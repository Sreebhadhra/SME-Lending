from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from users.models import User
from django.apps import apps


class DigiLedger(models.Model):
    """
    CRITICAL END-USE MONITORING SYSTEM
    Tracks every rupee from disbursement to final spend
    PREVENTS fund diversion
    """

    class TransactionType(models.TextChoices):
        DISBURSEMENT = 'DISB', 'Loan Disbursement'
        CARD_PAYMENT = 'CARD', 'Green Card Payment'
        UPI_PAYMENT = 'UPI', 'Green UPI Payment'
        NEFT_RTGS = 'NEFT', 'NEFT/RTGS Payment'
        REFUND = 'REFUND', 'Refund'
        ADJUSTMENT = 'ADJ', 'Adjustment'

    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
        FLAGGED = 'FLAGGED', 'Flagged for Review'

    # Core identification
    transaction_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique transaction identifier"
    )

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='ledger_entries'
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ledger_transactions'
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )

    transaction_date = models.DateTimeField(default=timezone.now)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # END-USE TRACKING (Critical)
    vendor = models.ForeignKey(
        'vendors.VendorRegistry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ledger_transactions'
    )

    # Invoice mandatory for compliance
    invoice_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="MANDATORY for all vendor payments"
    )
    invoice_date = models.DateField(blank=True, null=True)
    invoice_file = models.FileField(
        upload_to='ledger/invoices/%Y/%m/',
        blank=True,
        null=True
    )

    description = models.TextField()

    # Category validation
    merchant_category_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="MCC for card transactions"
    )

    # Compliance
    status = models.CharField(
        max_length=10,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )

    green_compliant = models.BooleanField(
        default=False,
        help_text="Transaction aligns with loan purpose"
    )

    # Fraud detection
    fraud_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MinValueValidator(Decimal('100'))],
        help_text="0=Clean, 100=High Risk"
    )

    flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)

    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_ledger_entries'
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    # Payment reference
    payment_reference = models.CharField(max_length=100, blank=True)
    utr_number = models.CharField(max_length=50, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Running balance
    balance_after_transaction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'digi_ledger'
        ordering = ['-transaction_date']
        verbose_name = 'Ledger Entry'
        verbose_name_plural = 'Digi-Ledger'
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['loan_account', 'transaction_date']),
            models.Index(fields=['vendor']),
        ]

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount}"

    def validate_transaction(self):
        """
        CORE END-USE VALIDATION
        Checks if transaction complies with loan purpose
        """
        flags = []

        # Check 1: Vendor approved?
        if self.vendor:
            if not self.vendor.is_eligible_for_green_transactions:
                flags.append("Vendor not approved for green transactions")
                self.fraud_score += Decimal('40.00')
        else:
            # No vendor specified for vendor payment
            if self.transaction_type in [
                self.TransactionType.CARD_PAYMENT,
                self.TransactionType.UPI_PAYMENT
            ]:
                flags.append("Vendor not specified")
                self.fraud_score += Decimal('20.00')

        # Check 2: Invoice attached?
        if self.transaction_type != self.TransactionType.DISBURSEMENT:
            if not self.invoice_number or not self.invoice_file:
                flags.append("Invoice missing")
                self.fraud_score += Decimal('30.00')

        # Check 3: Category match
        green_mccs = ['5541', '5983', '8999']  # Example green MCCs
        if self.merchant_category_code and self.merchant_category_code not in green_mccs:
            flags.append("Merchant category not aligned with green purpose")
            self.fraud_score += Decimal('25.00')

        # Check 4: Amount threshold
        if self.amount > Decimal('100000'):  # Large transaction
            if not self.invoice_file:
                flags.append("Large transaction without invoice")
                self.fraud_score += Decimal('20.00')

        # Cap fraud score
        self.fraud_score = min(self.fraud_score, Decimal('100.00'))

        # Flag if high risk
        if self.fraud_score >= Decimal('50.00'):
            self.flagged = True
            self.flag_reason = "; ".join(flags)
            self.status = self.TransactionStatus.FLAGGED
        else:
            self.green_compliant = True

        self.save()

        return flags

    def approve_transaction(self, user):
        """Approve a flagged transaction"""
        self.approved_by = user
        self.approved_at = timezone.now()
        self.status = self.TransactionStatus.APPROVED
        self.flagged = False
        self.save()

    def reject_transaction(self, user, reason):
        """Reject a transaction"""
        self.approved_by = user
        self.approved_at = timezone.now()
        self.status = self.TransactionStatus.REJECTED
        self.flag_reason = reason
        self.save()


class GreenCardTransaction(models.Model):
    """
    GREEN CARD TRANSACTION LOG
    Virtual card linked to loan account with automatic vendor validation
    """

    card_number_masked = models.CharField(max_length=20)

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='card_transactions'
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='card_transactions'
    )

    # Transaction details
    transaction_id = models.CharField(max_length=50, unique=True)
    transaction_date = models.DateTimeField(default=timezone.now)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Merchant details
    merchant_name = models.CharField(max_length=255)
    merchant_category_code = models.CharField(max_length=10)

    vendor = models.ForeignKey(
        'vendors.VendorRegistry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_transactions'
    )

    # Real-time validation
    approved_realtime = models.BooleanField(
        default=False,
        help_text="Auto-approved if vendor is whitelisted"
    )

    blocked = models.BooleanField(
        default=False,
        help_text="Blocked if vendor not approved"
    )
    block_reason = models.CharField(max_length=255, blank=True)

    # Link to ledger
    ledger_entry = models.OneToOneField(
        DigiLedger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='card_transaction'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'green_card_transactions'
        ordering = ['-transaction_date']
        verbose_name = 'Green Card Transaction'
        verbose_name_plural = 'Green Card Transactions'

    def __str__(self):
        return f"{self.transaction_id} - {self.merchant_name} - ₹{self.amount}"

    def process_transaction(self):
        """
        REAL-TIME END-USE CONTROL
        Automatically approves/blocks based on vendor registry
        """
        # Check if merchant is in approved vendor list
        if self.vendor and self.vendor.is_eligible_for_green_transactions:
            self.approved_realtime = True
            self.blocked = False

            # Create ledger entry
            ledger = DigiLedger.objects.create(
                transaction_id=self.transaction_id,
                loan_account=self.loan_account,
                borrower=self.borrower,
                transaction_type=DigiLedger.TransactionType.CARD_PAYMENT,
                transaction_date=self.transaction_date,
                amount=self.amount,
                vendor=self.vendor,
                description=f"Card payment to {self.merchant_name}",
                merchant_category_code=self.merchant_category_code,
                status=DigiLedger.TransactionStatus.APPROVED,
                green_compliant=True
            )
            self.ledger_entry = ledger

        else:
            # Block transaction
            self.blocked = True
            self.block_reason = "Vendor not in approved list"

            # Create flagged ledger entry
            ledger = DigiLedger.objects.create(
                transaction_id=self.transaction_id,
                loan_account=self.loan_account,
                borrower=self.borrower,
                transaction_type=DigiLedger.TransactionType.CARD_PAYMENT,
                transaction_date=self.transaction_date,
                amount=self.amount,
                description=f"BLOCKED: Card payment to {self.merchant_name}",
                merchant_category_code=self.merchant_category_code,
                status=DigiLedger.TransactionStatus.FLAGGED,
                flagged=True,
                flag_reason="Merchant not in approved vendor list",
                fraud_score=Decimal('80.00')
            )
            self.ledger_entry = ledger

        self.save()


class GreenUPITransaction(models.Model):
    """
    GREEN UPI WALLET TRANSACTIONS
    UPI payments with invoice validation
    """

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='upi_transactions'
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='upi_transactions'
    )

    # UPI details
    upi_transaction_id = models.CharField(max_length=50, unique=True)
    upi_ref_number = models.CharField(max_length=50)

    transaction_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Payee
    payee_vpa = models.CharField(max_length=100)
    payee_name = models.CharField(max_length=255)

    vendor = models.ForeignKey(
        'vendors.VendorRegistry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='upi_transactions'
    )

    # MANDATORY INVOICE
    invoice_number = models.CharField(max_length=100)
    invoice_file = models.FileField(upload_to='ledger/upi_invoices/%Y/%m/')

    # Validation
    validated = models.BooleanField(default=False)
    validation_notes = models.TextField(blank=True)

    # Link to ledger
    ledger_entry = models.OneToOneField(
        DigiLedger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='upi_transaction'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'green_upi_transactions'
        ordering = ['-transaction_date']
        verbose_name = 'Green UPI Transaction'
        verbose_name_plural = 'Green UPI Transactions'

    def __str__(self):
        return f"{self.upi_transaction_id} - {self.payee_name} - ₹{self.amount}"


class LedgerBalance(models.Model):
    """
    Real-time balance tracking per loan account
    """
    loan_account = models.OneToOneField(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='ledger_balance'
    )

    total_disbursed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    available_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Compliance metrics
    green_compliant_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    flagged_spend = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ledger_balances'
        verbose_name = 'Ledger Balance'
        verbose_name_plural = 'Ledger Balances'

    def __str__(self):
        return f"{self.loan_account.account_number} - Balance: ₹{self.available_balance}"

    @property
    def utilization_percentage(self):
        if self.total_disbursed == 0:
            return 0
        return (self.total_spent / self.total_disbursed) * 100

    @property
    def compliance_percentage(self):
        if self.total_spent == 0:
            return 100
        return (self.green_compliant_spend / self.total_spent) * 100
