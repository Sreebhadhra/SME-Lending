from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User


class VendorRegistry(models.Model):
    """
    CRITICAL FOR END-USE COMPLIANCE
    Only approved vendors can receive loan proceeds
    This prevents fund diversion
    """

    class VendorCategory(models.TextChoices):
        RENEWABLE_ENERGY = 'RENEW', 'Renewable Energy Equipment'
        GREEN_MATERIALS = 'GREEN_MAT', 'Green Raw Materials'
        ENERGY_EFFICIENT = 'ENERGY_EFF', 'Energy Efficient Equipment'
        WASTE_MANAGEMENT = 'WASTE', 'Waste Management'
        WATER_CONSERVATION = 'WATER', 'Water Conservation'
        SUSTAINABLE_PACKAGING = 'PACKAGING', 'Sustainable Packaging'
        GREEN_LOGISTICS = 'LOGISTICS', 'Green Logistics'
        ESG_CONSULTING = 'CONSULTING', 'ESG Consulting'
        CERTIFICATION_BODY = 'CERT', 'Certification Body'
        OTHER_GREEN = 'OTHER', 'Other Green Services'

    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low Risk'
        MEDIUM = 'MED', 'Medium Risk'
        HIGH = 'HIGH', 'High Risk'
        BLACKLISTED = 'BLACK', 'Blacklisted'

    # Basic Info
    vendor_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique vendor identifier"
    )
    vendor_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255)

    # Tax & Registration
    gstin = models.CharField(max_length=15, unique=True)
    pan = models.CharField(max_length=10, blank=True)

    # Classification
    category = models.CharField(
        max_length=20,
        choices=VendorCategory.choices
    )
    subcategory = models.CharField(max_length=100, blank=True)

    # ESG Credentials
    esg_certified = models.BooleanField(
        default=False,
        help_text="Has valid ESG certification"
    )
    certification_body = models.CharField(max_length=255, blank=True)
    certification_number = models.CharField(max_length=100, blank=True)
    certification_valid_until = models.DateField(blank=True, null=True)

    # Green credentials
    iso_14001 = models.BooleanField(default=False, help_text="Environmental Management")
    iso_50001 = models.BooleanField(default=False, help_text="Energy Management")
    leed_certified = models.BooleanField(default=False)
    carbon_neutral = models.BooleanField(default=False)

    # Risk Assessment
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM
    )
    risk_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0=High Risk, 100=Low Risk"
    )

    # Approval Status
    approved = models.BooleanField(
        default=False,
        help_text="Approved for Green Transactions"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_vendors'
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='registered_vendors'
    )

    # Flags
    active = models.BooleanField(default=True)
    blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'vendor_registry'
        ordering = ['vendor_name']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendor Registry'

    def __str__(self):
        return f"{self.vendor_code} - {self.vendor_name}"

    @property
    def is_eligible_for_green_transactions(self):
        """
        CORE END-USE CONTROL
        Determines if vendor can receive green loan proceeds
        """
        return (
                self.approved and
                self.active and
                not self.blacklisted and
                self.risk_level != self.RiskLevel.BLACKLISTED
        )

    @property
    def certification_valid(self):
        from django.utils import timezone
        if not self.certification_valid_until:
            return False
        return self.certification_valid_until > timezone.now().date()

    def calculate_risk_score(self):
        """
        Calculate vendor risk score
        Higher score = Lower risk
        """
        score = 50  # baseline

        # ESG certification
        if self.esg_certified and self.certification_valid:
            score += 20

        # ISO certifications
        if self.iso_14001:
            score += 10
        if self.iso_50001:
            score += 10

        # Other green credentials
        if self.leed_certified:
            score += 5
        if self.carbon_neutral:
            score += 5

        # Penalties
        if self.blacklisted:
            score = 0

        self.risk_score = min(max(score, 0), 100)

        # Set risk level
        if self.blacklisted:
            self.risk_level = self.RiskLevel.BLACKLISTED
        elif self.risk_score >= 80:
            self.risk_level = self.RiskLevel.LOW
        elif self.risk_score >= 50:
            self.risk_level = self.RiskLevel.MEDIUM
        else:
            self.risk_level = self.RiskLevel.HIGH

        self.save()
        return self.risk_score


class VendorTransaction(models.Model):
    """
    Tracks all transactions with vendors
    Critical for end-use monitoring
    """
    vendor = models.ForeignKey(
        VendorRegistry,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_transactions'
    )

    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Invoice linkage (critical for compliance)
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(blank=True, null=True)
    invoice_file = models.FileField(
        upload_to='invoices/%Y/%m/',
        blank=True,
        null=True
    )

    description = models.TextField()

    # Compliance
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_transactions'
    )
    approved_at = models.DateTimeField(blank=True, null=True)

    # Flags
    flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vendor_transactions'
        ordering = ['-created_at']
        verbose_name = 'Vendor Transaction'
        verbose_name_plural = 'Vendor Transactions'

    def __str__(self):
        return f"{self.transaction_id} - {self.vendor.vendor_name} - ₹{self.amount}"


class VendorAudit(models.Model):
    """
    Periodic audits of vendor compliance
    """
    vendor = models.ForeignKey(
        VendorRegistry,
        on_delete=models.CASCADE,
        related_name='audits'
    )

    audit_date = models.DateField()
    auditor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_audits'
    )

    findings = models.TextField()
    compliance_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    action_required = models.BooleanField(default=False)
    action_details = models.TextField(blank=True)

    next_audit_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vendor_audits'
        ordering = ['-audit_date']
        verbose_name = 'Vendor Audit'
        verbose_name_plural = 'Vendor Audits'

    def __str__(self):
        return f"Audit: {self.vendor.vendor_name} on {self.audit_date}"
