import datetime
from dataclasses import dataclass

from loguru import logger

from src.ai_engine_client.exceptions import AIEngineError
from src.assessments.enums import AssessmentStatus
from src.assessments.exceptions import AssessmentNotFoundError
from src.assessments.mapping import from_engine_result, to_engine_input
from src.assessments.models import AgentStepModel, AssessmentModel
from src.assessments.ports import AssessmentRepositoryPort, CommitteeGatewayPort
from src.auth.models import CurrentUserModel
from src.loan_applications.access import has_modify_access, has_view_access
from src.loan_applications.calculations import OFFERED_RATE_PERCENT
from src.loan_applications.exceptions import (
    LoanApplicationAccessError,
    LoanApplicationNotFoundError,
)
from src.loan_applications.models import LoanApplicationModel
from src.loan_applications.ports import LoanApplicationRepositoryPort
from src.utils import _get_utc_now

# AL-AI Engine keeps jobs in memory only: a job it no longer knows after this long is treated as lost
LOST_JOB_AFTER = datetime.timedelta(minutes=15)


@dataclass(frozen=True)
class AssessmentView:
    """An assessment together with its reasoning steps (empty until the run is done)."""

    assessment: AssessmentModel
    steps: list[AgentStepModel]


class AssessmentService:
    """Runs the AI committee for a loan application and exposes its reasoning.

    Flow (no callback from AL-AI Engine is needed: the client polls AL-Core every few seconds):
    POST .../assessments         -> application.start_assessment(); AL-AI Engine POST /v1/deliberations;
                                    assessment saved as `queued` with the engine's job ID.

    GET  .../assessments/latest  -> while the run is not finished, asks the engine for the job once;
                                    when it is done, the result and the reasoning steps are saved and
                                    application.finish_assessment() moves the application to `AI Deliberated`.
    """

    def __init__(
        self,
        applications: LoanApplicationRepositoryPort,
        assessments: AssessmentRepositoryPort,
        committee: CommitteeGatewayPort,
    ) -> None:
        self._applications = applications
        self._assessments = assessments
        self._committee = committee

    async def request_assessment(
        self, current_user: CurrentUserModel, loan_application_id: str
    ) -> AssessmentView:
        """Starts an AI committee run for a loan application, or returns the one already in progress.

        Args:
            current_user: assigned mortgage broker or underwriting bank officer.
            loan_application_id: ID of the loan application to assess.

        Returns:
            AssessmentView: the started (`queued`) or still running assessment, without steps.

        Raises:
            LoanApplicationNotFoundError: if the application does not exist or the user may not view it.
            LoanApplicationAccessError: if the user can view the application but is not assigned to it.
            LoanApplicationIsNotOpenError: if the application is already decided or closed.
            AIEngineError: if AL-AI Engine did not accept the run (the failed assessment is saved).
        """
        application = await self._load(current_user, loan_application_id)
        if not has_modify_access(current_user, application):
            raise LoanApplicationAccessError(loan_application_id)

        current = await self._current_assessment(application)
        if current is not None and not current.is_finished:
            return await self._refresh(application, current)  # one run at a time

        assessment = AssessmentModel(
            assessment_id=self._assessments.next_id(loan_application_id),
            loan_application_id=loan_application_id,
            requested_by_id=current_user.uid,
            rate_percent=OFFERED_RATE_PERCENT,
        )
        # checks again inside a transaction: the application must still be open and the user assigned
        application = await self._applications.update_loan_application(
            loan_application_id,
            lambda app: self._start(current_user, app, assessment.assessment_id),
        )

        try:
            job = await self._committee.start_deliberation(
                to_engine_input(application, assessment.rate_percent)
            )
        except AIEngineError as exc:
            failed = assessment.model_copy(
                update={
                    "status": AssessmentStatus.FAILED,
                    "error": str(exc.detail),
                    "finished_at": _get_utc_now(),
                }
            )
            await self._assessments.add_assessment(failed)
            raise

        assessment.job_id = job.job_id
        await self._assessments.add_assessment(assessment)
        return AssessmentView(assessment, [])

    async def get_latest_assessment(
        self, current_user: CurrentUserModel, loan_application_id: str
    ) -> AssessmentView:
        """Returns the latest AI committee run with its reasoning steps; collects the result if it just finished.

        Args:
            current_user: mortgage broker or underwriting bank officer who may view the application.
            loan_application_id: ID of the loan application.

        Returns:
            AssessmentView: the latest assessment; `steps` are filled once its status is `done`.

        Raises:
            LoanApplicationNotFoundError: if the application does not exist or the user may not view it.
            AssessmentNotFoundError: if the application has never been assessed.
        """
        application = await self._load(current_user, loan_application_id)
        assessment = await self._current_assessment(application)
        if assessment is None:
            raise AssessmentNotFoundError(loan_application_id)
        return await self._refresh(application, assessment)

    async def _load(
        self, current_user: CurrentUserModel, loan_application_id: str
    ) -> LoanApplicationModel:
        """Reads a loan application the current user may view.

        "Does not exist" and "exists, but is not yours" both raise the same 404, so IDs of other users'
        applications cannot be discovered by trying them.

        Args:
            current_user: user who sent the request.
            loan_application_id: ID of the loan application.

        Returns:
            LoanApplicationModel: the loan application.

        Raises:
            LoanApplicationNotFoundError: if the application does not exist or the user may not view it.
        """

        application = await self._applications.get_loan_application(loan_application_id)

        if application is None or not has_view_access(current_user, application):
            raise LoanApplicationNotFoundError(loan_application_id)

        return application

    async def _current_assessment(
        self, application: LoanApplicationModel
    ) -> AssessmentModel | None:
        """Reads the latest AI committee run of a loan application.

        The application stores the ID of its latest run, so one read by ID is enough (no "order by
        created_at" query, no index).

        Args:
            application: the loan application.

        Returns:
            AssessmentModel | None: the latest run; `None` if the application was never assessed, or if the
            run was just linked to the application and its document is not written yet.
        """
        if application.assessment_id is None:
            return None

        return await self._assessments.get_assessment(
            application.loan_application_id, application.assessment_id
        )

    @staticmethod
    def _start(
        current_user: CurrentUserModel,
        application: LoanApplicationModel,
        assessment_id: str,
    ) -> None:
        """Links a new AI committee run to the loan application; mutator for `update_loan_application`.

        Runs inside a Firestore transaction on the freshly read application, so the checks see its latest
        state (the broker may have been released or the application closed since it was first read).
        Firestore may call it more than once on contention, so it only changes the application.

        Args:
            current_user: user who starts the run.
            application: the loan application as read inside the transaction; changed in place.
            assessment_id: ID of the new run (from `AssessmentRepositoryPort.next_id`).

        Raises:
            LoanApplicationAccessError: if the user is no longer assigned to the application.
            LoanApplicationIsNotOpenError: if the application was decided or closed meanwhile.
        """
        if not has_modify_access(current_user, application):
            raise LoanApplicationAccessError(application.loan_application_id)

        application.start_assessment(assessment_id=assessment_id)

    async def _refresh(
        self, application: LoanApplicationModel, assessment: AssessmentModel
    ) -> AssessmentView:
        """Brings an AI committee run up to date, asking AL-AI Engine at most once.

        AL-Core gets the result by polling, not by a callback: every `GET .../assessments/latest` calls this
        method. Depending on the state of the run:

        - finished (`done` / `failed`): returned from Firestore with its steps; the engine is not asked;
        - engine unreachable: returned unchanged (only logged); the next poll tries again;
        - job unknown to the engine (it keeps jobs in memory): marked `failed` once `LOST_JOB_AFTER` has
          passed since the run was created, otherwise returned unchanged;
        - `queued` / `running`: the status is saved only if it changed;
        - `failed`: marked `failed` with the engine's error;
        - `done`: the result and the reasoning steps are saved in one batch, and the application gets the
          risk tier and moves to `AI Deliberated` (`finish_assessment` ignores an outdated run).

        Args:
            application: the loan application the run belongs to.
            assessment: the run as currently stored in Firestore.

        Returns:
            AssessmentView: the run in its current state; `steps` are filled only when it is `done`.
        """
        app_id = application.loan_application_id

        if assessment.is_finished or assessment.job_id is None:
            steps = await self._assessments.get_agent_steps(
                app_id, assessment.assessment_id
            )

            return AssessmentView(assessment, steps)

        try:
            job = await self._committee.get_deliberation(assessment.job_id)
        except AIEngineError as exc:
            # engine is temporarily down: keep showing the run as unfinished, the next poll tries again
            logger.warning(
                f"could not poll deliberation {assessment.job_id}: {exc.detail}"
            )

            return AssessmentView(assessment, [])

        if job is None:
            if _get_utc_now() - assessment.created_at > LOST_JOB_AFTER:
                return await self._fail(
                    app_id,
                    assessment,
                    "AL-AI Engine lost the job; request a new assessment",
                )

            return AssessmentView(assessment, [])

        if job.status in ("queued", "running"):
            if job.status != assessment.status:
                await self._assessments.save_result(
                    app_id, assessment.assessment_id, {"status": job.status}, []
                )

            return AssessmentView(
                assessment.model_copy(update={"status": AssessmentStatus(job.status)}),
                [],
            )

        if job.status == "failed" or job.result is None:
            return await self._fail(
                app_id, assessment, job.error or "committee run failed"
            )

        try:
            outcome = from_engine_result(job.result)
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            logger.error(
                f"unexpected result of deliberation {assessment.job_id}: {exc!r}"
            )
            return await self._fail(
                app_id, assessment, "AL-AI Engine returned an unexpected result"
            )

        await self._assessments.save_result(
            app_id, assessment.assessment_id, outcome.fields, outcome.steps
        )

        # ignored by the model when a newer run was started or the application was decided meanwhile
        await self._applications.update_loan_application(
            app_id,
            lambda app: app.finish_assessment(
                assessment_id=assessment.assessment_id, risk_tier=outcome.risk_tier
            ),
        )

        # model_validate (not model_copy) so the `decision` dict becomes a DecisionModel again
        updated = AssessmentModel.model_validate(
            {**assessment.model_dump(), **outcome.fields}
        )
        return AssessmentView(updated, outcome.steps)

    async def _fail(
        self, loan_application_id: str, assessment: AssessmentModel, error: str
    ) -> AssessmentView:
        """Marks an AI committee run as `failed` and saves why.

        Used when the engine reports a failed job, or when it lost the job (see `LOST_JOB_AFTER`).
        Once failed, the run is final: later polls return it from Firestore, and a new run can be started.

        Args:
            loan_application_id: ID of the loan application the run belongs to.
            assessment: the run that failed.
            error: reason shown to the user; cut to 500 characters (the engine may send a long traceback).

        Returns:
            AssessmentView: the failed run, without steps.
        """
        fields = {
            "status": AssessmentStatus.FAILED,
            "error": error[:500],
            "finished_at": _get_utc_now(),
        }
        await self._assessments.save_result(
            loan_application_id, assessment.assessment_id, fields, []
        )
        return AssessmentView(assessment.model_copy(update=fields), [])
