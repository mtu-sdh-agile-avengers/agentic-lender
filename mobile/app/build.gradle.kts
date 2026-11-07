plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

// Where the app finds AL-Core and the Firebase emulators. Defaults suit the Android emulator
// (10.0.2.2 = the host machine, where `docker compose up` runs). For a physical phone, set your
// computer's LAN IP in ~/.gradle/gradle.properties, e.g.:
//   al.apiBaseUrl=http://192.168.1.20:8000
//   al.emulatorHost=192.168.1.20
val alApiBaseUrl = providers.gradleProperty("al.apiBaseUrl").getOrElse("http://10.0.2.2:8000")
val alEmulatorHost = providers.gradleProperty("al.emulatorHost").getOrElse("10.0.2.2")
val alAuthEmulatorPort = providers.gradleProperty("al.authEmulatorPort").getOrElse("9099")
val alFirebaseProjectId = providers.gradleProperty("al.firebaseProjectId").getOrElse("demo-agentic-lender")

android {
    namespace = "com.example.alaimobileapp"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.example.alaimobileapp"
        minSdk = 35
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("String", "AL_API_BASE_URL", "\"$alApiBaseUrl\"")
        buildConfigField("String", "AL_EMULATOR_HOST", "\"$alEmulatorHost\"")
        buildConfigField("int", "AL_AUTH_EMULATOR_PORT", alAuthEmulatorPort)
        buildConfigField("String", "AL_FIREBASE_PROJECT_ID", "\"$alFirebaseProjectId\"")
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