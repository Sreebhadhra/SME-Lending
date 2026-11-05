from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GovernanceProfile
import sys
import os

# Add project root to path to import ml_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ML engine
try:
    from ml_engine import GovCredMLEngine

    ml_engine = GovCredMLEngine()
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print(" ML Engine not available - using standard calculations")


@login_required
def dashboard(request):
    """Main dashboard with ML risk analysis"""
    try:
        profile = request.user.governance_profile
        has_profile = True

        # Prepare context with profile data
        context = {
            'profile': profile,
            'has_profile': True,
            'score_percent': round((profile.governance_score / 900) * 100) if profile.governance_score else 0
        }

        # ===== ADD ML RISK ANALYSIS =====
        if ML_AVAILABLE:
            try:
                # Prepare borrower data for ML
                borrower_data = {
                    'governance_score': float(profile.governance_score or 0),
                    'board_independence_ratio': profile.board_independence_ratio,
                    'gender_diversity_ratio': profile.gender_diversity_ratio,
                    'unionization_ratio': profile.unionization_ratio,
                    'grievance_resolution_rate': profile.grievance_resolution_rate,
                    'supplier_screening_rate': profile.supplier_screening_rate,
                    'compliance_violations': profile.compliance_violations,
                    'equal_pay_policy': profile.equal_pay_policy,
                    'anti_corruption_policy': profile.anti_corruption_policy,

                    # Example loan parameters
                    'loan_amount': 5000000,
                    'tenure_months': 36,
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

                # Get ML predictions
                default_risk = ml_engine.predict_default_risk(borrower_data)
                compliance_risk = ml_engine.predict_compliance_risk(borrower_data)
                ml_pricing = ml_engine.optimize_rate(borrower_data, base_rate=12.0)

                # Add ML insights to context
                context.update({
                    'ml_default_risk': round(default_risk * 100, 1),
                    'ml_compliance_risk': round(compliance_risk * 100, 1),
                    'ml_recommended_rate': ml_pricing['final_rate'],
                    'ml_risk_premium': ml_pricing['risk_premium'],
                    'ml_available': True,
                })

            except Exception as e:
                print(f"ML Analysis Error: {e}")
                context['ml_available'] = False
        else:
            context['ml_available'] = False

        # ===== ESG HEATMAP + LOAN TRACKER DUMMY DATA =====
        context.update({
            'esg_score': 85,
            'governance_risk': 12,
            'diversion_risk': 8,
            'ml_risk_score': 15,
            'loan_status': "Under Review",
            'lifecycle_progress': 40,
        })

    except GovernanceProfile.DoesNotExist:
        context = {
            'has_profile': False,
            'ml_available': False,
            'profile': None,
            'score_percent': 0,
        }

    return render(request, 'dashboard.html', context)


@login_required
def governance_profile(request):
    """Governance profile management"""
    try:
        profile = request.user.governance_profile
    except GovernanceProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        if not profile:
            profile = GovernanceProfile.objects.create(user=request.user)

        # Update fields
        profile.board_size = int(request.POST.get('board_size', 0))
        profile.independent_directors = int(request.POST.get('independent_directors', 0))
        profile.women_on_board = int(request.POST.get('women_on_board', 0))
        profile.total_employees = int(request.POST.get('total_employees', 0))
        profile.women_employees = int(request.POST.get('women_employees', 0))
        profile.equal_pay_policy = request.POST.get('equal_pay_policy') == 'on'

        profile.unionized_workers = int(request.POST.get('unionized_workers', 0))
        profile.has_grievance_mechanism = request.POST.get('has_grievance_mechanism') == 'on'
        profile.grievances_received = int(request.POST.get('grievances_received', 0))
        profile.grievances_resolved = int(request.POST.get('grievances_resolved', 0))
        profile.anti_corruption_policy = request.POST.get('anti_corruption_policy') == 'on'
        profile.whistleblower_mechanism = request.POST.get('whistleblower_mechanism') == 'on'
        profile.compliance_violations = int(request.POST.get('compliance_violations', 0))
        profile.total_suppliers = int(request.POST.get('total_suppliers', 0))
        profile.esg_screened_suppliers = int(request.POST.get('esg_screened_suppliers', 0))

        profile.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('governance:dashboard')

    return render(request, 'governance/profile.html', {'profile': profile})


@login_required
def calculate_score(request):
    """Calculate governance score and show ML insights"""
    try:
        profile = request.user.governance_profile
        score = profile.calculate_governance_score()

        if ML_AVAILABLE:
            try:
                borrower_data = {
                    'governance_score': float(score),
                    'board_independence_ratio': profile.board_independence_ratio,
                    'gender_diversity_ratio': profile.gender_diversity_ratio,
                    'compliance_violations': profile.compliance_violations,
                    'loan_amount': 5000000,
                    'tenure_months': 36,
                }

                default_risk = ml_engine.predict_default_risk(borrower_data)
                ml_pricing = ml_engine.optimize_rate(borrower_data)

                messages.success(
                    request,
                    f'✅ Governance score calculated: {score}\n'
                    f'🤖 ML Analysis:\n'
                    f'• Default Risk: {default_risk * 100:.1f}%\n'
                    f'• Recommended Rate: {ml_pricing["final_rate"]}%\n'
                    f'• Your Discount: {ml_pricing["governance_discount"]}%'
                )
            except Exception as e:
                messages.success(request, f'Governance score calculated: {score}')
        else:
            messages.success(request, f'Governance score calculated: {score}')

    except GovernanceProfile.DoesNotExist:
        messages.error(request, 'Please create your governance profile first')

    return redirect('governance:dashboard')