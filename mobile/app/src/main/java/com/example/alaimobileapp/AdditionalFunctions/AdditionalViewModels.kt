package com.example.alaimobileapp.AdditionalFunctions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.alaimobileapp.Data.AppContainer
import com.example.alaimobileapp.Data.PaymentCard
import com.example.alaimobileapp.Data.PaymentKind
import com.example.alaimobileapp.Data.PaymentRecord
import com.example.alaimobileapp.Data.PaymentResult
import com.example.alaimobileapp.Data.SupportTicket
import com.example.alaimobileapp.Data.SupportTopic
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.Calendar

class BrokerViewModel : ViewModel() {
    private val repo = AppContainer.broker
    val broker = repo.broker
    val messages = repo.messages
    val brokerTyping = repo.brokerTyping
    fun send(text: String) = repo.send(text)
}

data class PaymentUiState(
    val processing: Boolean = false,
    val error: String? = null,
    val success: PaymentRecord? = null
)

class PaymentViewModel : ViewModel() {
    private val loans = AppContainer.loans
    private val payments = AppContainer.payments

    val application = loans.application
    val history = payments.history

    private val _state = MutableStateFlow(PaymentUiState())
    val state: StateFlow<PaymentUiState> = _state.asStateFlow()

    fun pay(kind: PaymentKind, number: String, expiry: String, cvc: String, holder: String) {
        val error = validate(number, expiry, cvc, holder)
        if (error != null) {
            _state.value = PaymentUiState(error = error)
            return
        }
        viewModelScope.launch {
            _state.value = PaymentUiState(processing = true)
            val result = withContext(NonCancellable) {
                val r = payments.pay(kind, PaymentCard(number, expiry, cvc, holder))
                if (r is PaymentResult.Success) loans.markPaid(kind)
                r
            }
            _state.value = when (result) {
                is PaymentResult.Success -> PaymentUiState(success = result.record)
                is PaymentResult.Failure -> PaymentUiState(error = result.message)
            }
        }
    }

    fun dismissResult() {
        _state.value = PaymentUiState()
    }

    private fun validate(number: String, expiry: String, cvc: String, holder: String): String? {
        val digits = number.filter { it.isDigit() }
        if (holder.isBlank()) return "Enter the name on the card."
        if (digits.length != 16) return "Card number must be 16 digits."
        val match = Regex("^(0[1-9]|1[0-2])/(\\d{2})$").matchEntire(expiry)
            ?: return "Enter expiry as MM/YY."
        val month = match.groupValues[1].toInt()
        val year = 2000 + match.groupValues[2].toInt()
        val now = Calendar.getInstance()
        val nowYear = now.get(Calendar.YEAR)
        val nowMonth = now.get(Calendar.MONTH) + 1
        if (year < nowYear || (year == nowYear && month < nowMonth)) return "This card has expired."
        if (cvc.length !in 3..4) return "Enter the 3 or 4 digit security code."
        return null
    }
}

class SupportViewModel : ViewModel() {
    private val repo = AppContainer.feedback
    val tickets = repo.tickets

    private val _lastTicket = MutableStateFlow<SupportTicket?>(null)
    val lastTicket: StateFlow<SupportTicket?> = _lastTicket.asStateFlow()

    fun submit(topic: SupportTopic, subject: String, message: String) {
        _lastTicket.value = repo.submitTicket(topic, subject, message)
    }

    fun dismissConfirmation() {
        _lastTicket.value = null
    }
}

class ReviewViewModel : ViewModel() {
    private val repo = AppContainer.feedback
    val reviews = repo.reviews

    private val _submitted = MutableStateFlow(false)
    val submitted: StateFlow<Boolean> = _submitted.asStateFlow()

    fun submit(rating: Int, comment: String) {
        repo.submitReview(rating, comment)
        _submitted.value = true
    }

    fun reset() {
        _submitted.value = false
    }
}
