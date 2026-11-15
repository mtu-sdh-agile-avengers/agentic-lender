plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

// Where the app finds AL-Core and Firebase. Defaults suit the Android emulator (10.0.2.2 = the host
// machine, where `docker compose up` runs) and the Firebase emulator suite. Override in
// ~/.gradle/gradle.properties (never commit keys), e.g. for a physical phone:
//   al.apiBaseUrl=http://192.168.1.20:8000
//   al.emulatorHost=192.168.1.20
// and for the real Firebase project (AL-Core must run with FIREBASE_MODE=cloud too):
//   al.firebaseMode=cloud
// plus app/google-services.json (Firebase Console -> Project settings -> Your apps -> Android;
// gitignored, share it privately). Without that file, give al.firebaseApiKey + al.firebaseAppId instead.
val alApiBaseUrl = providers.gradleProperty("al.apiBaseUrl").getOrElse("http://10.0.2.2:8000")
val alEmulatorHost = providers.gradleProperty("al.emulatorHost").getOrElse("10.0.2.2")
val alAuthEmulatorPort = providers.gradleProperty("al.authEmulatorPort").getOrElse("9099")
val alUseFirebaseEmulator = providers.gradleProperty("al.firebaseMode").getOrElse("emulator") != "cloud"
val alFirebaseProjectId = providers.gradleProperty("al.firebaseProjectId")
    .getOrElse(if (alUseFirebaseEmulator) "demo-agentic-lender" else "agentic-lender")
val alFirebaseApiKey = providers.gradleProperty("al.firebaseApiKey").getOrElse("")
val alFirebaseAppId = providers.gradleProperty("al.firebaseAppId").getOrElse("")

// google-services.json is optional: teammates without it still build (emulator mode).
// When present, the Google services plugin turns it into resources that cloud mode reads.
val hasGoogleServicesJson = layout.projectDirectory.file("google-services.json").asFile.exists()
if (hasGoogleServicesJson) {
    apply(plugin = "com.google.gms.google-services")
}
if (!alUseFirebaseEmulator && !hasGoogleServicesJson && (alFirebaseApiKey.isBlank() || alFirebaseAppId.isBlank())) {
    throw GradleException(
        "al.firebaseMode=cloud needs mobile/app/google-services.json, or al.firebaseApiKey and al.firebaseAppId " +
            "in ~/.gradle/gradle.properties (see docs/run-guide.md, 'Real Firebase')."
    )
}

android {
    namespace = "com.example.alaimobileapp"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        // must match the Android app registered in Firebase (google-services.json)
        applicationId = "io.github.mtu_sdh_agile_avengers.agenticlender.client"
        minSdk = 35
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "AL_API_BASE_URL", "\"$alApiBaseUrl\"")
        buildConfigField("String", "AL_EMULATOR_HOST", "\"$alEmulatorHost\"")
        buildConfigField("int", "AL_AUTH_EMULATOR_PORT", alAuthEmulatorPort)
        buildConfigField("String", "AL_FIREBASE_PROJECT_ID", "\"$alFirebaseProjectId\"")
        buildConfigField("boolean", "AL_USE_FIREBASE_EMULATOR", alUseFirebaseEmulator.toString())
        buildConfigField("String", "AL_FIREBASE_API_KEY", "\"$alFirebaseApiKey\"")
        buildConfigField("String", "AL_FIREBASE_APP_ID", "\"$alFirebaseAppId\"")
    }

    buildTypes {
        release {
            optimization {
                enable = false
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.material.icons.core)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    // Firebase Auth (sign-in) + OkHttp (calls to AL-Core)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.auth)
    implementation(libs.kotlinx.coroutines.play.services)
    implementation(libs.okhttp)
    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)

}