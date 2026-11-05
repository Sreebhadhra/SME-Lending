from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from users.models import User
from ledger.models import DigiLedger


class ComplianceAlert(models.Model):
    """
    FRAUD DETECTION & COMPLIANCE ALERTS
    Monitors for fund diversion and covenant breaches
    """

    class AlertType(models.TextChoices):
        INVOICE_MISMATCH = 'INV_MIS', 'Invoice Mismatch'
        NON_GREEN_VENDOR = 'NON_GREEN', 'Non-Green Vendor Transaction'
        SPENDING_OUTSIDE_PURPOSE = 'OFF_PURPOSE', 'Spending Outside Purpose'
        HIGH_FRAUD_SCORE = 'FRAUD', 'High Fraud Score'
        MISSING_INVOICE = 'NO_INV', 'Missing Invoice'
        DUPLICATE_INVOICE = 'DUP_INV', 'Duplicate Invoice'
        COVENANT_BREACH = 'COVENANT', 'Covenant Breach'
        OVERUTILIZATION = 'OVERUTIL', 'Over-utilization'
        SUSPICIOUS_PATTERN = 'PATTERN', 'Suspicious Pattern'

    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MED', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRIT', 'Critical'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        UNDER_REVIEW = 'REVIEW', 'Under Review'
        RESOLVED = 'RESOLVED', 'Resolved'
        FALSE_POSITIVE = 'FALSE', 'False Positive'
        ESCALATED = 'ESC', 'Escalated'

    # Alert identification
    alert_id = models.CharField(max_length=50, unique=True)

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='compliance_alerts'
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='compliance_alerts'
    )

    # Alert details
    alert_type = models.CharField(
        max_length=15,
        choices=AlertType.choices
    )

    severity = models.CharField(
        max_length=5,
        choices=Severity.choices,
        default=Severity.MEDIUM
    )

    description = models.TextField()

    # Related transaction
    ledger_entry = models.ForeignKey(
        DigiLedger,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alerts'
    )

    vendor = models.ForeignKey(
        'vendors.VendorRegistry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts'
    )

    # Risk scoring
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )

    # Status tracking
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN
    )

    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts'
    )

    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Escalation
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'compliance_alerts'
        ordering = ['-created_at']
        verbose_name = 'Compliance Alert'
        verbose_name_plural = 'Compliance Alerts'
        indexes = [
            models.Index(fields=['loan_account', 'status']),
            models.Index(fields=['severity', 'status']),
        ]

    def __str__(self):
        return f"{self.alert_id} - {self.get_alert_type_display()}"

    def assign(self, user):
        """Assign alert to compliance analyst"""
        self.assigned_to = user
        self.status = self.Status.UNDER_REVIEW
        self.save()

    def resolve(self, user, notes):
        """Mark alert as resolved"""
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.status = self.Status.RESOLVED
        self.save()

    def escalate(self):
        """Escalate alert"""
        self.escalated = True
        self.escalated_at = timezone.now()
        self.status = self.Status.ESCALATED
        self.severity = self.Severity.CRITICAL
        self.save()


class CovenantCompliance(models.Model):
    """
    COVENANT MONITORING
    Tracks compliance with loan covenants
    """

    class CovenantType(models.TextChoices):
        END_USE = 'END_USE', 'End-Use Compliance'
        VENDOR_RESTRICTION = 'VENDOR', 'Approved Vendor Usage'
        SPEND_LIMIT = 'SPEND', 'Spending Limits'
        INVOICE_MANDATORY = 'INVOICE', 'Invoice Requirement'
        GOVERNANCE_MAINTENANCE = 'GOV', 'Governance Score Maintenance'
        ENERGY_TARGET = 'ENERGY', 'Energy Savings Target'

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='covenant_compliance'
    )

    covenant_type = models.CharField(
        max_length=15,
        choices=CovenantType.choices
    )

    covenant_description = models.TextField()

    # Compliance status
    compliant = models.BooleanField(default=True)
    compliance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )

    # Breach tracking
    breach_count = models.IntegerField(default=0)
    last_breach_date = models.DateTimeField(blank=True, null=True)
    breach_notes = models.TextField(blank=True)

    # Monitoring
    last_checked = models.DateTimeField(auto_now=True)
    next_check_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'covenant_compliance'
        ordering = ['-last_checked']
        verbose_name = 'Covenant Compliance'
        verbose_name_plural = 'Covenant Compliance'

    def __str__(self):
        return f"{self.loan_account.account_number} - {self.get_covenant_type_display()}"

    def check_compliance(self):
        """
        Check covenant compliance
        Returns True if compliant, False otherwise
        """
        from django.db.models import Sum, Count, Q

        if self.covenant_type == self.CovenantType.END_USE:
            # Check if funds used for approved purposes
            total_spent = self.loan_account.ledger_entries.filter(
                transaction_type__in=[
                    DigiLedger.TransactionType.CARD_PAYMENT,
                    DigiLedger.TransactionType.UPI_PAYMENT
                ]
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            green_spent = self.loan_account.ledger_entries.filter(
                transaction_type__in=[
                    DigiLedger.TransactionType.CARD_PAYMENT,
                    DigiLedger.TransactionType.UPI_PAYMENT
                ],
                green_compliant=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            if total_spent > 0:
                compliance_pct = (green_spent / total_spent) * 100
                self.compliance_percentage = compliance_pct

                # Threshold: 90% must be green-compliant
                self.compliant = compliance_pct >= 90

        elif self.covenant_type == self.CovenantType.VENDOR_RESTRICTION:
            # Check approved vendor usage
            total_transactions = self.loan_account.ledger_entries.filter(
                vendor__isnull=False
            ).count()

            approved_transactions = self.loan_account.ledger_entries.filter(
                vendor__approved=True,
                vendor__active=True
            ).count()

            if total_transactions > 0:
                compliance_pct = (approved_transactions / total_transactions) * 100
                self.compliance_percentage = compliance_pct

                # Threshold: 95% must be with approved vendors
                self.compliant = compliance_pct >= 95

        elif self.covenant_type == self.CovenantType.INVOICE_MANDATORY:
            # Check invoice attachment
            transactions_requiring_invoice = self.loan_account.ledger_entries.filter(
                transaction_type__in=[
                    DigiLedger.TransactionType.CARD_PAYMENT,
                    DigiLedger.TransactionType.UPI_PAYMENT,
                    DigiLedger.TransactionType.NEFT_RTGS
                ]
            ).count()

            transactions_with_invoice = self.loan_account.ledger_entries.filter(
                transaction_type__in=[
                    DigiLedger.TransactionType.CARD_PAYMENT,
                    DigiLedger.TransactionType.UPI_PAYMENT,
                    DigiLedger.TransactionType.NEFT_RTGS
                ]
            ).exclude(Q(invoice_number='') | Q(invoice_file='')).count()

            if transactions_requiring_invoice > 0:
                compliance_pct = (transactions_with_invoice / transactions_requiring_invoice) * 100
                self.compliance_percentage = compliance_pct

                # Threshold: 100% must have invoices
                self.compliant = compliance_pct == 100

        elif self.covenant_type == self.CovenantType.GOVERNANCE_MAINTENANCE:
            # Check if governance score maintained
            try:
                current_score = self.loan_account.loan_application.borrower.governance_profile.governance_score
                original_score = self.loan_account.loan_application.governance_score_at_application

                # Score should not drop by more than 50 points
                score_drop = original_score - current_score
                self.compliant = score_drop <= 50

                if original_score > 0:
                    self.compliance_percentage = (current_score / original_score) * 100
            except:
                self.compliant = False

        # Record breach if non-compliant
        if not self.compliant:
            self.breach_count += 1
            self.last_breach_date = timezone.now()

            # Create compliance alert
            ComplianceAlert.objects.create(
                alert_id=f"COVENANT-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                loan_account=self.loan_account,
                borrower=self.loan_account.loan_application.borrower,
                alert_type=ComplianceAlert.AlertType.COVENANT_BREACH,
                severity=ComplianceAlert.Severity.HIGH,
                description=f"Covenant breach: {self.get_covenant_type_display()} - Compliance: {self.compliance_percentage}%",
                risk_score=Decimal('85.00')
            )

        self.save()
        return self.compliant


class FraudDetectionRule(models.Model):
    """
    ML-READY FRAUD DETECTION RULES
    Deterministic rules + ML risk prediction
    """

    rule_code = models.CharField(max_length=50, unique=True)
    rule_name = models.CharField(max_length=255)
    description = models.TextField()

    # Rule logic (stored as JSON)
    rule_conditions = models.JSONField(
        help_text="JSON defining rule conditions"
    )

    # Scoring
    risk_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Weight added to fraud score if triggered"
    )

    # Alert generation
    auto_flag = models.BooleanField(
        default=True,
        help_text="Automatically flag transactions that match this rule"
    )

    alert_type = models.CharField(
        max_length=15,
        choices=ComplianceAlert.AlertType.choices
    )

    # Status
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fraud_detection_rules'
        verbose_name = 'Fraud Detection Rule'
        verbose_name_plural = 'Fraud Detection Rules'

    def __str__(self):
        return f"{self.rule_code} - {self.rule_name}"


class DiersionRiskScore(models.Model):
    """
    ML DIVERSION RISK PREDICTION
    Placeholder for ML model integration
    """
    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.CASCADE,
        related_name='diversion_scores'
    )

    # Risk score
    diversion_risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="ML-predicted diversion risk (0=Low, 100=High)"
    )

    # Contributing factors
    governance_factor = models.DecimalField(max_digits=5, decimal_places=2)
    vendor_compliance_factor = models.DecimalField(max_digits=5, decimal_places=2)
    invoice_compliance_factor = models.DecimalField(max_digits=5, decimal_places=2)
    spending_pattern_factor = models.DecimalField(max_digits=5, decimal_places=2)

    # Model metadata
    model_version = models.CharField(max_length=50)
    prediction_date = models.DateTimeField(auto_now_add=True)

    # Confidence
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )

    class Meta:
        db_table = 'diversion_risk_scores'
        ordering = ['-prediction_date']
        verbose_name = 'Diversion Risk Score'
        verbose_name_plural = 'Diversion Risk Scores'

    def __str__(self):
        return f"{self.loan_account.account_number} - Risk: {self.diversion_risk_score}"
