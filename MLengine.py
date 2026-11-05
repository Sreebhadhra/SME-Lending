"""
ML PRICING ENGINE FOR GOVCRED
Predicts:
1. Default risk based on governance + financial data
2. End-use compliance violations
3. Optimal interest rate pricing
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from decimal import Decimal

class GovCredMLEngine:
    """
    Machine Learning Engine for:
    - Default risk prediction
    - End-use compliance risk
    - Dynamic rate optimization
    """

    def __init__(self):
        self.default_model = None
        self.compliance_model = None
        self.rate_optimizer = None
        self.scaler = StandardScaler()

    def prepare_features(self, borrower_data):
        """
        Extract features from borrower data

        Args:
            borrower_data: dict with governance, financial, and transaction data

        Returns:
            numpy array of features
        """
        features = {
            # Governance Features
            'governance_score': borrower_data.get('governance_score', 0),
            'board_independence': borrower_data.get('board_independence_ratio', 0),
            'gender_diversity': borrower_data.get('gender_diversity_ratio', 0),
            'unionization': borrower_data.get('unionization_ratio', 0),
            'grievance_resolution': borrower_data.get('grievance_resolution_rate', 100),
            'supplier_screening': borrower_data.get('supplier_screening_rate', 0),
            'compliance_violations': borrower_data.get('compliance_violations', 0),
            'equal_pay_policy': int(borrower_data.get('equal_pay_policy', False)),
            'anti_corruption_policy': int(borrower_data.get('anti_corruption_policy', False)),

            # Financial Features
            'loan_amount': borrower_data.get('loan_amount', 0),
            'tenure_months': borrower_data.get('tenure_months', 36),
            'revenue': borrower_data.get('revenue', 0),
            'debt_to_equity': borrower_data.get('debt_to_equity', 0),
            'interest_coverage': borrower_data.get('interest_coverage', 0),

            # Transaction Features
            'green_spend_ratio': borrower_data.get('green_spend_ratio', 0),
            'invoice_compliance': borrower_data.get('invoice_compliance_rate', 0),
            'approved_vendor_ratio': borrower_data.get('approved_vendor_ratio', 0),
            'avg_transaction_size': borrower_data.get('avg_transaction_size', 0),

            # Historical Features
            'previous_loans': borrower_data.get('previous_loans', 0),
            'repayment_history': borrower_data.get('repayment_history_score', 0),
        }

        return np.array(list(features.values())).reshape(1, -1)

    def train_default_model(self, X_train, y_train):
        """
        Train default risk prediction model

        Args:
            X_train: Training features
            y_train: Default labels (0 = no default, 1 = default)
        """
        self.default_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        self.default_model.fit(X_train_scaled, y_train)

        print(f"Default Model Accuracy: {self.default_model.score(X_train_scaled, y_train):.3f}")

    def train_compliance_model(self, X_train, y_train):
        """
        Train end-use compliance risk model

        Args:
            X_train: Training features
            y_train: Compliance violation labels (0 = compliant, 1 = violation)
        """
        self.compliance_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            random_state=42
        )

        X_train_scaled = self.scaler.transform(X_train)
        self.compliance_model.fit(X_train_scaled, y_train)

        print(f"Compliance Model Accuracy: {self.compliance_model.score(X_train_scaled, y_train):.3f}")

    def train_rate_optimizer(self, X_train, y_train):
        """
        Train optimal rate prediction model

        Args:
            X_train: Training features
            y_train: Optimal interest rates
        """
        self.rate_optimizer = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )

        X_train_scaled = self.scaler.transform(X_train)
        self.rate_optimizer.fit(X_train_scaled, y_train)

        print(f"Rate Optimizer R²: {self.rate_optimizer.score(X_train_scaled, y_train):.3f}")

    def predict_default_risk(self, borrower_data):
        """
        Predict probability of default

        Returns:
            float: Probability of default (0-1)
        """
        if self.default_model is None:
            # Use rule-based fallback
            return self._rule_based_default_risk(borrower_data)

        features = self.prepare_features(borrower_data)
        features_scaled = self.scaler.transform(features)

        default_prob = self.default_model.predict_proba(features_scaled)[0][1]
        return default_prob

    def predict_compliance_risk(self, borrower_data):
        """
        Predict probability of end-use compliance violation

        Returns:
            float: Probability of violation (0-1)
        """
        if self.compliance_model is None:
            # Use rule-based fallback
            return self._rule_based_compliance_risk(borrower_data)

        features = self.prepare_features(borrower_data)
        features_scaled = self.scaler.transform(features)

        violation_prob = self.compliance_model.predict_proba(features_scaled)[0][1]
        return violation_prob

    def optimize_rate(self, borrower_data, base_rate=12.0):
        """
        Calculate optimal interest rate based on risk

        Args:
            borrower_data: Borrower features
            base_rate: Base interest rate

        Returns:
            dict: {
                'recommended_rate': float,
                'default_risk': float,
                'compliance_risk': float,
                'governance_discount': float,
                'risk_premium': float
            }
        """
        # Get governance discount (rule-based)
        governance_score = borrower_data.get('governance_score', 0)
        governance_discount = self._calculate_governance_discount(governance_score)

        # Get risk scores
        default_risk = self.predict_default_risk(borrower_data)
        compliance_risk = self.predict_compliance_risk(borrower_data)

        # Calculate risk premium
        # Higher risk = higher premium
        risk_premium = (default_risk * 2.0) + (compliance_risk * 1.5)

        # Final rate = Base - Governance Discount + Risk Premium
        recommended_rate = base_rate - governance_discount + risk_premium

        # Floor at 8%, cap at 15%
        recommended_rate = max(8.0, min(15.0, recommended_rate))

        return {
            'recommended_rate': round(recommended_rate, 2),
            'base_rate': base_rate,
            'governance_discount': governance_discount,
            'risk_premium': round(risk_premium, 2),
            'default_risk': round(default_risk * 100, 2),  # as percentage
            'compliance_risk': round(compliance_risk * 100, 2),  # as percentage
            'final_rate': round(recommended_rate, 2)
        }

    def _calculate_governance_discount(self, governance_score):
        """Calculate discount based on governance score"""
        if governance_score >= 800:
            return 3.0
        elif governance_score >= 700:
            return 2.5
        elif governance_score >= 600:
            return 2.0
        elif governance_score >= 500:
            return 1.5
        elif governance_score >= 400:
            return 1.0
        else:
            return 0.0

    def _rule_based_default_risk(self, borrower_data):
        """Fallback rule-based default risk"""
        governance_score = borrower_data.get('governance_score', 0)
        compliance_violations = borrower_data.get('compliance_violations', 0)

        # Base risk from governance
        if governance_score >= 700:
            base_risk = 0.05  # 5% default risk
        elif governance_score >= 500:
            base_risk = 0.15  # 15%
        else:
            base_risk = 0.30  # 30%

        # Add risk for violations
        violation_risk = compliance_violations * 0.05

        return min(base_risk + violation_risk, 0.95)

    def _rule_based_compliance_risk(self, borrower_data):
        """Fallback rule-based compliance risk"""
        governance_score = borrower_data.get('governance_score', 0)
        green_spend_ratio = borrower_data.get('green_spend_ratio', 0)
        invoice_compliance = borrower_data.get('invoice_compliance_rate', 0)

        # Base risk from governance
        if governance_score >= 700:
            base_risk = 0.05
        elif governance_score >= 500:
            base_risk = 0.20
        else:
            base_risk = 0.40

        # Adjust for spend patterns
        if green_spend_ratio < 0.80:  # Less than 80% green spending
            base_risk += 0.20

        if invoice_compliance < 0.90:  # Less than 90% invoice compliance
            base_risk += 0.15

        return min(base_risk, 0.95)

    def save_models(self, path='ml_models/'):
        """Save trained models"""
        import os
        os.makedirs(path, exist_ok=True)

        if self.default_model:
            joblib.dump(self.default_model, f'{path}default_model.pkl')
        if self.compliance_model:
            joblib.dump(self.compliance_model, f'{path}compliance_model.pkl')
        if self.rate_optimizer:
            joblib.dump(self.rate_optimizer, f'{path}rate_optimizer.pkl')
        joblib.dump(self.scaler, f'{path}scaler.pkl')

        print(f"Models saved to {path}")

    def load_models(self, path='ml_models/'):
        """Load trained models"""
        try:
            self.default_model = joblib.load(f'{path}default_model.pkl')
            self.compliance_model = joblib.load(f'{path}compliance_model.pkl')
            self.rate_optimizer = joblib.load(f'{path}rate_optimizer.pkl')
            self.scaler = joblib.load(f'{path}scaler.pkl')
            print(f"Models loaded from {path}")
        except Exception as e:
            print(f"Could not load models: {e}")


# ============================================
# DJANGO INTEGRATION
# ============================================

def integrate_ml_with_loan_application(loan_application):
    """
    Integrate ML engine with Django LoanApplication model

    Usage in views.py:
    from ml_engine import integrate_ml_with_loan_application

    pricing = integrate_ml_with_loan_application(loan_application)
    """
    engine = GovCredMLEngine()

    # Prepare borrower data
    try:
        gov_profile = loan_application.borrower.governance_profile
    except:
        gov_profile = None

    borrower_data = {
        'governance_score': float(gov_profile.governance_score) if gov_profile else 0,
        'board_independence_ratio': gov_profile.board_independence_ratio if gov_profile else 0,
        'gender_diversity_ratio': gov_profile.gender_diversity_ratio if gov_profile else 0,
        'unionization_ratio': gov_profile.unionization_ratio if gov_profile else 0,
        'grievance_resolution_rate': gov_profile.grievance_resolution_rate if gov_profile else 100,
        'supplier_screening_rate': gov_profile.supplier_screening_rate if gov_profile else 0,
        'compliance_violations': gov_profile.compliance_violations if gov_profile else 0,
        'equal_pay_policy': gov_profile.equal_pay_policy if gov_profile else False,
        'anti_corruption_policy': gov_profile.anti_corruption_policy if gov_profile else False,

        'loan_amount': float(loan_application.requested_amount),
        'tenure_months': loan_application.tenure_months,
        'revenue': 10000000,  # Fetch from financials
        'debt_to_equity': 0.5,  # Fetch from financials
        'interest_coverage': 2.5,  # Fetch from financials

        'green_spend_ratio': 0.95,  # From ledger
        'invoice_compliance_rate': 0.98,  # From ledger
        'approved_vendor_ratio': 1.0,  # From ledger
        'avg_transaction_size': 50000,

        'previous_loans': 0,
        'repayment_history_score': 100,
    }

    # Get ML predictions
    pricing = engine.optimize_rate(borrower_data, base_rate=12.0)

    return pricing


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == '__main__':
    # Initialize engine
    engine = GovCredMLEngine()

    # Example borrower with GOOD governance
    good_borrower = {
        'governance_score': 750,
        'board_independence_ratio': 40,
        'gender_diversity_ratio': 30,
        'unionization_ratio': 20,
        'grievance_resolution_rate': 90,
        'supplier_screening_rate': 85,
        'compliance_violations': 0,
        'equal_pay_policy': True,
        'anti_corruption_policy': True,

        'loan_amount': 5000000,
        'tenure_months': 36,
        'revenue': 50000000,
        'debt_to_equity': 0.4,
        'interest_coverage': 3.0,

        'green_spend_ratio': 0.98,
        'invoice_compliance_rate': 1.0,
        'approved_vendor_ratio': 1.0,
        'avg_transaction_size': 75000,

        'previous_loans': 2,
        'repayment_history_score': 95,
    }

    # Example borrower with POOR governance
    poor_borrower = {
        'governance_score': 350,
        'board_independence_ratio': 10,
        'gender_diversity_ratio': 5,
        'unionization_ratio': 0,
        'grievance_resolution_rate': 40,
        'supplier_screening_rate': 20,
        'compliance_violations': 3,
        'equal_pay_policy': False,
        'anti_corruption_policy': False,

        'loan_amount': 5000000,
        'tenure_months': 36,
        'revenue': 30000000,
        'debt_to_equity': 1.2,
        'interest_coverage': 1.2,

        'green_spend_ratio': 0.70,
        'invoice_compliance_rate': 0.75,
        'approved_vendor_ratio': 0.80,
        'avg_transaction_size': 100000,

        'previous_loans': 0,
        'repayment_history_score': 0,
    }

    print("=" * 60)
    print("GOOD GOVERNANCE BORROWER")
    print("=" * 60)
    good_pricing = engine.optimize_rate(good_borrower)
    print(f"Governance Score: {good_borrower['governance_score']}")
    print(f"Default Risk: {good_pricing['default_risk']}%")
    print(f"Compliance Risk: {good_pricing['compliance_risk']}%")
    print(f"Base Rate: {good_pricing['base_rate']}%")
    print(f"Governance Discount: -{good_pricing['governance_discount']}%")
    print(f"Risk Premium: +{good_pricing['risk_premium']}%")
    print(f"FINAL RATE: {good_pricing['final_rate']}%")

    print("\n" + "=" * 60)
    print("POOR GOVERNANCE BORROWER")
    print("=" * 60)
    poor_pricing = engine.optimize_rate(poor_borrower)
    print(f"Governance Score: {poor_borrower['governance_score']}")
    print(f"Default Risk: {poor_pricing['default_risk']}%")
    print(f"Compliance Risk: {poor_pricing['compliance_risk']}%")
    print(f"Base Rate: {poor_pricing['base_rate']}%")
    print(f"Governance Discount: -{poor_pricing['governance_discount']}%")
    print(f"Risk Premium: +{poor_pricing['risk_premium']}%")
    print(f"FINAL RATE: {poor_pricing['final_rate']}%")

    print("\n" + "=" * 60)
    print(f"RATE DIFFERENCE: {poor_pricing['final_rate'] - good_pricing['final_rate']:.2f}%")
    print("=" * 60)