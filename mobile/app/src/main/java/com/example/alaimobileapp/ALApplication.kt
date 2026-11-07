package com.example.alaimobileapp

import android.app.Application
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.auth.FirebaseAuth

class ALApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseSetup.init(this)
    }
}

/**
 * Firebase without google-services.json: the app talks to the shared Firebase Auth emulator
 * (started by `docker compose up`), so no real Firebase project or credentials are needed.
 *
 * The project ID must match AL-Core and AL-Web ("demo-agentic-lender"), otherwise AL-Core
 * rejects the ID token. Values come from BuildConfig (see app/build.gradle.kts).
 */
object FirebaseSetup {
    // Never sent anywhere real: "demo-" projects only ever talk to the emulators.
    // Well-formed values, because some Firebase components validate their format.
    private const val EMULATOR_API_KEY = "AIzaSyEmulatorOnlyKeyNotARealKey0000000"
    private const val EMULATOR_APP_ID = "1:123456789012:android:0123456789abcdef"

    fun init(app: Application) {
        if (FirebaseApp.getApps(app).isEmpty()) {
            val options = FirebaseOptions.Builder()
                .setProjectId(BuildConfig.AL_FIREBASE_PROJECT_ID)
                .setApplicationId(EMULATOR_APP_ID)
                .setApiKey(EMULATOR_API_KEY)
                .build()
            FirebaseApp.initializeApp(app, options)
        }
        // Must happen before the first FirebaseAuth call
        FirebaseAuth.getInstance().useEmulator(
            BuildConfig.AL_EMULATOR_HOST,
            BuildConfig.AL_AUTH_EMULATOR_PORT
        )
    }
}
