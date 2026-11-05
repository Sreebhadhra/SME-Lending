from django.db import models
from django.utils import timezone
from users.models import User


class HelplineTicket(models.Model):
    """
    BORROWER SUPPORT SYSTEM
    Tracks issues, queries, and complaints
    """

    class TicketType(models.TextChoices):
        GENERAL_QUERY = 'GENERAL', 'General Query'
        TRANSACTION_ISSUE = 'TRANS', 'Transaction Issue'
        VENDOR_ISSUE = 'VENDOR', 'Vendor Issue'
        CARD_ISSUE = 'CARD', 'Green Card Issue'
        UPI_ISSUE = 'UPI', 'UPI Issue'
        INVOICE_HELP = 'INVOICE', 'Invoice Help'
        RATE_QUERY = 'RATE', 'Interest Rate Query'
        GOVERNANCE_QUERY = 'GOV', 'Governance Score Query'
        COMPLAINT = 'COMPLAINT', 'Complaint'
        TECHNICAL_ISSUE = 'TECH', 'Technical Issue'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MED', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URG', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROG', 'In Progress'
        PENDING_INFO = 'PENDING', 'Pending Information'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'
        ESCALATED = 'ESC', 'Escalated'

    # Ticket identification
    ticket_number = models.CharField(max_length=50, unique=True)

    # Requester
    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='helpline_tickets'
    )

    loan_account = models.ForeignKey(
        'loans.LoanAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='helpline_tickets'
    )

    # Ticket details
    ticket_type = models.CharField(
        max_length=15,
        choices=TicketType.choices
    )

    subject = models.CharField(max_length=255)
    description = models.TextField()

    priority = models.CharField(
        max_length=5,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

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
        related_name='assigned_tickets'
    )

    # Resolution
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_tickets'
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    # Satisfaction
    satisfaction_rating = models.IntegerField(
        blank=True,
        null=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="1-5 star rating"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SLA tracking
    sla_breach = models.BooleanField(default=False)
    sla_deadline = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'helpline_tickets'
        ordering = ['-created_at']
        verbose_name = 'Helpline Ticket'
        verbose_name_plural = 'Helpline Tickets'

    def __str__(self):
        return f"{self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate ticket number
            import random
            self.ticket_number = f"TKT{timezone.now().year}{random.randint(100000, 999999)}"

        # Set SLA deadline based on priority
        if not self.sla_deadline:
            from datetime import timedelta
            if self.priority == self.Priority.URGENT:
                self.sla_deadline = timezone.now() + timedelta(hours=4)
            elif self.priority == self.Priority.HIGH:
                self.sla_deadline = timezone.now() + timedelta(hours=24)
            elif self.priority == self.Priority.MEDIUM:
                self.sla_deadline = timezone.now() + timedelta(hours=48)
            else:
                self.sla_deadline = timezone.now() + timedelta(hours=72)

        # Check SLA breach
        if self.status not in [self.Status.RESOLVED, self.Status.CLOSED]:
            if timezone.now() > self.sla_deadline:
                self.sla_breach = True

        super().save(*args, **kwargs)

    def assign(self, operator):
        """Assign ticket to helpline operator"""
        self.assigned_to = operator
        self.status = self.Status.IN_PROGRESS
        self.save()

    def resolve(self, operator, resolution):
        """Resolve ticket"""
        self.resolved_by = operator
        self.resolved_at = timezone.now()
        self.resolution = resolution
        self.status = self.Status.RESOLVED
        self.save()

    def close(self):
        """Close ticket"""
        self.status = self.Status.CLOSED
        self.save()

    def escalate(self):
        """Escalate ticket"""
        self.status = self.Status.ESCALATED
        self.priority = self.Priority.URGENT
        self.save()


class TicketComment(models.Model):
    """
    Comments/updates on helpline tickets
    """
    ticket = models.ForeignKey(
        HelplineTicket,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    commenter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_comments'
    )

    comment = models.TextField()

    internal = models.BooleanField(
        default=False,
        help_text="Internal note (not visible to borrower)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_comments'
        ordering = ['created_at']
        verbose_name = 'Ticket Comment'
        verbose_name_plural = 'Ticket Comments'

    def __str__(self):
        return f"Comment on {self.ticket.ticket_number} by {self.commenter.username}"


class FAQ(models.Model):
    """
    Frequently Asked Questions
    """

    class Category(models.TextChoices):
        GENERAL = 'GEN', 'General'
        LOAN_APPLICATION = 'LOAN', 'Loan Application'
        GOVERNANCE = 'GOV', 'Governance Score'
        TRANSACTIONS = 'TRANS', 'Transactions'
        GREEN_CARD = 'CARD', 'Green Card'
        VENDORS = 'VENDOR', 'Vendors'
        COMPLIANCE = 'COMP', 'Compliance'

    category = models.CharField(
        max_length=10,
        choices=Category.choices
    )

    question = models.TextField()
    answer = models.TextField()

    order = models.IntegerField(default=0)

    active = models.BooleanField(default=True)

    view_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faqs'
        ordering = ['category', 'order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return f"{self.get_category_display()}: {self.question[:50]}"


class BorrowerFeedback(models.Model):
    """
    Borrower feedback on the platform
    """

    class FeedbackType(models.TextChoices):
        GENERAL = 'GEN', 'General Feedback'
        FEATURE_REQUEST = 'FEAT', 'Feature Request'
        BUG_REPORT = 'BUG', 'Bug Report'
        IMPROVEMENT = 'IMP', 'Improvement Suggestion'

    borrower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feedback'
    )

    feedback_type = models.CharField(
        max_length=5,
        choices=FeedbackType.choices
    )

    subject = models.CharField(max_length=255)
    details = models.TextField()

    # Rating
    overall_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="Overall platform rating (1-5)"
    )

    # Specific ratings
    ease_of_use = models.IntegerField(
        blank=True,
        null=True,
        choices=[(i, i) for i in range(1, 6)]
    )

    transparency = models.IntegerField(
        blank=True,
        null=True,
        choices=[(i, i) for i in range(1, 6)]
    )

    support_quality = models.IntegerField(
        blank=True,
        null=True,
        choices=[(i, i) for i in range(1, 6)]
    )

    # Response
    responded = models.BooleanField(default=False)
    response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_responses'
    )
    responded_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'borrower_feedback'
        ordering = ['-created_at']
        verbose_name = 'Borrower Feedback'
        verbose_name_plural = 'Borrower Feedback'

    def __str__(self):
        return f"Feedback from {self.borrower.username} - {self.overall_rating} stars"
