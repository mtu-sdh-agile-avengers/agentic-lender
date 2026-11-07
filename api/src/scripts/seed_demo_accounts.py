"""Seeds the shared demo accounts (one per role) into the Firebase emulator suite.

Idempotent: safe to run on every `docker compose up`. Existing accounts are left as they are,
except that the role claim and the Firestore profile are (re)created if missing.

Usage:
    python -m src.scripts.seed_demo_accounts          # from api/, RUN_MODE=dev
    docker compose run --rm seed                      # what Docker Compose does

NOTE: refuses to run in prod, these passwords are public.
"""

import asyncio
from dataclasses import dataclass

from firebase_admin import auth

from src.auth.enums import Role
from src.auth.gateway import FirebaseAuthGateway
from src.config import RunMode, get_config
from src.firebase.connection import get_firestore, init_firebase
from src.users.models import UserProfileModel
from src.users.repository import UserProfileFirestoreRepository

DEMO_PASSWORD = "Password1"


@dataclass(frozen=True)
class DemoAccount:
    email: str
    full_name: str
    role: Role
    phone: str | None = None


DEMO_ACCOUNTS = (
    DemoAccount("borrower@demo.agenticlender.ie", "Bríd Borrower", Role.BORROWER, "+353870000001"),
    DemoAccount("broker@demo.agenticlender.ie", "Brian Broker", Role.BROKER, "+353870000002"),
    DemoAccount("officer@demo.agenticlender.ie", "Orla Officer", Role.BANK_OFFICER, "+353870000003"),
)


def _get_or_create_user(account: DemoAccount) -> tuple[auth.UserRecord, bool]:
    try:
        return auth.get_user_by_email(account.email), False
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=account.email,
            password=DEMO_PASSWORD,
            display_name=account.full_name,
            phone_number=account.phone,
            email_verified=True,
        )
        return user, True


async def seed() -> None:
    repo = UserProfileFirestoreRepository(get_firestore())
    gateway = FirebaseAuthGateway()

    for account in DEMO_ACCOUNTS:
        user, created = _get_or_create_user(account)

        # role claim; set before the first sign-in, so the first ID token already carries it
        if (user.custom_claims or {}).get("role") != account.role.value:
            await gateway.set_user_role(user.uid, account.role)

        if await repo.get_user_profile(user.uid) is None:
            await repo.add_user_profile(UserProfileModel(
                uid=user.uid,
                email=account.email,
                phone=account.phone,
                full_name=account.full_name,
                role=account.role,
            ))

        state = "created" if created else "exists "
        print(f"  {state}  {account.role.value:<27} {account.email:<34} {DEMO_PASSWORD}")


def main() -> None:
    if get_config().run_mode != RunMode.DEV:
        raise SystemExit("seed_demo_accounts only runs against the emulators (RUN_MODE=dev)")

    init_firebase()
    print("Seeding demo accounts (Firebase Auth emulator + Firestore emulator):")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
