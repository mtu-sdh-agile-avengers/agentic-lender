package com.example.alaimobileapp.LoanAndCheckers

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
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.LoanStepper
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.StatCard
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Common.formatPercent
import com.example.alaimobileapp.Data.LoanCalculator
import com.example.alaimobileapp.Data.PaymentKind

@Composable
fun StatusScreen(navController: NavHostController, viewModel: LoanViewModel = viewModel()) {
    val application by viewModel.application.collectAsState()
    val app = application

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ScreenHeader("Application status")

        if (app == null) {
            Text("You haven't submitted an application yet.")
            Button(onClick = { navController.navigate("LoanApplication") }, modifier = Modifier.fillMaxWidth()) {
                Text("Start application")
            }
            return@Column
        }

        val a = app.assessment

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(app.statusTitle, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                LoanStepper(app.stepsDone)
                Text(
                    "Digital loan note: ${app.loanNoteState}",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("AL-AI approval likelihood", style = MaterialTheme.typography.labelLarge)
                Text(
                    "${a.approvalLabel} (${a.approvalScore}%)",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                LinearProgressIndicator(progress = { a.approvalScore / 100f }, modifier = Modifier.fillMaxWidth())
                a.tips.forEach { tip ->
                    Text("• $tip", style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            StatCard("LTV", formatPercent(a.ltv), Modifier.weight(1f), caption = "Aim for 80% or less")
            StatCard("DTI", formatPercent(a.dti), Modifier.weight(1f), caption = "Aim for 36% or less")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            StatCard("Loan", formatEuro(a.loanAmount), Modifier.weight(1f))
            StatCard(
                "Monthly",
                formatEuro(a.monthlyPayment),
                Modifier.weight(1f),
                caption = "${app.termYears} yrs at ${(LoanCalculator.ANNUAL_RATE * 100).toInt()}%"
            )
        }

        Text("Speed things up", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        PaymentKind.values().forEach { kind ->
            val paid = app.hasPaid(kind)
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(kind.title, fontWeight = FontWeight.Bold)
                    Text(kind.description, style = MaterialTheme.typography.bodySmall)
                    if (paid) {
                        Text("Paid ✓", color = MaterialTheme.colorScheme.primary)
                    } else {
                        OutlinedButton(onClick = { navController.navigate("MakePayment") }) {
                            Text("Pay ${formatEuro(kind.amountEur)}")
                        }
                    }
                }
            }
        }

        Button(onClick = { navController.navigate("BrokerContact") }, modifier = Modifier.fillMaxWidth()) {
            Text("Message my broker")
        }

        if (!app.isFinished) {
            TextButton(onClick = { viewModel.advanceDemo() }, modifier = Modifier.fillMaxWidth()) {
                Text("Demo: simulate next stage")
            }
        }
    }
}
