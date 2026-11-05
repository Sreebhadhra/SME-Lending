from django.contrib import admin
from .models import (
    ComplianceAlert,
    CovenantCompliance,
    FraudDetectionRule,
    DiersionRiskScore
)


@admin.register(ComplianceAlert)
class ComplianceAlertAdmin(admin.ModelAdmin):
    list_display = (
        "alert_id",
        "loan_account",
        "alert_type",
        "severity",
        "status",
        "risk_score",
        "created_at",
    )

    list_filter = (
        "alert_type",
        "severity",
        "status",
        "created_at",
    )

    search_fields = (
        "alert_id",
        "description",
    )


@admin.register(CovenantCompliance)
class CovenantComplianceAdmin(admin.ModelAdmin):
    list_display = (
        "loan_account",
        "covenant_type",
        "compliant",
        "compliance_percentage",
        "breach_count",
        "last_checked",
    )

    list_filter = (
        "covenant_type",
        "compliant",
    )


@admin.register(FraudDetectionRule)
class FraudDetectionRuleAdmin(admin.ModelAdmin):
    list_display = (
        "rule_code",
        "rule_name",
        "alert_type",
        "risk_weight",
        "active",
    )

    list_filter = (
        "active",
        "alert_type",
    )

    search_fields = (
        "rule_code",
        "rule_name",
    )


@admin.register(DiersionRiskScore)
class DiersionRiskScoreAdmin(admin.ModelAdmin):
    list_display = (
        "loan_account",
        "diversion_risk_score",
        "confidence_score",
        "model_version",
        "prediction_date",
    )

    list_filter = (
        "model_version",
    )


