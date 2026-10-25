package com.example.alaimobileapp.AdditionalFunctions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.example.alaimobileapp.Common.DropdownField
import com.example.alaimobileapp.Common.ErrorText
import com.example.alaimobileapp.Common.ScreenHeader
import com.example.alaimobileapp.Data.SupportTopic

private val faqs = listOf(
    "How is my approval likelihood calculated?" to
        "AL-AI looks at your loan-to-value (LTV), debt-to-income (DTI) and how the loan compares with your income. Lower LTV and DTI mean a higher likelihood.",
    "What is the verification fee for?" to
        "It covers checking your income, debts and deposit documents. Paying it moves your application to the Verification stage.",
    "How accurate is the Fair-Price Checker?" to
        "It gives a quick estimate from an automated model. It isn't a formal valuation; request a fast-track appraisal for that.",
    "Can I change my application after submitting?" to
        "Message your broker from the Broker tab and they can update it for you."
)

@Composable
fun SupportScreen(navController: NavHostController, viewModel: SupportViewModel = viewModel()) {
    val tickets by viewModel.tickets.collectAsState()
    val lastTicket by viewModel.lastTicket.collectAsState()

    var topic by rememberSaveable { mutableStateOf(SupportTopic.APPLICATION) }
    var subject by rememberSaveable { mutableStateOf("") }
    var message by rememberSaveable { mutableStateOf("") }
    var attempted by rememberSaveable { mutableStateOf(false) }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ScreenHeader("Support", "Find an answer or send us a message.")

        Text("Common questions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        faqs.forEach { (question, answer) -> FaqItem(question, answer) }

        HorizontalDivider()
        Text("Contact support", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

        val confirmation = lastTicket
        if (confirmation != null) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Request ${confirmation.ref} received ✓", fontWeight = FontWeight.Bold)
                    Text(confirmation.autoReply, style = MaterialTheme.typography.bodyMedium)
                }
            }
            Button(onClick = { viewModel.dismissConfirmation() }, modifier = Modifier.fillMaxWidth()) {
                Text("Send another message")
            }
        } else {
            DropdownField("Topic", SupportTopic.values().toList(), topic, { it.label }, { topic = it })
            OutlinedTextField(
                value = subject,
                onValueChange = { subject = it },
                label = { Text("Subject") },
                singleLine = true,
                isError = attempted && subject.isBlank(),
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = message,
                onValueChange = { message = it },
                label = { Text("How can we help?") },
                minLines = 4,
                isError = attempted && message.isBlank(),
                modifier = Modifier.fillMaxWidth()
            )
            if (attempted && (subject.isBlank() || message.isBlank())) {
                ErrorText("Please add a subject and a message.")
            }
            Button(
                onClick = {
                    attempted = true
                    if (subject.isNotBlank() && message.isNotBlank()) {
                        viewModel.submit(topic, subject, message)
                        subject = ""
                        message = ""
                        attempted = false
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) { Text("Send") }
        }

        if (tickets.isNotEmpty()) {
            HorizontalDivider()
            Text("Your requests", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            tickets.forEach { t ->
                Column {
                    Text("${t.ref}: ${t.subject}", fontWeight = FontWeight.Bold)
                    Text(t.topic.label, style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}

@Composable
private fun FaqItem(question: String, answer: String) {
    var open by rememberSaveable(question) { mutableStateOf(false) }
    Card(Modifier.fillMaxWidth().clickable { open = !open }) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(question, fontWeight = FontWeight.Bold)
            if (open) Text(answer, style = MaterialTheme.typography.bodyMedium)
        }
    }
}
