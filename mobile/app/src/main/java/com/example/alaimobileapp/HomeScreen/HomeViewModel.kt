package com.example.alaimobileapp.HomeScreen

import androidx.lifecycle.ViewModel
import com.example.alaimobileapp.Data.AppContainer

class HomeViewModel : ViewModel() {
    val user = AppContainer.auth.currentUser
    val application = AppContainer.loans.application
}
