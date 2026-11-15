package com.example.alaimobileapp.HomeScreen

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ListItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Data.AppContainer

@Composable
fun MoreScreen(navController: NavHostController) {
    @Composable
    fun Entry(title: String, subtitle: String, onClick: () -> Unit) {
        ListItem(
            headlineContent = { Text(title) },
            supportingContent = { Text(subtitle) },
            modifier = Modifier.clickable(onClick = onClick)
        )
        HorizontalDivider()
    }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        ScreenHeader("More")
        Entry("Make Payment", "Verification fee and fast-track appraisal") { navController.navigate("MakePayment") }
        Entry("Fair-Price Property Checker", "Estimate what a property is worth") { navController.navigate("PropertyPriceChecker") }
        Entry("Borrowing estimator", "How much could I borrow?") { navController.navigate("BorrowAmountEstimator") }
        Entry("Support", "Ask us a question") { navController.navigate("Support") }
        Entry("Reviews", "Rate your experience") { navController.navigate("MakeReview") }
        Entry("Sign out", "Log out of this device") {
            AppContainer.signOut()
            navController.navigate("LoginRegister") {
                popUpTo(navController.graph.id) { inclusive = true }
            }
        }
    }
}
