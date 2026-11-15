package com.example.alaimobileapp.LoanAndCheckers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.alaimobileapp.Data.AppContainer
import com.example.alaimobileapp.Data.LoanApplicationData
import com.example.alaimobileapp.Data.PropertySpec
import com.example.alaimobileapp.Data.ValuationResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class LoanViewModel : ViewModel() {
    private val repo = AppContainer.loans
    val application = repo.application
    val draftPropertyValue = repo.draftPropertyValue

    fun submit(data: LoanApplicationData) = repo.submit(data)
    fun advanceDemo() = repo.advance()
}

data class PropertyUiState(
    val loading: Boolean = false,
    val result: ValuationResult? = null,
    val error: String? = null
)

class PropertyViewModel : ViewModel() {
    private val service = AppContainer.valuation

    private val _state = MutableStateFlow(PropertyUiState())
    val state: StateFlow<PropertyUiState> = _state.asStateFlow()

    fun check(spec: PropertySpec) {
        viewModelScope.launch {
            _state.value = PropertyUiState(loading = true)
            try {
                _state.value = PropertyUiState(result = service.estimate(spec))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.value = PropertyUiState(error = "Couldn't get a valuation. Please try again.")
            }
        }
    }

    fun useForApplication(value: Double) = AppContainer.loans.setDraftPropertyValue(value)
}
