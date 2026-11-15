package com.example.alaimobileapp

import com.example.alaimobileapp.Data.LoanCalculator
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LoanCalculatorTest {
    @Test
    fun ltvIsLoanOverPropertyValue() {
        val a = LoanCalculator.assess(100_000.0, 0.0, 100_000.0, 30, 400_000.0)
        assertEquals(75.0, a.ltv, 0.001)
        assertEquals(300_000.0, a.loanAmount, 0.001)
    }

    @Test
    fun principalAndPaymentAreInverse() {
        val payment = LoanCalculator.monthlyPayment(250_000.0, 25)
        assertEquals(250_000.0, LoanCalculator.principalFor(payment, 25), 0.01)
    }

    @Test
    fun highLtvLowersApproval() {
        val safe = LoanCalculator.assess(120_000.0, 0.0, 100_000.0, 30, 400_000.0)
        val risky = LoanCalculator.assess(120_000.0, 0.0, 10_000.0, 30, 400_000.0)
        assertTrue(risky.approvalScore < safe.approvalScore)
    }

    @Test
    fun maxBorrowNeverExceedsFourTimesIncome() {
        val m = LoanCalculator.maxBorrow(80_000.0, 0.0, 500_000.0, 30)
        assertTrue(m.maxLoan <= 320_000.0 + 0.01)
    }
}
