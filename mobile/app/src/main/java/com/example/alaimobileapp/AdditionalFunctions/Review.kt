package com.example.alaimobileapp.AdditionalFunctions

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.ErrorText
import com.example.alaimobileapp.Common.ScreenHeader

@Composable
fun MakeReviewScreen(navController: NavHostController, viewModel: ReviewViewModel = viewModel()) {
    val reviews by viewModel.reviews.collectAsState()
    val submitted by viewModel.submitted.collectAsState()

    var rating by rememberSaveable { mutableIntStateOf(0) }
    var comment by rememberSaveable { mutableStateOf("") }
    var attempted by rememberSaveable { mutableStateOf(false) }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Reviews", "How was your experience with AL Mobile?")

        if (submitted) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Thank you for your review ✓", fontWeight = FontWeight.Bold)
                    Text("Your feedback helps us improve.")
                }
            }
            Button(onClick = { viewModel.reset() }, modifier = Modifier.fillMaxWidth()) {
                Text("Write another review")
            }
        } else {
            Row {
                (1..5).forEach { star ->
                    IconButton(onClick = { rating = star }) {
                        Icon(
                            Icons.Default.Star,
                            contentDescription = "$star star${if (star > 1) "s" else ""}",
                            tint = if (star <= rating) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.outlineVariant
                        )
                    }
                }
            }
            OutlinedTextField(
                value = comment,
                onValueChange = { comment = it },
                label = { Text("Tell us more (optional)") },
                minLines = 4,
                modifier = Modifier.fillMaxWidth()
            )
            if (attempted && rating == 0) ErrorText("Please choose a star rating.")
            Button(
                onClick = {
                    attempted = true
                    if (rating > 0) {
                        viewModel.submit(rating, comment)
                        rating = 0
                        comment = ""
                        attempted = false
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Submit review") }
        }

        if (reviews.isNotEmpty()) {
            HorizontalDivider()
            Text("Your reviews", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            reviews.forEach { r ->
                Column {
                    Text("★".repeat(r.rating) + "☆".repeat(5 - r.rating))
                    if (r.comment.isNotBlank()) Text(r.comment, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}
