package com.example.alaimobileapp.Data

import com.example.alaimobileapp.LoginRegister.AuthRepository
import com.example.alaimobileapp.LoginRegister.AuthViewRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicLong
import kotlin.math.roundToInt

/**
 * Single place where the app's services are created.
 * Needs Firestore, ML endpoint and Stripe implementations
 */
object AppContainer {
    val auth: AuthRepository = AuthViewRepository()
    val loans: LoanRepository = FakeLoanRepository()
    val valuation: ValuationService = FakeValuationService()
    val broker: BrokerRepository = FakeBrokerRepository()
    val payments: PaymentService = FakePaymentService()
    val feedback: FeedbackRepository = FakeFeedbackRepository()

    fun signOut() {
        auth.signOut()
        loans.clear()
        broker.clear()
        payments.clear()
        feedback.clear()
    }
}

// ---------- Loans ----------

interface LoanRepository {
    val application: StateFlow<LoanApplicationData?>
    val draftPropertyValue: StateFlow<Double?>
    fun submit(data: LoanApplicationData)
    fun markPaid(kind: PaymentKind)
    /** Demo only: moves the application to its next stage  */
    fun advance()
    fun setDraftPropertyValue(value: Double?)
    fun clear()
}

/** TODO: replace with Firestore / backend that holds the real digital loan note. */
class FakeLoanRepository : LoanRepository {
    private val _application = MutableStateFlow<LoanApplicationData?>(null)
    override val application: StateFlow<LoanApplicationData?> = _application.asStateFlow()

    private val _draft = MutableStateFlow<Double?>(null)
    override val draftPropertyValue: StateFlow<Double?> = _draft.asStateFlow()

    override fun submit(data: LoanApplicationData) {
        _application.value = data.copy(stepsDone = 1)
    }

    override fun markPaid(kind: PaymentKind) {
        _application.update { app ->
            when {
                app == null -> null
                kind == PaymentKind.VERIFICATION_FEE ->
                    app.copy(verificationFeePaid = true, stepsDone = maxOf(app.stepsDone, 2))
                else ->
                    app.copy(fastTrackPaid = true, stepsDone = maxOf(app.stepsDone, 3))
            }
        }
    }

    override fun advance() {
        _application.update { app -> app?.copy(stepsDone = (app.stepsDone + 1).coerceAtMost(4)) }
    }

    override fun setDraftPropertyValue(value: Double?) {
        _draft.value = value
    }

    override fun clear() {
        _application.value = null
        _draft.value = null
    }
}

// ---------- Valuation (ML model) ----------

interface ValuationService {
    suspend fun estimate(spec: PropertySpec): ValuationResult
}

/**
 * Formula-based stand-in for the ML valuation model.
 * TODO: replace with an HTTP call to the real model endpoint.
 */
class FakeValuationService : ValuationService {
    override suspend fun estimate(spec: PropertySpec): ValuationResult {
        delay(900)
        val base = Counties.perSqm[spec.county] ?: 2500.0
        val bedroomFactor = 1.0 + 0.02 * (spec.bedrooms - 3)
        val perSqm = base * spec.type.factor * spec.ber.factor * bedroomFactor
        val estimate = (perSqm * spec.sqm / 1000.0).roundToInt() * 1000.0

        var verdict: PriceVerdict? = null
        var diff: Double? = null
        val asking = spec.askingPrice
        if (asking != null && asking > 0 && estimate > 0) {
            val d = (asking - estimate) / estimate * 100.0
            diff = d
            verdict = when {
                d < -5.0 -> PriceVerdict.GOOD_VALUE
                d <= 7.0 -> PriceVerdict.FAIR
                else -> PriceVerdict.OVERPRICED
            }
        }
        return ValuationResult(
            estimate = estimate,
            low = (estimate * 0.92 / 1000.0).roundToInt() * 1000.0,
            high = (estimate * 1.08 / 1000.0).roundToInt() * 1000.0,
            pricePerSqm = if (spec.sqm > 0) estimate / spec.sqm else 0.0,
            verdict = verdict,
            differencePct = diff
        )
    }
}

// ---------- Broker chat ----------

interface BrokerRepository {
    val broker: Broker
    val messages: StateFlow<List<ChatMessage>>
    val brokerTyping: StateFlow<Boolean>
    fun send(text: String)
    fun clear()
}

/** TODO: replace with Firestore (or similar) chat between borrower and the assigned broker. */
class FakeBrokerRepository : BrokerRepository {
    override val broker = Broker("Aoife Murphy", "Mortgage broker")

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val ids = AtomicLong(0)

    private val _messages = MutableStateFlow(listOf(welcome()))
    override val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _typing = MutableStateFlow(false)
    override val brokerTyping: StateFlow<Boolean> = _typing.asStateFlow()

    private fun welcome() = ChatMessage(
        ids.incrementAndGet(),
        "Hi, I'm Aoife, your mortgage broker. Ask me anything about your application.",
        fromUser = false,
        timestamp = System.currentTimeMillis()
    )

    override fun send(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return
        _messages.update {
            it + ChatMessage(ids.incrementAndGet(), trimmed, true, System.currentTimeMillis())
        }
        scope.launch {
            _typing.value = true
            delay(1500)
            _messages.update {
                it + ChatMessage(ids.incrementAndGet(), replyFor(trimmed), false, System.currentTimeMillis())
            }
            _typing.value = false
        }
    }

    private fun replyFor(text: String): String {
        val t = text.lowercase()
        return when {
            "document" in t || "payslip" in t || "bank statement" in t ->
                "Please upload your last 3 payslips and 6 months of bank statements and I'll check them today."
            "rate" in t || "interest" in t ->
                "Rates depend on your LTV. At the moment I can see options from about 3.5% to 4.5% for your profile."
            "status" in t || "verification" in t || "when" in t ->
                "I can see your application on my side. The Status screen shows each stage as it completes."
            "property" in t || "valuation" in t || "price" in t ->
                "The Fair-Price Checker gives a quick estimate. For a formal valuation, request a fast-track appraisal."
            "hello" in t || "hi" == t || "hey" in t ->
                "Hello! How can I help with your mortgage today?"
            else ->
                "Thanks for your message. I'll look into that and get back to you shortly."
        }
    }

    override fun clear() {
        _messages.value = listOf(welcome())
        _typing.value = false
    }
}

// ---------- Payments (Stripe) ----------

interface PaymentService {
    val history: StateFlow<List<PaymentRecord>>
    suspend fun pay(kind: PaymentKind, card: PaymentCard): PaymentResult
    fun clear()
}

/**
 * Mimics Stripe test mode using Stripe's published test card numbers.
 * TODO: replace with Stripe PaymentSheet + a backend that creates PaymentIntents.
 */
class FakePaymentService : PaymentService {
    private val _history = MutableStateFlow<List<PaymentRecord>>(emptyList())
    override val history: StateFlow<List<PaymentRecord>> = _history.asStateFlow()

    private val successCards = setOf("4242424242424242", "5555555555554444", "4000056655665556")

    override suspend fun pay(kind: PaymentKind, card: PaymentCard): PaymentResult {
        delay(1200)
        val digits = card.number.filter { it.isDigit() }
        return when {
            digits in successCards -> {
                val record = PaymentRecord(
                    id = "pi_test_" + System.currentTimeMillis().toString().takeLast(8),
                    kind = kind,
                    amountEur = kind.amountEur,
                    timestamp = System.currentTimeMillis(),
                    last4 = digits.takeLast(4)
                )
                _history.update { listOf(record) + it }
                PaymentResult.Success(record)
            }
            digits == "4000000000000002" -> PaymentResult.Failure("Your card was declined.")
            digits == "4000000000009995" -> PaymentResult.Failure("Your card has insufficient funds.")
            else -> PaymentResult.Failure("Sandbox mode: use a Stripe test card, e.g. 4242 4242 4242 4242.")
        }
    }

    override fun clear() {
        _history.value = emptyList()
    }
}

// ---------- Support tickets & reviews ----------

interface FeedbackRepository {
    val tickets: StateFlow<List<SupportTicket>>
    val reviews: StateFlow<List<Review>>
    fun submitTicket(topic: SupportTopic, subject: String, message: String): SupportTicket
    fun submitReview(rating: Int, comment: String)
    fun clear()
}

/** TODO: replace with Firestore collections (or a helpdesk API). */
class FakeFeedbackRepository : FeedbackRepository {
    private val _tickets = MutableStateFlow<List<SupportTicket>>(emptyList())
    override val tickets: StateFlow<List<SupportTicket>> = _tickets.asStateFlow()

    private val _reviews = MutableStateFlow<List<Review>>(emptyList())
    override val reviews: StateFlow<List<Review>> = _reviews.asStateFlow()

    private val ids = AtomicLong(0)

    override fun submitTicket(topic: SupportTopic, subject: String, message: String): SupportTicket {
        val ticket = SupportTicket(
            ref = "ALM-" + (1000 + ids.incrementAndGet()),
            topic = topic,
            subject = subject.trim(),
            message = message.trim(),
            autoReply = topic.autoReply,
            createdAt = System.currentTimeMillis()
        )
        _tickets.update { listOf(ticket) + it }
        return ticket
    }

    override fun submitReview(rating: Int, comment: String) {
        _reviews.update {
            listOf(Review(ids.incrementAndGet(), rating.coerceIn(1, 5), comment.trim(), System.currentTimeMillis())) + it
        }
    }

    override fun clear() {
        _tickets.value = emptyList()
        _reviews.value = emptyList()
    }
}
