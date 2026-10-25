package com.example.alaimobileapp.AdditionalFunctions

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.ErrorText
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Common.formatEuro
import com.example.alaimobileapp.Data.PaymentKind
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun PaymentScreen(navController: NavHostController, viewModel: PaymentViewModel = viewModel()) {
    val application by viewModel.application.collectAsState()
    val history by viewModel.history.collectAsState()
    val state by viewModel.state.collectAsState()
    val app = application

    var selected by rememberSaveable { mutableStateOf(PaymentKind.VERIFICATION_FEE) }
    var holder by rememberSaveable { mutableStateOf("") }
    var number by rememberSaveable { mutableStateOf("") }
    var expiry by rememberSaveable { mutableStateOf("") }
    var cvc by rememberSaveable { mutableStateOf("") }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Make Payment", "Sandbox mode: no real money is taken.")

        if (app == null) {
            Text("Submit a loan application first, then you can pay the verification fee or fast-track your appraisal.")
            Button(onClick = { navController.navigate("LoanApplication") }, modifier = Modifier.fillMaxWidth()) {
                Text("Start application")
            }
        } else if (state.success != null) {
            val record = state.success!!
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Payment successful ✓", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("${record.kind.title}: ${formatEuro(record.amountEur)}")
                    Text("Card ending ${record.last4}  |  Ref ${record.id}", style = MaterialTheme.typography.bodySmall)
                }
            }
            Button(onClick = { navController.navigate("Status") }, modifier = Modifier.fillMaxWidth()) {
                Text("See application status")
            }
            Button(onClick = { viewModel.dismissResult() }, modifier = Modifier.fillMaxWidth()) {
                Text("Make another payment")
            }
        } else {
            PaymentKind.values().forEach { kind ->
                val paid = app.hasPaid(kind)
                Card(Modifier.fillMaxWidth()) {
                    Row(
                        Modifier
                            .selectable(
                                selected = selected == kind,
                                enabled = !paid,
                                role = Role.RadioButton,
                                onClick = { selected = kind }
                            )
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(selected = selected == kind, onClick = null, enabled = !paid)
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(kind.title, fontWeight = FontWeight.Bold)
                            Text(kind.description, style = MaterialTheme.typography.bodySmall)
                        }
                        Text(if (paid) "Paid ✓" else formatEuro(kind.amountEur), fontWeight = FontWeight.Bold)
                    }
                }
            }

            if (app.hasPaid(selected)) {
                Text("You've already paid for this item.")
            } else {
                Text("Card details", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                OutlinedTextField(
                    value = holder,
                    onValueChange = { holder = it },
                    label = { Text("Name on card") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = number,
                    onValueChange = { number = it.filter { c -> c.isDigit() }.take(16) },
                    label = { Text("Card number") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedTextField(
                        value = expiry,
                        onValueChange = { expiry = it.filter { c -> c.isDigit() || c == '/' }.take(5) },
                        label = { Text("MM/YY") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = cvc,
                        onValueChange = { cvc = it.filter { c -> c.isDigit() }.take(4) },
                        label = { Text("CVC") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.weight(1f)
                    )
                }
                Text(
                    "Test card: 4242 4242 4242 4242, any future date, any CVC. 4000 0000 0000 0002 simulates a decline.",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                ErrorText(state.error)

                Button(
                    onClick = { viewModel.pay(selected, number, expiry, cvc, holder) },
                    enabled = !state.processing,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (state.processing) "Processing..." else "Pay ${formatEuro(selected.amountEur)}")
                }
            }
        }

        if (history.isNotEmpty()) {
            HorizontalDivider()
            Text("Payment history", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            history.forEach { record ->
                val date = SimpleDateFormat("d MMM yyyy, HH:mm", Locale.getDefault()).format(Date(record.timestamp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f)) {
                        Text(record.kind.title)
                        Text(
                            "$date  |  •••• ${record.last4}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Text(formatEuro(record.amountEur))
                }
            }
        }
    }
}
