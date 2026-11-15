package com.example.alaimobileapp.HomeScreen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.LoanStepper
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.StatCard
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Common.formatPercent

@Composable
fun HomeScreenApplication(navController: NavHostController, viewModel: HomeViewModel = viewModel()) {
    val user by viewModel.user.collectAsState()
    val application by viewModel.application.collectAsState()
    val firstName = user?.name?.substringBefore(' ') ?: ""
    val app = application

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ScreenHeader("Hello, $firstName")

        if (app == null) {
            Text("No application found.")
            Button(onClick = { navController.navigate("LoanApplication") }) { Text("Start application") }
        } else {
            val a = app.assessment

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Loan Application Status", style = MaterialTheme.typography.labelLarge)
                    Text(app.statusTitle, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    LoanStepper(app.stepsDone)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard("Loan Value", formatEuro(a.loanAmount), Modifier.weight(1f))
                StatCard("Property value", formatEuro(app.propertyValue), Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                StatCard("LTV", formatPercent(a.ltv), Modifier.weight(1f), caption = "Loan-to-value")
                StatCard("DTI", formatPercent(a.dti), Modifier.weight(1f), caption = "Debt-to-income")
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("AL-AI approval likelihood", style = MaterialTheme.typography.labelLarge)
                    Text(
                        "${a.approvalLabel} (${a.approvalScore}%)",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    LinearProgressIndicator(
                        progress = { a.approvalScore / 100f },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            Text("Quick Actions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FilledTonalButton(
                    onClick = { navController.navigate("PropertyPriceChecker") },
                    modifier = Modifier.weight(1f)
                ) { Text("Check Property Value", textAlign = TextAlign.Center) }
                FilledTonalButton(
                    onClick = { navController.navigate("MakePayment") },
                    modifier = Modifier.weight(1f)
                ) { Text("Make Payment", textAlign = TextAlign.Center) }
            }
            Button(onClick = { navController.navigate("Status") }, modifier = Modifier.fillMaxWidth()) {
                Text("View full status")
            }
        }
    }
}
