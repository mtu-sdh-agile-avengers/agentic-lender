package com.example.alaimobileapp.HomeScreen

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.ScreenHeader

@Composable
fun HomeScreenNoApplication(navController: NavHostController, viewModel: HomeViewModel = viewModel()) {
    val user by viewModel.user.collectAsState()
    val firstName = user?.name?.substringBefore(' ') ?: ""

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ScreenHeader("Hello, $firstName", "Let's get you started with your mortgage.")

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("No application yet", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(
                    "Start an application to see your loan-to-value, debt-to-income and approval likelihood.",
                    style = MaterialTheme.typography.bodyMedium
                )
                Button(onClick = { navController.navigate("LoanApplication") }, modifier = Modifier.fillMaxWidth()) {
                    Text("Start loan application")
                }
            }
        }

        Text("Quick Actions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

        OutlinedButton(
            onClick = { navController.navigate("BorrowAmountEstimator") },
            modifier = Modifier.fillMaxWidth()
        ) { Text("How much can I borrow?") }

        OutlinedButton(
            onClick = { navController.navigate("PropertyPriceChecker") },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Check a property's fair price") }

        OutlinedButton(
            onClick = { navController.navigate("BrokerContact") },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Talk to a broker") }
    }
}
