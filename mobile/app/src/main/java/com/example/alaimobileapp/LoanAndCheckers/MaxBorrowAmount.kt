package com.example.alaimobileapp.LoanAndCheckers

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.NumberField
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Data.LoanCalculator

@Composable
fun BorrowAmountEstimatorScreen(navController: NavHostController) {
    var income by rememberSaveable { mutableStateOf("") }
    var debt by rememberSaveable { mutableStateOf("") }
    var deposit by rememberSaveable { mutableStateOf("") }
    var term by rememberSaveable { mutableFloatStateOf(30f) }

    val incomeV = income.toDoubleOrNull() ?: 0.0
    val debtV = debt.toDoubleOrNull() ?: 0.0
    val depositV = deposit.toDoubleOrNull() ?: 0.0
    val result = if (incomeV > 0) LoanCalculator.maxBorrow(incomeV, debtV, depositV, term.toInt()) else null

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("How much can I borrow?", "A quick, indicative estimate.")

        NumberField("Household annual gross income", income, { income = it }, prefix = "€")
        NumberField("Existing debt repayments (per month)", debt, { debt = it }, prefix = "€")
        NumberField("Deposit", deposit, { deposit = it }, prefix = "€")

        Text("Mortgage term: ${term.toInt()} years", style = MaterialTheme.typography.bodyLarge)
        Slider(value = term, onValueChange = { term = it }, valueRange = 5f..35f, steps = 29)

        if (result != null) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("You could borrow up to", style = MaterialTheme.typography.labelLarge)
                    Text(
                        formatEuro(result.maxLoan),
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        "Property price up to ${formatEuro(result.maxPropertyPrice)} with your deposit.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Text(
                        "Limited by ${result.limitingFactor}.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        Text(
            "Assumes a ${(LoanCalculator.ANNUAL_RATE * 100).toInt()}% interest rate. This is a guide, not a loan offer.",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Button(
            onClick = { navController.navigate("LoanApplication") },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Start an application") }
    }
}
