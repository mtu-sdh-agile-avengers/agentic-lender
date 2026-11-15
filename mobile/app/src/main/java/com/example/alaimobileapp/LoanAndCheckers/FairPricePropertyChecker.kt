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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.DropdownField
import com.example.alaimobileapp.Common.ErrorText
import com.example.alaimobileapp.Common.NumberField
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Data.BerRating
import com.example.alaimobileapp.Data.Counties
import com.example.alaimobileapp.Data.PriceVerdict
import com.example.alaimobileapp.Data.PropertySpec
import com.example.alaimobileapp.Data.PropertyType
import kotlin.math.abs

@Composable
fun PropertyPriceCheckerScreen(navController: NavHostController, viewModel: PropertyViewModel = viewModel()) {
    var county by rememberSaveable { mutableStateOf<String?>(null) }
    var sqm by rememberSaveable { mutableStateOf("") }
    var bedrooms by rememberSaveable { mutableStateOf<Int?>(null) }
    var type by rememberSaveable { mutableStateOf<PropertyType?>(null) }
    var ber by rememberSaveable { mutableStateOf<BerRating?>(null) }
    var asking by rememberSaveable { mutableStateOf("") }
    var attempted by rememberSaveable { mutableStateOf(false) }

    val state by viewModel.state.collectAsState()

    val sqmV = sqm.toDoubleOrNull()
    val ready = county != null && sqmV != null && sqmV > 0 && bedrooms != null && type != null && ber != null

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Fair-Price Checker", "Estimate what a property should cost.")

        DropdownField("County", Counties.names, county, { it }, { county = it })
        NumberField(
            "Size", sqm, { sqm = it }, suffix = "m²",
            error = if (attempted && (sqmV == null || sqmV <= 0)) "Enter the floor area" else null
        )
        DropdownField("Bedrooms", (1..6).toList(), bedrooms, { "$it" }, { bedrooms = it })
        DropdownField("Property type", PropertyType.values().toList(), type, { it.label }, { type = it })
        DropdownField("BER energy rating", BerRating.values().toList(), ber, { it.label }, { ber = it })
        NumberField("Asking price (optional)", asking, { asking = it }, prefix = "€")

        if (attempted && !ready) {
            ErrorText("Please fill in every field above.")
        }

        Button(
            onClick = {
                attempted = true
                if (ready) {
                    viewModel.check(
                        PropertySpec(
                            county = county!!,
                            sqm = sqmV!!,
                            bedrooms = bedrooms!!,
                            type = type!!,
                            ber = ber!!,
                            askingPrice = asking.toDoubleOrNull()
                        )
                    )
                }
            },
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth()
        ) { Text(if (state.loading) "Estimating..." else "Get valuation") }

        ErrorText(state.error)

        val result = state.result
        if (result != null) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Estimated value", style = MaterialTheme.typography.labelLarge)
                    Text(
                        formatEuro(result.estimate),
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text("Likely range ${formatEuro(result.low)} to ${formatEuro(result.high)}")
                    Text("About ${formatEuro(result.pricePerSqm)} per m²")

                    val verdict = result.verdict
                    val diff = result.differencePct
                    if (verdict != null && diff != null) {
                        val direction = if (diff >= 0) "above" else "below"
                        Text(
                            "${verdict.label}: the asking price is ${String.format("%.0f", abs(diff))}% $direction the estimate.",
                            fontWeight = FontWeight.Bold,
                            color = if (verdict == PriceVerdict.OVERPRICED) MaterialTheme.colorScheme.error
                            else MaterialTheme.colorScheme.primary
                        )
                    }
                    Text(
                        "Estimate from a prototype model. Not a formal valuation.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            OutlinedButton(
                onClick = {
                    viewModel.useForApplication(result.estimate)
                    navController.navigate("LoanApplication")
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Use this value in my application") }
        }
    }
}
