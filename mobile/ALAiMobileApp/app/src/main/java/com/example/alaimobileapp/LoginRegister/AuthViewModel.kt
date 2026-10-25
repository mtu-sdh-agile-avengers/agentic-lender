package com.example.alaimobileapp.LoginRegister

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.alaimobileapp.Data.AppContainer
import com.example.alaimobileapp.Data.AppUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiState(val loading: Boolean = false, val error: String? = null)

object AuthValidation {
    private val emailRegex = Regex("^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")
    fun isValidEmail(email: String) = emailRegex.matches(email.trim())
    const val MIN_PASSWORD = 6
}

class AuthViewModel : ViewModel() {
    private val repo = AppContainer.auth

    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    fun login(email: String, password: String, onSuccess: () -> Unit) {
        when {
            !AuthValidation.isValidEmail(email) -> return fail("Enter a valid email address.")
            password.isEmpty() -> return fail("Enter your password.")
        }
        launchAuth({ repo.signIn(email, password) }, onSuccess)
    }

    fun register(name: String, email: String, password: String, confirm: String, onSuccess: () -> Unit) {
        when {
            name.isBlank() -> return fail("Enter your full name.")
            !AuthValidation.isValidEmail(email) -> return fail("Enter a valid email address.")
            password.length < AuthValidation.MIN_PASSWORD ->
                return fail("Password must be at least ${AuthValidation.MIN_PASSWORD} characters.")
            password != confirm -> return fail("Passwords don't match.")
        }
        launchAuth({ repo.register(name, email, password) }, onSuccess)
    }

    fun googleSignIn(onSuccess: () -> Unit) {
        launchAuth({ repo.signInWithGoogle() }, onSuccess)
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    private fun fail(message: String) {
        _state.value = AuthUiState(error = message)
    }

    private fun launchAuth(block: suspend () -> Result<AppUser>, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _state.value = AuthUiState(loading = true)
            val result = block()
            if (result.isSuccess) {
                _state.value = AuthUiState()
                onSuccess()
            } else {
                _state.value = AuthUiState(error = result.exceptionOrNull()?.message ?: "Something went wrong.")
            }
        }
    }
}
