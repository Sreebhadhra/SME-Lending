from django.contrib import admin
from .models import LoanApplication, LoanAccount, CovenantAdjustment


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    """Loan application admin"""

    list_display = [
        'application_number',
        'borrower',
        'requested_amount',
        'final_interest_rate',
        'governance_discount',
        'status',
        'fast_track_eligible',
        'submitted_at'
    ]
    list_filter = ['status', 'purpose', 'fast_track_eligible']
    search_fields = ['application_number', 'borrower__company_name']
    readonly_fields = [
        'application_number',
        'governance_discount',
        'final_interest_rate',
        'governance_score_at_application',
        'fast_track_eligible',
        'created_at',
        'submitted_at'
    ]

    actions = ['calculate_rates']

    def calculate_rates(self, request, queryset):
        """Bulk calculate governance discounts"""
        for app in queryset:
            app.calculate_governance_discount()
        self.message_user(request, f"{queryset.count()} rates calculated")

    calculate_rates.short_description = "Calculate governance discounts"


@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    """Loan account admin"""

    list_display = [
        'account_number',
        'principal_amount',
        'interest_rate',
        'outstanding_principal',
        'covenant_compliant',
        'active'
    ]
    list_filter = ['active', 'covenant_compliant']
    search_fields = ['account_number']
    readonly_fields = ['account_number', 'created_at', 'updated_at']


@admin.register(CovenantAdjustment)
class CovenantAdjustmentAdmin(admin.ModelAdmin):
    """Covenant adjustment admin"""

    list_display = [
        'loan_account',
        'previous_interest_rate',
        'new_interest_rate',
        'governance_score_at_adjustment',
        'adjustment_date'
    ]
    list_filter = ['adjustment_date']
    readonly_fields = ['adjustment_date']

