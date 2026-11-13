package com.example.alaimobileapp.Data

import com.example.alaimobileapp.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Profile returned by AL-Core: account data from the token + the profile record in Firestore. */
data class UserProfile(
    val uid: String,
    val email: String,
    val fullName: String?,
    val phone: String?,
    val role: String,
    val emailVerified: Boolean
) {
    companion object {
        const val ROLE_BORROWER = "retail_borrower"

        fun fromJson(json: JSONObject) = UserProfile(
            uid = json.getString("uid"),
            email = json.getString("email"),
            fullName = json.optStringOrNull("full_name"),
            phone = json.optStringOrNull("phone"),
            role = json.optString("role"),
            emailVerified = json.optBoolean("email_verified")
        )

        private fun JSONObject.optStringOrNull(key: String): String? =
            if (isNull(key)) null else optString(key).ifBlank { null }
    }
}

/** An AL-Core error. status = 0 means AL-Core could not be reached at all. */
class AlCoreException(val status: Int, message: String) : Exception(message)

/**
 * HTTP client for AL-Core (the REST API). Every call sends the Firebase ID token as
 * `Authorization: Bearer <token>`; AL-Core verifies it against the same Firebase emulator.
 */
class AlCoreApi(
    private val baseUrl: String = BuildConfig.AL_API_BASE_URL,
    private val client: OkHttpClient = defaultClient
) {
    /** GET /api/v1/users/me. Throws AlCoreException(404) if the profile does not exist yet. */
    suspend fun getMyProfile(idToken: String): UserProfile =
        call(idToken, Request.Builder().url("$baseUrl/api/v1/users/me").get())

    /** POST /api/v1/users/me. Creates the borrower profile and sets the role claim. */
    suspend fun createMyProfile(idToken: String, fullName: String?, phone: String? = null): UserProfile {
        val body = JSONObject()
            .put("full_name", fullName ?: JSONObject.NULL)
            .put("phone", phone ?: JSONObject.NULL)
            .toString()
            .toRequestBody(JSON)
        return call(idToken, Request.Builder().url("$baseUrl/api/v1/users/me").post(body))
    }

    private suspend fun call(idToken: String, builder: Request.Builder): UserProfile =
        withContext(Dispatchers.IO) {
            val request = builder.header("Authorization", "Bearer $idToken").build()
            try {
                client.newCall(request).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (!response.isSuccessful) {
                        throw AlCoreException(response.code, messageFor(response.code, text))
                    }
                    UserProfile.fromJson(JSONObject(text))
                }
            } catch (e: IOException) {
                throw AlCoreException(0, "Can't reach the server at $baseUrl. Is AL-Core running?")
            } catch (e: JSONException) {
                throw AlCoreException(-1, "Unexpected response from the server.")
            }
        }

    private fun messageFor(status: Int, body: String): String {
        val detail = runCatching { JSONObject(body).optString("detail") }.getOrNull()
        return when (status) {
            401 -> "Your session could not be verified. Please sign in again."
            404 -> "No profile exists for this account yet."
            409 -> "A profile for this account already exists."
            429 -> "Too many requests. Please wait a moment."
            else -> detail?.takeIf { it.isNotBlank() } ?: "Server error ($status). Please try again."
        }
    }

    private companion object {
        val JSON = "application/json".toMediaType()
        val defaultClient: OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()
    }
}
