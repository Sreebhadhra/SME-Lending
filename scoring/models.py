from django.db import models
from decimal import Decimal
from users.models import User
from governance.models import GovernanceProfile


class ScoringModel(models.Model):
    """
    GOVERNANCE SCORING MODEL CONFIGURATION
    Defines how governance scores are calculated
    """

    model_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    description = models.TextField()

    # Scoring weights (totals to 100)
    board_structure_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00')
    )
    gender_diversity_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00')
    )
    labor_relations_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00')
    )
    ethics_compliance_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('25.00')
    )
    supplier_screening_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00')
    )
    world_bank_risk_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00')
    )

    # Thresholds for rating
    aaa_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('800.00')
    )
    aa_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('700.00')
    )
    a_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('600.00')
    )
    bbb_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('500.00')
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scoring_models'
        verbose_name = 'Scoring Model'
        verbose_name_plural = 'Scoring Models'

    def __str__(self):
        return f"{self.model_name} v{self.version}"


class GovernanceRating(models.Model):
    """
    GOVERNANCE CREDIT RATING
    Based on GovCred Score
    """

    class Rating(models.TextChoices):
        AAA = 'AAA', 'AAA - Excellent'
        AA = 'AA', 'AA - Very Good'
        A = 'A', 'A - Good'
        BBB = 'BBB', 'BBB - Adequate'
        BB = 'BB', 'BB - Below Average'
        B = 'B', 'B - Poor'
        C = 'C', 'C - Very Poor'
        D = 'D', 'D - Default Risk'

    governance_profile = models.ForeignKey(
        GovernanceProfile,
        on_delete=models.CASCADE,
        related_name='ratings'
    )

    rating = models.CharField(
        max_length=3,
        choices=Rating.choices
    )

    score = models.DecimalField(max_digits=5, decimal_places=2)

    # Rating rationale
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    # Analyst
    rated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='governance_ratings'
    )

    rating_date = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField()

    # Outlook
    outlook = models.CharField(
        max_length=20,
        choices=[
            ('POSITIVE', 'Positive'),
            ('STABLE', 'Stable'),
            ('NEGATIVE', 'Negative'),
            ('DEVELOPING', 'Developing')
        ],
        default='STABLE'
    )

    class Meta:
        db_table = 'governance_ratings'
        ordering = ['-rating_date']
        verbose_name = 'Governance Rating'
        verbose_name_plural = 'Governance Ratings'

    def __str__(self):
        return f"{self.governance_profile.user.company_name} - {self.rating}"

    @staticmethod
    def calculate_rating(score):
        """
        Convert score to rating
        """
        if score >= 800:
            return GovernanceRating.Rating.AAA
        elif score >= 700:
            return GovernanceRating.Rating.AA
        elif score >= 600:
            return GovernanceRating.Rating.A
        elif score >= 500:
            return GovernanceRating.Rating.BBB
        elif score >= 400:
            return GovernanceRating.Rating.BB
        elif score >= 300:
            return GovernanceRating.Rating.B
        elif score >= 200:
            return GovernanceRating.Rating.C
        else:
            return GovernanceRating.Rating.D


class InterestRateMatrix(models.Model):
    """
    INTEREST RATE DETERMINATION
    Maps governance score ranges to interest rate discounts
    THIS IS THE COMMITMENT MECHANISM
    """

    # Score range
    min_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Minimum governance score for this tier"
    )
    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Maximum governance score for this tier"
    )

    # Rate benefits
    base_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        help_text="Base interest rate (%)"
    )

    governance_discount = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="Governance discount (%)"
    )

    final_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Final interest rate after discount (%)"
    )

    # Benefits
    fast_track_processing = models.BooleanField(
        default=False,
        help_text="Eligible for fast-track approval"
    )

    lower_documentation = models.BooleanField(
        default=False,
        help_text="Reduced documentation requirements"
    )

    higher_loan_amount = models.BooleanField(
        default=False,
        help_text="Eligible for higher loan amounts"
    )

    # Metadata
    effective_from = models.DateField()
    effective_until = models.DateField(blank=True, null=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'interest_rate_matrix'
        ordering = ['-min_score']
        verbose_name = 'Interest Rate Matrix'
        verbose_name_plural = 'Interest Rate Matrix'

    def __str__(self):
        return f"Score {self.min_score}-{self.max_score}: {self.final_rate}% ({self.governance_discount}% discount)"

    @staticmethod
    def get_rate_for_score(score):
        """
        AUTOMATIC RATE DETERMINATION
        Returns interest rate based on governance score
        """
        from django.utils import timezone

        try:
            rate_tier = InterestRateMatrix.objects.filter(
                min_score__lte=score,
                max_score__gte=score,
                active=True,
                effective_from__lte=timezone.now().date()
            ).filter(
                models.Q(effective_until__isnull=True) |
                models.Q(effective_until__gte=timezone.now().date())
            ).first()

            if rate_tier:
                return {
                    'base_rate': rate_tier.base_rate,
                    'discount': rate_tier.governance_discount,
                    'final_rate': rate_tier.final_rate,
                    'fast_track': rate_tier.fast_track_processing,
                }
            else:
                # Default rates
                return {
                    'base_rate': Decimal('12.00'),
                    'discount': Decimal('0.00'),
                    'final_rate': Decimal('12.00'),
                    'fast_track': False,
                }
        except:
            return {
                'base_rate': Decimal('12.00'),
                'discount': Decimal('0.00'),
                'final_rate': Decimal('12.00'),
                'fast_track': False,
            }


class PrimeEligibilityCriteria(models.Model):
    """
    PRIME FAST-TRACK ELIGIBILITY
    Defines criteria for prime/fast-track processing
    """

    criteria_name = models.CharField(max_length=255)
    description = models.TextField()

    # Governance thresholds
    min_governance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('700.00')
    )

    # ESG thresholds
    min_energy_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum energy efficiency score"
    )

    min_carbon_reduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum carbon reduction commitment (tonnes/year)"
    )

    # Compliance history
    max_compliance_violations = models.IntegerField(
        default=0,
        help_text="Maximum allowed violations in last 12 months"
    )

    # Benefits
    approval_sla_days = models.IntegerField(
        default=3,
        help_text="Fast-track approval SLA in days"
    )

    rate_discount_bonus = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.50'),
        help_text="Additional rate discount for prime customers (%)"
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prime_eligibility_criteria'
        verbose_name = 'Prime Eligibility Criteria'
        verbose_name_plural = 'Prime Eligibility Criteria'

    def __str__(self):
        return self.criteria_name

    def check_eligibility(self, governance_profile, loan_application):
        """
        Check if borrower is eligible for prime/fast-track
        """
        # Check governance score
        if governance_profile.governance_score < self.min_governance_score:
            return False, "Governance score below threshold"

        # Check compliance violations
        if governance_profile.compliance_violations > self.max_compliance_violations:
            return False, "Too many compliance violations"

        # Check energy commitments
        if loan_application.expected_energy_savings:
            if loan_application.expected_energy_savings < self.min_carbon_reduction:
                return False, "Energy savings commitment below threshold"

        return True, "Eligible for Prime Fast-Track"


class ESGScorecard(models.Model):
    """
    ESG SCORECARD
    Separate from governance, tracks environmental performance
    """

    governance_profile = models.OneToOneField(
        GovernanceProfile,
        on_delete=models.CASCADE,
        related_name='esg_scorecard'
    )

    # Environmental
    energy_efficiency_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    carbon_footprint_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    waste_management_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Social (overlaps with governance)
    labor_practices_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    community_impact_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Governance (from GovernanceProfile)
    governance_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Overall ESG
    overall_esg_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'esg_scorecards'
        verbose_name = 'ESG Scorecard'
        verbose_name_plural = 'ESG Scorecards'

    def __str__(self):
        return f"{self.governance_profile.user.company_name} - ESG: {self.overall_esg_score}"

    def calculate_overall_score(self):
        """
        Calculate weighted ESG score
        E: 40%, S: 30%, G: 30%
        """
        e_score = (
                self.energy_efficiency_score * Decimal('0.15') +
                self.carbon_footprint_score * Decimal('0.15') +
                self.waste_management_score * Decimal('0.10')
        )

        s_score = (
                self.labor_practices_score * Decimal('0.15') +
                self.community_impact_score * Decimal('0.15')
        )

        g_score = self.governance_score * Decimal('0.30')

        self.overall_esg_score = e_score + s_score + g_score
        self.save()

        return self.overall_esg_score
