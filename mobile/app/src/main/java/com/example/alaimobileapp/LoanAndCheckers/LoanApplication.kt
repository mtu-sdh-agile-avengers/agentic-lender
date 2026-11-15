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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.NumberField
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Common.formatPercent
import com.example.alaimobileapp.Data.LoanApplicationData
import com.example.alaimobileapp.Data.LoanCalculator

@Composable
fun LoanApplicationScreen(navController: NavHostController, viewModel: LoanViewModel = viewModel()) {
    val existing by viewModel.application.collectAsState()
    val draftValue by viewModel.draftPropertyValue.collectAsState()

    if (existing != null) {
        Column(
            Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            ScreenHeader("Loan application")
            Text("You already have an application in progress.")
            Button(onClick = { navController.navigate("Status") }, modifier = Modifier.fillMaxWidth()) {
                Text("View status")
            }
        }
        return
    }

    var income by rememberSaveable { mutableStateOf("") }
    var debt by rememberSaveable { mutableStateOf("") }
    var deposit by rememberSaveable { mutableStateOf("") }
    var propertyValue by rememberSaveable { mutableStateOf("") }
    var term by rememberSaveable { mutableFloatStateOf(30f) }
    var submitAttempted by rememberSaveable { mutableStateOf(false) }

    // Prefill from the Fair-Price Checker if the user came from there.
    LaunchedEffect(draftValue) {
        val d = draftValue
        if (d != null && propertyValue.isEmpty()) propertyValue = d.toLong().toString()
    }

    val incomeV = income.toDoubleOrNull()
    val debtV = debt.toDoubleOrNull() ?: 0.0
    val depositV = deposit.toDoubleOrNull()
    val valueV = propertyValue.toDoubleOrNull()

    val incomeError = if (submitAttempted && (incomeV == null || incomeV <= 0)) "Enter your annual income" else null
    val valueError = if (submitAttempted && (valueV == null || valueV <= 0)) "Enter the property value" else null
    val depositError = when {
        submitAttempted && depositV == null -> "Enter your deposit"
        depositV != null && valueV != null && depositV >= valueV -> "Deposit must be less than the property value"
        else -> null
    }

    val valid = incomeV != null && incomeV > 0 && valueV != null && valueV > 0 &&
        depositV != null && depositV < valueV

    val preview = if (valid) {
        LoanCalculator.assess(incomeV!!, debtV, depositV!!, term.toInt(), valueV!!)
    } else null

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Loan application", "Tell us about your finances and the property.")

        NumberField("Household annual gross income", income, { income = it }, prefix = "€", error = incomeError)
        NumberField("Existing debt repayments (per month)", debt, { debt = it }, prefix = "€")
        NumberField("Property value", propertyValue, { propertyValue = it }, prefix = "€", error = valueError)
        NumberField("Deposit", deposit, { deposit = it }, prefix = "€", error = depositError)

        Text("Requested term: ${term.toInt()} years", style = MaterialTheme.typography.bodyLarge)
        Slider(value = term, onValueChange = { term = it }, valueRange = 5f..35f, steps = 29)

        if (preview != null) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Live preview", style = MaterialTheme.typography.labelLarge)
                    Text("Loan: ${formatEuro(preview.loanAmount)}", fontWeight = FontWeight.Bold)
                    Text("Monthly repayment: ${formatEuro(preview.monthlyPayment)}")
                    Text("LTV ${formatPercent(preview.ltv)}  |  DTI ${formatPercent(preview.dti)}")
                    Text("Approval likelihood: ${preview.approvalLabel}")
                }
            }
        }

        Button(
            onClick = {
                submitAttempted = true
                if (valid) {
                    viewModel.submit(
                        LoanApplicationData(
                            annualIncome = incomeV!!,
                            monthlyDebt = debtV,
                            deposit = depositV!!,
                            termYears = term.toInt(),
                            propertyValue = valueV!!
                        )
                    )
                    navController.navigate("HomeScreenWithApplication") {
                        popUpTo("HomeScreenNoApplication") { inclusive = true }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Submit application") }

        OutlinedButton(
            onClick = { navController.navigate("PropertyPriceChecker") },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Not sure of the value? Check fair price") }
    }
}
