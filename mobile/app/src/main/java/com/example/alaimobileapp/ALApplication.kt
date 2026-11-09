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
 * Firebase without google-services.json. Two modes, chosen at build time (see app/build.gradle.kts):
 *
 *  - emulator (default): the shared Firebase Auth emulator started by `docker compose up`;
 *    no real project or credentials needed.
 *  - cloud (al.firebaseMode=cloud): the real Firebase project, with the Android app's API key
 *    and app ID from ~/.gradle/gradle.properties.
 *
 * The project ID must match AL-Core's, otherwise AL-Core rejects the ID token.
 */
object FirebaseSetup {
    // Never sent anywhere real: "demo-" projects only ever talk to the emulators.
    // Well-formed values, because some Firebase components validate their format.
    private const val EMULATOR_API_KEY = "AIzaSyEmulatorOnlyKeyNotARealKey0000000"
    private const val EMULATOR_APP_ID = "1:123456789012:android:0123456789abcdef"

    fun init(app: Application) {
        val useEmulator = BuildConfig.AL_USE_FIREBASE_EMULATOR
        if (FirebaseApp.getApps(app).isEmpty()) {
            val options = FirebaseOptions.Builder()
                .setProjectId(BuildConfig.AL_FIREBASE_PROJECT_ID)
                .setApplicationId(if (useEmulator) EMULATOR_APP_ID else BuildConfig.AL_FIREBASE_APP_ID)
                .setApiKey(if (useEmulator) EMULATOR_API_KEY else BuildConfig.AL_FIREBASE_API_KEY)
                .build()
            FirebaseApp.initializeApp(app, options)
        }
        if (useEmulator) {
            // Must happen before the first FirebaseAuth call
            FirebaseAuth.getInstance().useEmulator(
                BuildConfig.AL_EMULATOR_HOST,
                BuildConfig.AL_AUTH_EMULATOR_PORT
            )
        }
    }
}
