from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User


class GovernanceProfile(models.Model):
    """
    Stores BRSR-based governance indicators for SMEs
    CORE COMMITMENT MECHANISM: This data drives automatic rate adjustments
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='governance_profile'
    )

    # === BOARD STRUCTURE ===
    board_size = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    independent_directors = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    women_on_board = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )

    # === GENDER & DIVERSITY ===
    total_employees = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    women_employees = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    equal_pay_policy = models.BooleanField(
        default=False,
        help_text="Equal remuneration policy in place"
    )

    # === LABOR & UNIONIZATION ===
    unionized_workers = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    has_grievance_mechanism = models.BooleanField(default=False)
    grievances_received = models.IntegerField(default=0)
    grievances_resolved = models.IntegerField(default=0)

    # === ETHICS & COMPLIANCE ===
    anti_corruption_policy = models.BooleanField(default=False)
    whistleblower_mechanism = models.BooleanField(default=False)
    compliance_violations = models.IntegerField(
        default=0,
        help_text="Number of regulatory violations in last 12 months"
    )

    # === SUPPLIER ESG ===
    total_suppliers = models.IntegerField(default=0)
    esg_screened_suppliers = models.IntegerField(default=0)

    # === CALCULATED METRICS ===
    governance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(900)],
        help_text="GovCred Score (0-900)"
    )

    last_updated = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_profiles'
    )

    class Meta:
        db_table = 'governance_profiles'
        verbose_name = 'Governance Profile'
        verbose_name_plural = 'Governance Profiles'

    def __str__(self):
        return f"{self.user.company_name} - Score: {self.governance_score}"

    @property
    def board_independence_ratio(self):
        if self.board_size == 0:
            return 0
        return (self.independent_directors / self.board_size) * 100

    @property
    def gender_diversity_ratio(self):
        if self.total_employees == 0:
            return 0
        return (self.women_employees / self.total_employees) * 100

    @property
    def unionization_ratio(self):
        if self.total_employees == 0:
            return 0
        return (self.unionized_workers / self.total_employees) * 100

    @property
    def grievance_resolution_rate(self):
        if self.grievances_received == 0:
            return 100
        return (self.grievances_resolved / self.grievances_received) * 100

    @property
    def supplier_screening_rate(self):
        if self.total_suppliers == 0:
            return 0
        return (self.esg_screened_suppliers / self.total_suppliers) * 100

    def calculate_governance_score(self):
        """
        CORE COMMITMENT ENGINE
        Calculates governance score that triggers automatic rate benefits
        """
        score = 0

        # Board structure (200 points)
        if self.board_independence_ratio >= 33:
            score += 100
        elif self.board_independence_ratio >= 20:
            score += 60

        if self.women_on_board > 0:
            score += 50
        if self.women_on_board >= 2:
            score += 50

        # Gender diversity (150 points)
        if self.gender_diversity_ratio >= 30:
            score += 100
        elif self.gender_diversity_ratio >= 20:
            score += 60
        elif self.gender_diversity_ratio >= 10:
            score += 30

        if self.equal_pay_policy:
            score += 50

        # Labor relations (150 points)
        if self.has_grievance_mechanism:
            score += 50

        if self.grievance_resolution_rate >= 80:
            score += 50
        elif self.grievance_resolution_rate >= 60:
            score += 30

        if self.unionization_ratio > 0:
            score += 50

        # Ethics & compliance (200 points)
        if self.anti_corruption_policy:
            score += 75

        if self.whistleblower_mechanism:
            score += 75

        # Penalty for violations
        if self.compliance_violations == 0:
            score += 50
        else:
            score -= (self.compliance_violations * 20)

        # Supplier screening (100 points)
        if self.supplier_screening_rate >= 80:
            score += 100
        elif self.supplier_screening_rate >= 50:
            score += 60
        elif self.supplier_screening_rate >= 25:
            score += 30

        # Risk adjustment (100 points) - placeholder
        # In production, integrate World Bank Doing Business scores
        score += 100

        # Cap at 900
        self.governance_score = min(max(score, 0), 900)
        self.save()

        return self.governance_score


class ESGEvidence(models.Model):
    """
    Document repository for governance verification
    COMMITMENT PROOF: Evidence backing the governance score
    """

    class DocumentType(models.TextChoices):
        ELECTRICITY_BILL = 'ELEC', 'Electricity Bill'
        ISO_CERTIFICATE = 'ISO', 'ISO Certificate'
        ESG_POLICY = 'ESG', 'ESG Policy'
        BOARD_RESOLUTION = 'BR', 'Board Resolution'
        AUDIT_REPORT = 'AUDIT', 'Audit Report'
        CONTRACT = 'CONTRACT', 'Contract'
        PHOTO = 'PHOTO', 'Photo Evidence'
        SOCIAL_POLICY = 'SOCIAL', 'Social Policy Document'
        OTHER = 'OTHER', 'Other'

    governance_profile = models.ForeignKey(
        GovernanceProfile,
        on_delete=models.CASCADE,
        related_name='evidence'
    )

    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    file = models.FileField(upload_to='governance/evidence/%Y/%m/')
    file_size = models.IntegerField(blank=True, null=True)  # in bytes

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_evidence'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_evidence'
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'esg_evidence'
        ordering = ['-uploaded_at']
        verbose_name = 'ESG Evidence'
        verbose_name_plural = 'ESG Evidence'

    def __str__(self):
        return f"{self.title} - {self.get_document_type_display()}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class GovernanceScoreHistory(models.Model):
    """
    Tracks governance score changes over time
    COMMITMENT TRACKING: Shows improvement/deterioration trends
    """
    governance_profile = models.ForeignKey(
        GovernanceProfile,
        on_delete=models.CASCADE,
        related_name='score_history'
    )

    score = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(help_text="Why did the score change?")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='score_changes'
    )

    class Meta:
        db_table = 'governance_score_history'
        ordering = ['-created_at']
        verbose_name = 'Governance Score History'
        verbose_name_plural = 'Governance Score History'

    def __str__(self):
        return f"{self.governance_profile.user.company_name} - {self.score} on {self.created_at}"
