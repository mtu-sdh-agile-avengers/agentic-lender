package com.example.alaimobileapp.LoginRegister

import com.example.alaimobileapp.Data.AppUser
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

interface AuthRepository {
    val currentUser: StateFlow<AppUser?>
    suspend fun signIn(email: String, password: String): Result<AppUser>
    suspend fun register(name: String, email: String, password: String): Result<AppUser>
    suspend fun signInWithGoogle(): Result<AppUser>
    fun signOut()
}

class AuthViewRepository : AuthRepository {
    private val users = mutableMapOf(
        "demo@alai.ie" to ("Password1" to AppUser("demo-uid", "John", "demo@alai.ie"))
    )
    private val _currentUser = MutableStateFlow<AppUser?>(null)
    override val currentUser: StateFlow<AppUser?> = _currentUser.asStateFlow()

    override suspend fun signIn(email: String, password: String): Result<AppUser> {
        delay(600)
        val entry = users[email.trim().lowercase()]
        return if (entry == null || entry.first != password) {
            Result.failure(Exception("Incorrect email or password."))
        } else {
            _currentUser.value = entry.second
            Result.success(entry.second)
        }
    }

    override suspend fun register(name: String, email: String, password: String): Result<AppUser> {
        delay(600)
        val key = email.trim().lowercase()
        if (users.containsKey(key)) {
            return Result.failure(Exception("An account with this email already exists."))
        }
        val user = AppUser("uid-${users.size + 1}", name.trim(), key)
        users[key] = password to user
        _currentUser.value = user
        return Result.success(user)
    }

    override suspend fun signInWithGoogle(): Result<AppUser> {
        delay(600)
        val user = AppUser("google-uid", "Google User", "google.user@example.com")
        _currentUser.value = user
        return Result.success(user)
    }

    override fun signOut() {
        _currentUser.value = null
    }
}
