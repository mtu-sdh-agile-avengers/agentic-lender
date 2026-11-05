package com.example.alaimobileapp.Data

import kotlin.math.pow

data class AppUser(val uid: String, val name: String, val email: String)

enum class PaymentKind(val title: String, val description: String, val amountEur: Double) {
    VERIFICATION_FEE(
        "Application verification fee",
        "One-off fee to verify your income, debts and deposit.",
        49.0
    ),
    FAST_TRACK(
        "Fast-track appraisal",
        "Priority property appraisal so your application reaches review sooner.",
        149.0
    )
}

/**
 * The borrower's application and its lifecycle.
 * stepsDone: 1 = Application, 2 = Verification, 3 = Review, 4 = Decision.
 */
data class LoanApplicationData(
    val annualIncome: Double,
    val monthlyDebt: Double,
    val deposit: Double,
    val termYears: Int,
    val propertyValue: Double,
    val stepsDone: Int = 1,
    val verificationFeePaid: Boolean = false,
    val fastTrackPaid: Boolean = false,
    val submittedAt: Long = System.currentTimeMillis()
) {
    val assessment: LoanAssessment
        get() = LoanCalculator.assess(annualIncome, monthlyDebt, deposit, termYears, propertyValue)

    val isFinished: Boolean get() = stepsDone >= 4
    val approved: Boolean get() = assessment.approvalScore >= 50

    val statusTitle: String
        get() = when (stepsDone) {
            1 -> "Awaiting Verification"
            2 -> "Under Review"
            3 -> "Decision Pending"
            else -> if (approved) "Approved" else "Declined"
        }


    val loanNoteState: String
        get() = when (stepsDone) {
            1 -> "Draft note issued"
            2 -> "Note under review"
            3 -> "Note awaiting sign-off"
            else -> if (approved) "Note active" else "Note closed"
        }

    fun hasPaid(kind: PaymentKind): Boolean = when (kind) {
        PaymentKind.VERIFICATION_FEE -> verificationFeePaid
        PaymentKind.FAST_TRACK -> fastTrackPaid
    }
}

data class LoanAssessment(
    val loanAmount: Double,
    val ltv: Double,
    val dti: Double,
    val monthlyPayment: Double,
    val approvalScore: Int,
    val tips: List<String>
) {
    val approvalLabel: String
        get() = when {
            approvalScore >= 75 -> "High"
            approvalScore >= 50 -> "Medium"
            else -> "Low"
        }
}

data class MaxBorrow(
    val maxLoan: Double,
    val maxPropertyPrice: Double,
    val limitingFactor: String
)

/** Stand in math for borrow estimator*/
object LoanCalculator {
    const val ANNUAL_RATE = 0.04          // assumed interest rate
    const val MAX_INCOME_MULTIPLE = 4.0   // lending cap: 4x gross income
    const val MAX_LTV = 90.0              // percent
    const val MAX_DTI = 36.0              // percent

    fun monthlyPayment(principal: Double, termYears: Int, annualRate: Double = ANNUAL_RATE): Double {
        if (principal <= 0.0 || termYears <= 0) return 0.0
        val r = annualRate / 12.0
        val n = termYears * 12
        return principal * r / (1 - (1 + r).pow(-n))
    }

    fun principalFor(payment: Double, termYears: Int, annualRate: Double = ANNUAL_RATE): Double {
        if (payment <= 0.0 || termYears <= 0) return 0.0
        val r = annualRate / 12.0
        val n = termYears * 12
        return payment * (1 - (1 + r).pow(-n)) / r
    }

    fun assess(
        annualIncome: Double,
        monthlyDebt: Double,
        deposit: Double,
        termYears: Int,
        propertyValue: Double
    ): LoanAssessment {
        val loan = (propertyValue - deposit).coerceAtLeast(0.0)
        val payment = monthlyPayment(loan, termYears)
        val monthlyIncome = annualIncome / 12.0
        val ltv = if (propertyValue > 0) loan / propertyValue * 100.0 else 0.0
        val dti = if (monthlyIncome > 0) (monthlyDebt + payment) / monthlyIncome * 100.0 else 100.0

        var score = 100
        val tips = mutableListOf<String>()

        if (ltv > 90) {
            score -= 45
        } else if (ltv > 80) {
            score -= 15
        }
        if (ltv > 80) {
            val extra = propertyValue * 0.20 - deposit
            tips += "A deposit about ${money(extra)} larger would bring your LTV down to 80%."
        }

        if (dti > 43) {
            score -= 40
        } else if (dti > 36) {
            score -= 20
        } else if (dti > 28) {
            score -= 5
        }
        if (dti > 36) {
            tips += "Paying down existing debts or choosing a longer term would lower your DTI."
        }

        if (loan > annualIncome * MAX_INCOME_MULTIPLE) {
            score -= 30
            tips += "This loan is above ${MAX_INCOME_MULTIPLE.toInt()}x your gross income."
        }

        if (tips.isEmpty()) tips += "Your figures look strong. Next step: get your documents verified."

        return LoanAssessment(
            loanAmount = loan,
            ltv = ltv,
            dti = dti,
            monthlyPayment = payment,
            approvalScore = score.coerceIn(0, 100),
            tips = tips
        )
    }

    fun maxBorrow(annualIncome: Double, monthlyDebt: Double, deposit: Double, termYears: Int): MaxBorrow {
        val byIncome = annualIncome * MAX_INCOME_MULTIPLE
        val byLtv = deposit * (MAX_LTV / (100.0 - MAX_LTV))   // loan <= 9x deposit at 90% LTV
        val paymentCap = (annualIncome / 12.0 * MAX_DTI / 100.0 - monthlyDebt).coerceAtLeast(0.0)
        val byDti = principalFor(paymentCap, termYears)

        val limits = listOf(
            byIncome to "the ${MAX_INCOME_MULTIPLE.toInt()}x income lending cap",
            byLtv to "the ${MAX_LTV.toInt()}% loan-to-value limit (your deposit)",
            byDti to "the ${MAX_DTI.toInt()}% debt-to-income limit"
        )
        val tightest = limits.minByOrNull { it.first }!!
        val maxLoan = tightest.first.coerceAtLeast(0.0)
        return MaxBorrow(maxLoan, maxLoan + deposit, tightest.second)
    }

    private fun money(v: Double): String = "€" + String.format(java.util.Locale.UK, "%,.0f", v.coerceAtLeast(0.0))
}


/** Stand in for property estimator */
enum class PropertyType(val label: String, val factor: Double) {
    APARTMENT("Apartment", 0.95),
    TERRACED("Terraced house", 0.97),
    SEMI_DETACHED("Semi-detached house", 1.00),
    DETACHED("Detached house", 1.12),
    BUNGALOW("Bungalow", 1.05)
}

enum class BerRating(val label: String, val factor: Double) {
    A1("A1", 1.08), A2("A2", 1.06), A3("A3", 1.04),
    B1("B1", 1.02), B2("B2", 1.01), B3("B3", 1.00),
    C1("C1", 0.99), C2("C2", 0.98), C3("C3", 0.97),
    D1("D1", 0.95), D2("D2", 0.94),
    E1("E1", 0.92), E2("E2", 0.91),
    F("F", 0.89), G("G", 0.87)
}

data class PropertySpec(
    val county: String,
    val sqm: Double,
    val bedrooms: Int,
    val type: PropertyType,
    val ber: BerRating,
    val askingPrice: Double? = null
)

enum class PriceVerdict(val label: String) {
    GOOD_VALUE("Good value"),
    FAIR("Fairly priced"),
    OVERPRICED("Looks overpriced")
}

data class ValuationResult(
    val estimate: Double,
    val low: Double,
    val high: Double,
    val pricePerSqm: Double,
    val verdict: PriceVerdict?,
    val differencePct: Double?
)

object Counties {
    val perSqm: Map<String, Double> = mapOf(
        "Carlow" to 2600.0, "Cavan" to 2000.0, "Clare" to 2700.0, "Cork" to 3600.0,
        "Donegal" to 2000.0, "Dublin" to 5500.0, "Galway" to 3500.0, "Kerry" to 2700.0,
        "Kildare" to 3800.0, "Kilkenny" to 2900.0, "Laois" to 2500.0, "Leitrim" to 1800.0,
        "Limerick" to 3000.0, "Longford" to 1800.0, "Louth" to 3000.0, "Mayo" to 2100.0,
        "Meath" to 3500.0, "Monaghan" to 2000.0, "Offaly" to 2300.0, "Roscommon" to 1900.0,
        "Sligo" to 2300.0, "Tipperary" to 2300.0, "Waterford" to 2800.0, "Westmeath" to 2600.0,
        "Wexford" to 2700.0, "Wicklow" to 4200.0
    )
    val names: List<String> = perSqm.keys.sorted()
}

// ---------- Broker chat ----------

data class Broker(val name: String, val title: String)

data class ChatMessage(val id: Long, val text: String, val fromUser: Boolean, val timestamp: Long)

// ---------- Payments ----------

data class PaymentCard(val number: String, val expiry: String, val cvc: String, val holder: String)

data class PaymentRecord(
    val id: String,
    val kind: PaymentKind,
    val amountEur: Double,
    val timestamp: Long,
    val last4: String
)

sealed class PaymentResult {
    data class Success(val record: PaymentRecord) : PaymentResult()
    data class Failure(val message: String) : PaymentResult()
}

// ---------- Support & reviews ----------

enum class SupportTopic(val label: String, val autoReply: String) {
    APPLICATION(
        "Loan application",
        "Thanks for getting in touch. You can follow every stage of your application on the Status screen. A lending specialist will reply within 1 working day."
    ),
    PAYMENTS(
        "Payments & fees",
        "Thanks for your message. Payments made in the app appear under Make Payment. If a charge looks wrong, our billing team will review it within 2 working days."
    ),
    PROPERTY(
        "Property valuation",
        "Thanks for your message. Valuations are estimates, not formal appraisals. A fast-track appraisal can be requested from Make Payment."
    ),
    ACCOUNT(
        "Account & login",
        "Thanks for your message. If you can't sign in, try resetting your password. Our team will follow up within 1 working day."
    ),
    OTHER(
        "Something else",
        "Thanks for your message. We've logged your request and a member of the team will reply soon."
    )
}

data class SupportTicket(
    val ref: String,
    val topic: SupportTopic,
    val subject: String,
    val message: String,
    val autoReply: String,
    val createdAt: Long
)

data class Review(val id: Long, val rating: Int, val comment: String, val createdAt: Long)
