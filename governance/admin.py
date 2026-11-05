from django.contrib import admin
from .models import GovernanceProfile, ESGEvidence, GovernanceScoreHistory


@admin.register(GovernanceProfile)
class GovernanceProfileAdmin(admin.ModelAdmin):
    """Governance profile admin"""

    list_display = [
        'user',
        'governance_score',
        'board_independence_ratio',
        'gender_diversity_ratio',
        'verified_at'
    ]
    list_filter = ['verified_at', 'last_updated']
    search_fields = ['user__company_name', 'user__username']
    readonly_fields = [
        'governance_score',
        'last_updated',
        'board_independence_ratio',
        'gender_diversity_ratio',
        'unionization_ratio',
        'grievance_resolution_rate',
        'supplier_screening_rate'
    ]

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Board Structure', {
            'fields': ('board_size', 'independent_directors', 'women_on_board')
        }),
        ('Gender & Diversity', {
            'fields': ('total_employees', 'women_employees', 'equal_pay_policy')
        }),
        ('Labor Relations', {
            'fields': (
                'unionized_workers', 'has_grievance_mechanism',
                'grievances_received', 'grievances_resolved'
            )
        }),
        ('Ethics & Compliance', {
            'fields': (
                'anti_corruption_policy', 'whistleblower_mechanism',
                'compliance_violations'
            )
        }),
        ('Supplier ESG', {
            'fields': ('total_suppliers', 'esg_screened_suppliers')
        }),
        ('Score & Verification', {
            'fields': (
                'governance_score', 'verified_at', 'verified_by', 'last_updated'
            )
        }),
    )

    actions = ['calculate_scores']

    def calculate_scores(self, request, queryset):
        """Bulk calculate governance scores"""
        for profile in queryset:
            profile.calculate_governance_score()
        self.message_user(request, f"{queryset.count()} scores calculated")

    calculate_scores.short_description = "Calculate governance scores"


@admin.register(ESGEvidence)
class ESGEvidenceAdmin(admin.ModelAdmin):
    """ESG evidence admin"""

    list_display = [
        'title', 'document_type', 'governance_profile',
        'verified', 'uploaded_at'
    ]
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['title', 'governance_profile__user__company_name']
    readonly_fields = ['uploaded_at', 'file_size']


@admin.register(GovernanceScoreHistory)
class GovernanceScoreHistoryAdmin(admin.ModelAdmin):
    """Score history admin"""

    list_display = ['governance_profile', 'score', 'created_at']
    list_filter = ['created_at']
    search_fields = ['governance_profile__user__company_name']
    readonly_fields = ['created_at']
