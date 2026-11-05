from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from users.models import User
from governance.models import GovernanceProfile


class LoanApplication(models.Model):
    """
    GREEN LOAN APPLICATION WITH GOVERNANCE-LINKED PRICING
    SOLVES: Commitment Deficit - Automatic rate adjustment based on governance score
    """

    class LoanStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        GOVERNANCE_REVIEW = 'GOV_REVIEW', 'Governance Review'
        APPROVED = 'APPROVED', 'Approved'
        SANCTIONED = 'SANCTIONED', 'Sanctioned'
        DISBURSED = 'DISBURSED', 'Disbursed'
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED = 'CLOSED', 'Closed'
        REJECTED = 'REJECTED', 'Rejected'

    class LoanPurpose(models.TextChoices):
        RENEWABLE_ENERGY = 'RENEW', 'Renewable Energy Installation'
        ENERGY_EFFICIENCY = 'ENERGY', 'Energy Efficiency Upgrades'
        GREEN_MATERIALS = 'MATERIALS', 'Green Raw Materials'
        WASTE_MANAGEMENT = 'WASTE', 'Waste Management Systems'
        WATER_CONSERVATION = 'WATER', 'Water Conservation'
        GREEN_TRANSPORT = 'TRANSPORT', 'Green Transportation'
        ESG_CERTIFICATION = 'CERT', 'ESG Certification'
        OTHER_GREEN = 'OTHER', 'Other Green Purpose'

    # Application Details
    application_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated loan application number"
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='loan_applications'
    )

    # Loan Details
    purpose = models.CharField(
        max_length=20,
        choices=LoanPurpose.choices
    )
    purpose_details = models.TextField(
        help_text="Detailed description of green initiative"
    )

    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100000'))]
    )

    tenure_months = models.IntegerField(
        validators=[MinValueValidator(6), MaxValueValidator(60)]
    )

    # END-USE SPECIFICATION (Critical for compliance)
    # NOTE: ManyToManyField to VendorRegistry moved to separate method to avoid circular import

    expected_energy_savings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Expected energy savings in kWh/year"
    )

    expected_carbon_reduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Expected CO2 reduction in tonnes/year"
    )

    # === GOVERNANCE-LINKED PRICING (COMMITMENT MECHANISM) ===
    base_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        help_text="Base interest rate before governance adjustment"
    )

    governance_discount = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount based on governance score (in %)"
    )

    final_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        help_text="Final rate after governance discount"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=LoanStatus.choices,
        default=LoanStatus.DRAFT
    )

    # Review & Approval
    loan_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_loans'
    )

    governance_analyst = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_loans'
    )

    governance_score_at_application = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Approval
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    approval_date = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField(blank=True)

    # Disbursement
    disbursement_date = models.DateTimeField(blank=True, null=True)
    disbursed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    # Fast Track Flag
    fast_track_eligible = models.BooleanField(
        default=False,
        help_text="Prime fast-track for high governance scores"
    )

    class Meta:
        db_table = 'loan_applications'
        ordering = ['-created_at']
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'

    def __str__(self):
        return f"{self.application_number} - {self.borrower.company_name}"

    def save(self, *args, **kwargs):
        if not self.application_number:
            import random
            self.application_number = f"GL{timezone.now().year}{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)

    def calculate_governance_discount(self):
        """
        CORE COMMITMENT ENGINE
        Automatically calculates interest rate discount based on governance score
        """
        try:
            gov_profile = self.borrower.governance_profile
            gov_score = gov_profile.governance_score
            self.governance_score_at_application = gov_score

            # Discount tiers
            if gov_score >= 800:
                self.governance_discount = Decimal('3.00')
                self.fast_track_eligible = True
            elif gov_score >= 700:
                self.governance_discount = Decimal('2.50')
                self.fast_track_eligible = True
            elif gov_score >= 600:
                self.governance_discount = Decimal('2.00')
            elif gov_score >= 500:
                self.governance_discount = Decimal('1.50')
            elif gov_score >= 400:
                self.governance_discount = Decimal('1.00')
            else:
                self.governance_discount = Decimal('0.00')

            # Calculate final rate
            self.final_interest_rate = self.base_interest_rate - self.governance_discount

            self.save()

        except GovernanceProfile.DoesNotExist:
            self.governance_discount = Decimal('0.00')
            self.final_interest_rate = self.base_interest_rate
            self.fast_track_eligible = False
            self.save()

    def check_fast_track_eligibility(self):
        """PRIME FAST TRACK ELIGIBILITY"""
        try:
            gov_score = self.borrower.governance_profile.governance_score

            governance_threshold = 700
            energy_threshold = 10000

            if (gov_score >= governance_threshold and
                    self.expected_energy_savings and
                    self.expected_energy_savings >= energy_threshold):
                self.fast_track_eligible = True
                self.save()
                return True

        except GovernanceProfile.DoesNotExist:
            pass

        return False

    def submit_application(self):
        """Submit application for review"""
        self.status = self.LoanStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.calculate_governance_discount()
        self.check_fast_track_eligibility()
        self.save()

    def move_to_governance_review(self):
        """Move to governance analyst review"""
        self.status = self.LoanStatus.GOVERNANCE_REVIEW
        self.save()

    def approve(self, approved_amount, loan_officer):
        """Approve loan application"""
        self.status = self.LoanStatus.APPROVED
        self.approved_amount = approved_amount
        self.approval_date = timezone.now()
        self.loan_officer = loan_officer
        self.save()

    def sanction(self):
        """Sanction the loan"""
        self.status = self.LoanStatus.SANCTIONED
        self.save()

    def disburse(self, amount):
        """Disburse the loan"""
        self.status = self.LoanStatus.DISBURSED
        self.disbursed_amount = amount
        self.disbursement_date = timezone.now()
        self.save()

        # Create loan account
        LoanAccount.objects.create(
            loan_application=self,
            principal_amount=amount,
            interest_rate=self.final_interest_rate,
            tenure_months=self.tenure_months
        )

    def reject(self, reason):
        """Reject loan application"""
        self.status = self.LoanStatus.REJECTED
        self.approval_notes = reason
        self.save()


# ManyToManyField for approved vendors - add AFTER VendorRegistry is defined
class LoanApplicationVendor(models.Model):
    """Bridge table for loan applications and approved vendors"""
    loan_application = models.ForeignKey('LoanApplication', on_delete=models.CASCADE)
    vendor = models.ForeignKey('vendors.VendorRegistry', on_delete=models.CASCADE)

    class Meta:
        db_table = 'loan_application_vendors'
        unique_together = ('loan_application', 'vendor')


class LoanAccount(models.Model):
    """
    Active loan account with covenant tracking
    """
    loan_application = models.OneToOneField(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='loan_account'
    )

    account_number = models.CharField(max_length=50, unique=True)

    # Loan terms
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()

    # Balances
    outstanding_principal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    outstanding_interest = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Payment tracking
    emi_amount = models.DecimalField(max_digits=10, decimal_places=2)
    next_payment_date = models.DateField()

    # Status
    active = models.BooleanField(default=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    # Covenant compliance (end-use monitoring)
    covenant_compliant = models.BooleanField(
        default=True,
        help_text="Is borrower using funds as agreed?"
    )
    last_compliance_check = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_accounts'
        verbose_name = 'Loan Account'
        verbose_name_plural = 'Loan Accounts'

    def __str__(self):
        return f"{self.account_number} - {self.loan_application.borrower.company_name}"

    def save(self, *args, **kwargs):
        if not self.account_number:
            import random
            self.account_number = f"GL{timezone.now().year}{random.randint(100000, 999999)}"

        if not self.outstanding_principal:
            self.outstanding_principal = self.principal_amount

        if not self.emi_amount:
            # Simple EMI calculation
            r = self.interest_rate / Decimal('1200')
            n = self.tenure_months
            if r > 0:
                self.emi_amount = (
                        self.principal_amount * r *
                        ((1 + r) ** n) / (((1 + r) ** n) - 1)
                )
            else:
                self.emi_amount = self.principal_amount / n

        if not self.next_payment_date:
            from dateutil.relativedelta import relativedelta
            self.next_payment_date = timezone.now().date() + relativedelta(months=1)

        super().save(*args, **kwargs)


class CovenantAdjustment(models.Model):
    """
    DYNAMIC COVENANT ADJUSTMENT
    Allows rate/term changes based on ongoing governance performance
    """
    loan_account = models.ForeignKey(
        LoanAccount,
        on_delete=models.CASCADE,
        related_name='covenant_adjustments'
    )

    adjustment_date = models.DateTimeField(auto_now_add=True)

    # What changed
    previous_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    new_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    # Why it changed
    governance_score_at_adjustment = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    reason = models.TextField()

    # Who approved
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='covenant_adjustments'
    )

    class Meta:
        db_table = 'covenant_adjustments'
        ordering = ['-adjustment_date']
        verbose_name = 'Covenant Adjustment'
        verbose_name_plural = 'Covenant Adjustments'

    def __str__(self):
        return f"{self.loan_account.account_number} - Rate: {self.previous_interest_rate}% → {self.new_interest_rate}%"