from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Custom User Model with role-based access control
    Addresses: Authentication & Authorization for end-use monitoring
    """

    class UserRole(models.TextChoices):
        SME_USER = 'SME', 'SME User'
        LOAN_OFFICER = 'LO', 'Loan Officer'
        GOVERNANCE_ANALYST = 'GA', 'Governance Analyst'
        HELPLINE_OPERATOR = 'HO', 'Helpline Operator'
        ADMIN = 'AD', 'Admin'

    role = models.CharField(
        max_length=3,
        choices=UserRole.choices,
        default=UserRole.SME_USER
    )

    # SME-specific fields
    company_name = models.CharField(max_length=255, blank=True)
    gstin = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                message='Invalid GSTIN format'
            )
        ]
    )

    # Contact
    phone = models.CharField(max_length=15, blank=True)

    # Compliance flags
    kyc_verified = models.BooleanField(default=False)
    governance_consent = models.BooleanField(
        default=False,
        help_text="Consent to governance monitoring and automated rate adjustments"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_sme(self):
        return self.role == self.UserRole.SME_USER

    @property
    def is_loan_officer(self):
        return self.role == self.UserRole.LOAN_OFFICER

    @property
    def is_governance_analyst(self):
        return self.role == self.UserRole.GOVERNANCE_ANALYST

    @property
    def can_approve_loans(self):
        return self.role in [self.UserRole.LOAN_OFFICER, self.UserRole.ADMIN]

    @property
    def can_monitor_compliance(self):
        return self.role in [
            self.UserRole.GOVERNANCE_ANALYST,
            self.UserRole.LOAN_OFFICER,
            self.UserRole.ADMIN
        ]


class UserActivity(models.Model):
    """
    Audit trail for user actions - critical for compliance
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_activities'
        ordering = ['-timestamp']
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
