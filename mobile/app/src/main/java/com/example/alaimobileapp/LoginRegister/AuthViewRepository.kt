package com.example.alaimobileapp.LoginRegister

import com.example.alaimobileapp.BuildConfig
import com.example.alaimobileapp.Data.AlCoreApi
import com.example.alaimobileapp.Data.AlCoreException
import com.example.alaimobileapp.Data.AppUser
import com.example.alaimobileapp.Data.UserProfile
import com.google.firebase.FirebaseNetworkException
import com.google.firebase.FirebaseTooManyRequestsException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.auth.FirebaseAuthUserCollisionException
import com.google.firebase.auth.FirebaseAuthWeakPasswordException
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.UserProfileChangeRequest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.tasks.await

interface AuthRepository {
    val currentUser: StateFlow<AppUser?>
    suspend fun signIn(email: String, password: String): Result<AppUser>
    suspend fun register(name: String, email: String, password: String): Result<AppUser>
    suspend fun signInWithGoogle(): Result<AppUser>
    fun signOut()
}

/**
 * Real sign-in: Firebase Auth (the shared emulator in development) for the account,
 * AL-Core GET/POST /api/v1/users/me for the profile and role.
 *
 *   sign in  -> Firebase signIn -> ID token -> GET /users/me (404? -> POST /users/me)
 *   register -> Firebase createUser -> POST /users/me (borrower profile + role claim) -> refresh token
 */
class AuthViewRepository(
    private val auth: FirebaseAuth = FirebaseAuth.getInstance(),
    private val api: AlCoreApi = AlCoreApi()
) : AuthRepository {
    private val _currentUser = MutableStateFlow<AppUser?>(null)
    override val currentUser: StateFlow<AppUser?> = _currentUser.asStateFlow()

    override suspend fun signIn(email: String, password: String): Result<AppUser> = authenticate {
        val user = auth.signInWithEmailAndPassword(email.trim(), password).await().user
            ?: throw AuthFailure("Sign-in failed. Please try again.")
        loadOrCreateProfile(user)
    }

    override suspend fun register(name: String, email: String, password: String): Result<AppUser> = authenticate {
        val user = auth.createUserWithEmailAndPassword(email.trim(), password).await().user
            ?: throw AuthFailure("Registration failed. Please try again.")
        user.updateProfile(UserProfileChangeRequest.Builder().setDisplayName(name.trim()).build()).await()

        val profile = api.createMyProfile(idToken(user), fullName = name.trim())
        // AL-Core has just set the role claim; fetch a token that carries it
        user.getIdToken(true).await()
        profile
    }

    override suspend fun signInWithGoogle(): Result<AppUser> =
        Result.failure(Exception("Google sign-in isn't available yet. Please use email and password."))

    override fun signOut() {
        auth.signOut()
        _currentUser.value = null
    }

    /** The profile from AL-Core; created on first sign-in if the account has none yet. */
    private suspend fun loadOrCreateProfile(user: FirebaseUser): UserProfile = try {
        api.getMyProfile(idToken(user))
    } catch (e: AlCoreException) {
        if (e.status != 404) throw e
        api.createMyProfile(idToken(user), fullName = user.displayName).also {
            user.getIdToken(true).await()
        }
    }

    private suspend fun idToken(user: FirebaseUser): String =
        user.getIdToken(false).await().token ?: throw AuthFailure("Could not get a sign-in token.")

    /** Runs a sign-in flow; only borrowers may use the mobile app. */
    private suspend fun authenticate(block: suspend () -> UserProfile): Result<AppUser> = try {
        val profile = block()
        if (profile.role != UserProfile.ROLE_BORROWER) {
            auth.signOut()
            throw AuthFailure("This app is for borrowers. Brokers and bank officers sign in on the web portal.")
        }
        val user = AppUser(
            uid = profile.uid,
            name = profile.fullName ?: profile.email.substringBefore('@'),
            email = profile.email,
            role = profile.role
        )
        _currentUser.value = user
        Result.success(user)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        // Account exists in Firebase but AL-Core failed: do not leave a half-signed-in session
        if (e is AlCoreException) auth.signOut()
        Result.failure(Exception(messageFor(e), e))
    }

    private fun messageFor(e: Exception): String = when (e) {
        is AuthFailure, is AlCoreException -> e.message ?: GENERIC_ERROR
        is FirebaseAuthWeakPasswordException -> "Password is too weak. Use at least 6 characters."
        is FirebaseAuthInvalidCredentialsException,
        is FirebaseAuthInvalidUserException -> "Incorrect email or password."
        is FirebaseAuthUserCollisionException -> "An account with this email already exists."
        is FirebaseTooManyRequestsException -> "Too many attempts. Please wait and try again."
        is FirebaseNetworkException ->
            if (BuildConfig.AL_USE_FIREBASE_EMULATOR) "Can't reach the sign-in server. Is the Firebase emulator running?"
            else "Can't reach the sign-in server. Check your internet connection."
        else -> GENERIC_ERROR
    }

    private class AuthFailure(message: String) : Exception(message)

    private companion object {
        const val GENERIC_ERROR = "Something went wrong. Please try again."
    }
}
