package com.example.alaimobileapp.LoginRegister

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.ErrorText
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Data.AppContainer


internal fun goHomeAfterAuth(navController: NavHostController) {
    val route = if (AppContainer.loans.application.value != null) "HomeScreenWithApplication"
    else "HomeScreenNoApplication"
    navController.navigate(route) {
        popUpTo("LoginRegister") { inclusive = true }
    }
}

@Composable
fun Login(navController: NavHostController, viewModel: AuthViewModel = viewModel()) {
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    val state by viewModel.state.collectAsState()
    val onSuccess = { goHomeAfterAuth(navController) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(Modifier.height(32.dp))
        ScreenHeader("Welcome back", "Sign in to continue", Modifier.fillMaxWidth())

        OutlinedTextField(
            value = email,
            onValueChange = { email = it; viewModel.clearError() },
            label = { Text("Email") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it; viewModel.clearError() },
            label = { Text("Password") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth()
        )

        ErrorText(state.error, Modifier.fillMaxWidth())

        Button(
            onClick = { viewModel.login(email, password, onSuccess) },
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (state.loading) "Signing in..." else "Login")
        }

        OutlinedButton(
            onClick = { viewModel.googleSignIn(onSuccess) },
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Continue with Google")
        }

        TextButton(onClick = { navController.navigate("Register") }) {
            Text("New here? Create an account")
        }

        Text(
            "Demo account: demo@alai.ie / Password1",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
