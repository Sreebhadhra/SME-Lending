from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import LoanApplication
from decimal import Decimal
import sys
import os

# ML ENGINE IMPORT
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MLengine import GovCredMLEngine

ml_engine = GovCredMLEngine()


# ================================
# APPLY FOR GREEN LOAN
# ================================
@login_required
def loan_apply(request):

    if request.method == 'POST':

        app = LoanApplication.objects.create(
            borrower=request.user,
            purpose=request.POST.get('purpose'),
            purpose_details=request.POST.get('purpose_details'),
            requested_amount=Decimal(request.POST.get('requested_amount')),
            tenure_months=int(request.POST.get('tenure_months')),
            expected_energy_savings=Decimal(
                request.POST.get('expected_energy_savings', 0) or 0
            )
        )

        try:
            gov_profile = request.user.governance_profile

            borrower_data = {
                'governance_score': float(gov_profile.governance_score),
                'board_independence_ratio': gov_profile.board_independence_ratio,
                'gender_diversity_ratio': gov_profile.gender_diversity_ratio,
                'unionization_ratio': gov_profile.unionization_ratio,
                'grievance_resolution_rate': gov_profile.grievance_resolution_rate,
                'supplier_screening_rate': gov_profile.supplier_screening_rate,
                'compliance_violations': gov_profile.compliance_violations,
                'equal_pay_policy': gov_profile.equal_pay_policy,
                'anti_corruption_policy': gov_profile.anti_corruption_policy,

                'loan_amount': float(app.requested_amount),
                'tenure_months': app.tenure_months,
                'revenue': 10000000,
                'debt_to_equity': 0.5,
                'interest_coverage': 2.5,

                'green_spend_ratio': 0.95,
                'invoice_compliance_rate': 0.98,
                'approved_vendor_ratio': 1.0,
                'avg_transaction_size': 50000,

                'previous_loans': 0,
                'repayment_history_score': 100,
            }

            ml_pricing = ml_engine.optimize_rate(
                borrower_data,
                base_rate=12.0
            )

            app.base_interest_rate = Decimal(str(ml_pricing['base_rate']))
            app.governance_discount = Decimal(str(ml_pricing['governance_discount']))
            app.final_interest_rate = Decimal(str(ml_pricing['final_rate']))
            app.status = "SUBMITTED"
            app.save()

            messages.success(
                request,
                f'Application {app.application_number} submitted! '
                f'Final Rate: {ml_pricing["final_rate"]}%'
            )

        except Exception:
            app.calculate_governance_discount()
            app.status = "SUBMITTED"
            app.save()

        return redirect('loans:detail', pk=app.pk)

    return render(request, 'loans/apply.html')


# ================================
# SME VIEW
# ================================
@login_required
def loan_list(request):
    applications = LoanApplication.objects.filter(borrower=request.user)
    return render(request, 'loans/list.html', {'applications': applications})


@login_required
def loan_detail(request, pk):

    app = get_object_or_404(
        LoanApplication,
        pk=pk,
        borrower=request.user
    )

    ml_analysis = None

    try:
        gov_profile = request.user.governance_profile

        borrower_data = {
            'governance_score': float(gov_profile.governance_score),
            'loan_amount': float(app.requested_amount),
            'tenure_months': app.tenure_months,
        }

        ml_pricing = ml_engine.optimize_rate(borrower_data)

        ml_analysis = {
            'default_risk': ml_pricing['default_risk'],
            'compliance_risk': ml_pricing['compliance_risk'],
            'risk_premium': ml_pricing['risk_premium'],
        }

    except:
        pass

    return render(
        request,
        'loans/detail.html',
        {'application': app, 'ml_analysis': ml_analysis}
    )


# ================================
# SME ACCEPT LOAN OFFER
# ================================
@login_required
def accept_loan(request, pk):

    loan = get_object_or_404(
        LoanApplication,
        pk=pk,
        borrower=request.user
    )

    loan.status = "ACCEPTED"
    loan.save()

    messages.success(request, "Loan Accepted Successfully!")

    return redirect('loans:detail', pk=pk)


# ================================
# ✅ ERROR 2 FIX — SUCCESS VIEW
# ================================
@login_required
def loan_success(request, loan_id):

    application = get_object_or_404(
        LoanApplication,
        id=loan_id,
        borrower=request.user
    )

    return render(
        request,
        'loans/success.html',
        {'application': application}
    )
