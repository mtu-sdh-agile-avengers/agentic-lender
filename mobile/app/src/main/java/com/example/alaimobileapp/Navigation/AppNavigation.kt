package com.example.alaimobileapp.Navigation

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalDensity
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.example.alaimobileapp.AdditionalFunctions.BrokerContactScreen
import com.example.alaimobileapp.AdditionalFunctions.MakeReviewScreen
import com.example.alaimobileapp.AdditionalFunctions.PaymentScreen
import com.example.alaimobileapp.AdditionalFunctions.SupportScreen
import com.example.alaimobileapp.Data.AppContainer
import com.example.alaimobileapp.HomeScreen.HomeScreenApplication
import com.example.alaimobileapp.HomeScreen.HomeScreenNoApplication
import com.example.alaimobileapp.HomeScreen.MoreScreen
import com.example.alaimobileapp.LoanAndCheckers.BorrowAmountEstimatorScreen
import com.example.alaimobileapp.LoanAndCheckers.LoanApplicationScreen
import com.example.alaimobileapp.LoanAndCheckers.PropertyPriceCheckerScreen
import com.example.alaimobileapp.LoanAndCheckers.StatusScreen
import com.example.alaimobileapp.LoginRegister.Login
import com.example.alaimobileapp.LoginRegister.LoginRegister
import com.example.alaimobileapp.LoginRegister.Register

private val AUTH_ROUTES = setOf("LoginRegister", "Login", "Register")

private data class BottomItem(
    val label: String,
    val icon: ImageVector,
    val target: String,
    val routes: Set<String>
)

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val route = backStackEntry?.destination?.route

    val application by AppContainer.loans.application.collectAsState()
    val homeRoute = if (application != null) "HomeScreenWithApplication" else "HomeScreenNoApplication"
    val applicationRoute = if (application != null) "Status" else "LoanApplication"

    // Hide the bottom bar while the keyboard is open (e.g. when typing in the broker chat).
    val imeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
    val showBar = route != null && route !in AUTH_ROUTES && !imeVisible

    val items = listOf(
        BottomItem("Home", Icons.Default.Home, homeRoute,
            setOf("HomeScreenNoApplication", "HomeScreenWithApplication")),
        BottomItem("Application", Icons.Default.Edit, applicationRoute,
            setOf("LoanApplication", "Status", "BorrowAmountEstimator")),
        BottomItem("Broker", Icons.Default.Email, "BrokerContact",
            setOf("BrokerContact")),
        BottomItem("More", Icons.Default.Menu, "More",
            setOf("More", "MakePayment", "MakeReview", "Support", "PropertyPriceChecker"))
    )

    Scaffold(
        bottomBar = {
            if (showBar) {
                NavigationBar {
                    items.forEach { item ->
                        NavigationBarItem(
                            selected = route in item.routes,
                            onClick = {
                                if (route != item.target) {
                                    navController.navigate(item.target) {
                                        popUpTo(homeRoute) { inclusive = item.target == homeRoute }
                                        launchSingleTop = true
                                    }
                                }
                            },
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label) }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = "LoginRegister",
            modifier = Modifier
                .padding(innerPadding)
                .consumeWindowInsets(innerPadding)
                .imePadding()
        ) {
            composable("LoginRegister") { LoginRegister(navController) }
            composable("Login") { Login(navController) }
            composable("Register") { Register(navController) }
            composable("HomeScreenNoApplication") { HomeScreenNoApplication(navController) }
            composable("HomeScreenWithApplication") { HomeScreenApplication(navController) }
            composable("PropertyPriceChecker") { PropertyPriceCheckerScreen(navController) }
            composable("BorrowAmountEstimator") { BorrowAmountEstimatorScreen(navController) }
            composable("LoanApplication") { LoanApplicationScreen(navController) }
            composable("Status") { StatusScreen(navController) }
            composable("BrokerContact") { BrokerContactScreen(navController) }
            composable("MakePayment") { PaymentScreen(navController) }
            composable("MakeReview") { MakeReviewScreen(navController) }
            composable("Support") { SupportScreen(navController) }
            composable("More") { MoreScreen(navController) }
        }
    }
}
