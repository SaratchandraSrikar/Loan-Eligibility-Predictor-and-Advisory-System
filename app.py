from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import pandas as pd
import numpy as np
import shap
import os
import json


app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # replace with env in production

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "loan_app.db")

# Automatically switch to Cloud Database if detecting Render Environment Variable
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =====================================================
# DATABASE MODELS
# =====================================================


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    applications = db.relationship("LoanApplication", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    dependents = db.Column(db.Integer)
    education = db.Column(db.String(32))
    self_employed = db.Column(db.String(8))
    income = db.Column(db.Float)
    loan_amount = db.Column(db.Float)
    loan_term = db.Column(db.Float)
    cibil = db.Column(db.Float)
    res_assets = db.Column(db.Float)
    com_assets = db.Column(db.Float)
    lux_assets = db.Column(db.Float)
    bank_assets = db.Column(db.Float)

    loan_status = db.Column(db.String(8))
    interest_rate = db.Column(db.Float)
    emi = db.Column(db.Float)
    dti = db.Column(db.Float)
    lti = db.Column(db.Float)
    aai = db.Column(db.Float)
    max_eligible_loan = db.Column(db.Float)
    risk_category = db.Column(db.String(32))
    loan_type = db.Column(db.String(32))
    cibil_category = db.Column(db.String(32))

    reasons = db.Column(db.Text)
    suggestions = db.Column(db.Text)

    created_at = db.Column(db.DateTime, server_default=db.func.now())


class CibilReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    age = db.Column(db.Float)
    employment = db.Column(db.String(64))
    experience = db.Column(db.Float)
    
    income = db.Column(db.Float)
    expenses = db.Column(db.Float)
    emi = db.Column(db.Float)
    
    active_loans = db.Column(db.Float)
    outstanding_loan = db.Column(db.Float)
    home_loans = db.Column(db.Float)
    car_loans = db.Column(db.Float)
    personal_loans = db.Column(db.Float)
    education_loans = db.Column(db.Float)
    
    credit_cards = db.Column(db.Float)
    cc_limit = db.Column(db.Float)
    cc_used = db.Column(db.Float)
    
    missed_payments = db.Column(db.Float)
    max_delay = db.Column(db.String(64))
    default_history = db.Column(db.String(16))
    settled_loans = db.Column(db.String(16))
    
    history_years = db.Column(db.Float)
    closed_loans = db.Column(db.Float)
    inquiries = db.Column(db.Float)
    
    cibil_score = db.Column(db.Float)
    category = db.Column(db.String(32))

    created_at = db.Column(db.DateTime, server_default=db.func.now())

with app.app_context():
    db.create_all()


# =====================================================
# LOAD MODEL AND SCALER
# =====================================================

MODEL_PATH = os.path.join(os.path.dirname(__file__), "loan_model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)


# =====================================================
# CORE FINANCIAL UTILITIES
# =====================================================

def calculate_interest(cibil: float) -> float:
    """Simple rule-based interest approximation driven by CIBIL."""
    return max(1.0, 6.0 + (750 - cibil) / 100.0)


def calculate_emi(loan_amount: float, rate: float, term_years: float) -> float:
    if rate <= 0 or term_years <= 0 or loan_amount <= 0:
        return 0.0
    R = rate / (12 * 100)  # monthly interest
    N = term_years * 12    # number of months
    denom = (1 + R) ** N - 1
    if denom == 0:
        return 0.0
    return loan_amount * R * (1 + R) ** N / denom


def calculate_dti(emi: float, income_annum: float) -> float:
    if income_annum <= 0:
        return 0.0
    return emi / (income_annum / 12.0)


def max_loan(income_annum: float, rate: float, term_years: float) -> float:
    if income_annum <= 0 or rate <= 0 or term_years <= 0:
        return 0.0
    max_emi = income_annum / 12.0 * 0.4  # 40% of monthly income
    R = rate / (12 * 100)
    N = term_years * 12
    denom = R * (1 + R) ** N
    if denom == 0:
        return 0.0
    return max_emi * ((1 + R) ** N - 1) / denom


def calculate_lti(loan_amount: float, income_annum: float) -> float:
    if income_annum <= 0:
        return 0.0
    return loan_amount / income_annum


def total_assets(res_assets: float, com_assets: float, lux_assets: float, bank_assets: float) -> float:
    return max(0.0, res_assets) + max(0.0, com_assets) + max(0.0, lux_assets) + max(0.0, bank_assets)


# =====================================================
# ADVISORY & SCORING UTILITIES
# =====================================================

def cibil_category(cibil: float) -> str:
    if cibil < 600:
        return "Poor"
    if cibil < 650:
        return "Fair"
    if cibil < 700:
        return "Good"
    if cibil < 750:
        return "Very Good"
    return "Excellent"


def calculate_aai(cibil: float, dti: float, lti: float, assets_value: float, income_annum: float) -> float:
    """
    Applicant Affordability Index (0–100).
    Combines credit quality, leverage, and buffer from assets vs income.
    """
    # Base from CIBIL (scaled roughly from 300–900 to 0–60)
    cibil_component = np.clip((cibil - 300) / 600 * 60, 0, 60)

    # DTI component (higher DTI => lower score), 0–20
    if dti <= 0.3:
        dti_component = 20
    elif dti <= 0.4:
        dti_component = 14
    elif dti <= 0.5:
        dti_component = 8
    else:
        dti_component = 3

    # LTI component, 0–10
    if lti <= 2:
        lti_component = 10
    elif lti <= 4:
        lti_component = 6
    elif lti <= 6:
        lti_component = 3
    else:
        lti_component = 1

    # Asset buffer: assets vs annual income, 0–10
    income_annum = max(income_annum, 1.0)
    asset_ratio = assets_value / income_annum
    if asset_ratio >= 5:
        asset_component = 10
    elif asset_ratio >= 2:
        asset_component = 7
    elif asset_ratio >= 1:
        asset_component = 4
    else:
        asset_component = 1

    raw_score = cibil_component + dti_component + lti_component + asset_component
    return float(np.clip(raw_score, 0, 100))


def risk_category(aai: float) -> str:
    if aai >= 85:
        return "Very Safe"
    if aai >= 70:
        return "Safe"
    if aai >= 55:
        return "Moderate"
    if aai >= 40:
        return "Risky"
    return "Very Risky"


def loan_type_recommendation(
    loan_amount: float,
    income_annum: float,
    res_assets: float,
    com_assets: float,
    lux_assets: float,
    education: str,
    cibil: float,
) -> str:
    """
    Simple heuristic-based recommendation for loan type.
    """
    assets_val = total_assets(res_assets, com_assets, lux_assets, 0.0)
    # Treat all amounts as in local currency (e.g. INR)

    # Very large ticket -> likely home loan
    if loan_amount >= income_annum * 3 or res_assets > 0.5 * loan_amount:
        return "Home Loan"

    # Mid-ticket amounts, moderate assets -> car loan
    if income_annum * 0.8 <= loan_amount <= income_annum * 2.5 and lux_assets > 0:
        return "Car Loan"

    # Education loan: lower income, moderate loan and good education
    if income_annum < loan_amount * 1.5 and education == "Graduate" and cibil >= 650:
        return "Education Loan"

    # Fallbacks based on loan size vs income
    if loan_amount <= income_annum * 0.8:
        return "Personal Loan"

    return "Personal Loan"


def multi_bank_emi_comparison(loan_amount: float, term_years: float, loan_type: str, cibil: float, dti: float, ai_rate: float):
    """
    Compare EMI across real banks using dynamic rates based on loan_type and CIBIL,
    along with Approval Probability based on DTI and CIBIL criteria.
    """
    # Base rates per loan type
    # Bank : {"Home": x, "Car": y, "Personal": z, "Education": w, "IsNBFC": False}
    bank_profiles = {
        "HDFC Bank": {"Home Loan": 8.5, "Car Loan": 8.75, "Personal Loan": 10.5, "Education Loan": 9.5, "nbfc": False},
        "SBI": {"Home Loan": 8.4, "Car Loan": 8.65, "Personal Loan": 11.0, "Education Loan": 8.5, "nbfc": False},
        "ICICI Bank": {"Home Loan": 8.75, "Car Loan": 8.9, "Personal Loan": 10.75, "Education Loan": 9.5, "nbfc": False},
        "Bajaj Finserv": {"Home Loan": 9.0, "Car Loan": 10.0, "Personal Loan": 12.0, "Education Loan": 10.5, "nbfc": True},
    }
    
    # Calculate Risk Premium
    risk_premium = 0.0
    if cibil < 650:
        risk_premium = 1.5
    elif cibil < 700:
        risk_premium = 0.75
    elif cibil < 750:
        risk_premium = 0.25
        
    comparison = []
    
    for name, profile in bank_profiles.items():
        base_rate = profile.get(loan_type, profile["Personal Loan"])
        final_rate = base_rate + risk_premium
        
        # Approval Probability Logic
        prob = "Low"
        is_nbfc = profile["nbfc"]
        
        if not is_nbfc:
            if cibil >= 750 and dti <= 0.4:
                prob = "High"
            elif cibil >= 700 and dti <= 0.5:
                prob = "Medium"
        else:
            # NBFCs are more relaxed
            if cibil >= 650 and dti <= 0.55:
                prob = "High"
            elif cibil >= 600 and dti <= 0.65:
                prob = "Medium"
                
        emi = calculate_emi(loan_amount, final_rate, term_years)
        
        comparison.append({
            "bank": name,
            "rate": round(final_rate, 2),
            "emi": round(emi, 2),
            "prob": prob,
            "is_user_profile": False # Flag for frontend UI
        })
        
    # Append the "AI Recommendation" 
    ai_emi = calculate_emi(loan_amount, ai_rate, term_years)
    comparison.append({
        "bank": "Your Profile (AI)",
        "rate": round(ai_rate, 2),
        "emi": round(ai_emi, 2),
        "prob": "Current Fit", # Visual Distinction
        "is_user_profile": True
    })

    # Sort by EMI ascending (best first)
    comparison.sort(key=lambda x: x["emi"])
    return comparison


def calculate_cibil_insights(data: dict) -> dict:
    """
    Computes an estimated CIBIL score based on detailed behavioral and financial inputs.
    Returns the score, category, key factors, and actionable tips.
    """
    # Helpers
    def to_float(key, default=0.0):
        try:
            return float(data.get(key, default))
        except (TypeError, ValueError):
            return default

    def to_int(key, default=0):
        try:
            return int(float(data.get(key, default)))
        except (TypeError, ValueError):
            return default

    # Extract inputs
    age = to_float("age", 30.0)
    employment = data.get("employment", "Salaried")
    experience = to_float("experience", 5.0)
    
    income = to_float("income", 50000.0)
    expenses = to_float("expenses", 30000.0)
    emi = to_float("emi", 10000.0)
    
    active_loans = to_int("active_loans", 1)
    outstanding_loan = to_float("outstanding_loan", 500000.0)
    home_loans = to_int("home_loans", 0)
    car_loans = to_int("car_loans", 0)
    personal_loans = to_int("personal_loans", 0)
    education_loans = to_int("education_loans", 0)
    
    credit_cards = to_int("credit_cards", 1)
    cc_limit = to_float("cc_limit", 100000.0)
    cc_used = to_float("cc_used", 30000.0)
    
    missed_payments = to_int("missed_payments", 0)
    max_delay = data.get("max_delay", "No Delay")
    default_history = data.get("default_history", "No")
    settled_loans = data.get("settled_loans", "No")
    
    history_years = to_float("history_years", 3.0)
    closed_loans = to_int("closed_loans", 0)
    inquiries = to_int("inquiries", 1)

    # 1. Normalization (0-1 scales) and Insights lists
    factors = []
    tips = []

    # Repayment History (35%)
    # Starts at 1.0. Deduct for misses, delays, settled. Default sets it to 0.
    repayment_norm = 1.0
    if missed_payments > 0:
        penalty = min(0.5, missed_payments * 0.1) # Up to 50% drop for misses
        repayment_norm -= penalty
        factors.append(f"Missed {missed_payments} payment(s) negatively impacts your core history.")
        tips.append("Always pay EMIs and card dues on or before the due date.")

    if max_delay == "30 Days":
        repayment_norm -= 0.15
        factors.append("A recent 30-day delay in payments was noted.")
    elif max_delay == "60 Days":
        repayment_norm -= 0.3
        factors.append("A 60-day delay in payments shows moderate repayment risk.")
        tips.append("Clear all overdue accounts immediately to stop further score damage.")
    elif max_delay == "90+ Days":
        repayment_norm -= 0.5
        factors.append("A 90+ day delay severely damages repayment history.")
        tips.append("Contact your lender to restructure or clear 90+ day overdues.")

    if settled_loans == "Yes":
        repayment_norm -= 0.3
        factors.append("'Settled' (instead of 'Closed') loans stay on your report and lower scores.")
        tips.append("Try to fully pay off and 'Close' accounts rather than settling them.")

    if default_history == "Yes":
        repayment_norm = 0.0
        factors.append("A previous Loan Default is dragging down your score significantly.")
        tips.append("Rebuild credit by obtaining a secured credit card and making flawless payments.")

    repayment_norm = max(0.0, repayment_norm)
    if repayment_norm == 1.0:
        factors.append("Flawless repayment history is strongly boosting your score.")

    # Credit Utilization (25%)
    # High utilization (>70%) is a known penalty
    cc_limit_total = max(cc_limit, 1.0) # Avoid div by zero
    utilization_ratio = cc_used / cc_limit_total if credit_cards > 0 else 0.0
    
    if credit_cards == 0:
        util_norm = 0.5 # Neutral if no cards
    else:
        if utilization_ratio <= 0.3:
            util_norm = 1.0
            factors.append(f"Low credit card utilization ({int(utilization_ratio*100)}%) is excellent.")
        elif utilization_ratio <= 0.6:
            util_norm = 0.7
            factors.append(f"Moderate credit card utilization ({int(utilization_ratio*100)}%).")
        elif utilization_ratio <= 0.9:
            util_norm = 0.3
            factors.append(f"High credit card utilization ({int(utilization_ratio*100)}%) is penalizing your score.")
            tips.append("Keep your credit card balances below 30% of your total limit.")
        else:
            util_norm = 0.0
            factors.append(f"Maxed out credit cards ({int(utilization_ratio*100)}%) represent a high risk factor.")
            tips.append("Pay down your revolving credit debt to drastically improve your score.")

    # Apply global penalty: High utilization (>70%) reduces score
    high_util_penalty = 1.0
    if utilization_ratio > 0.7:
        high_util_penalty = 0.9 # Subtracts 10% from final score later

    # Credit History Length (15%)
    # Normalize with 15 years as 'excellent' (1.0)
    history_norm = min(1.0, history_years / 10.0) 
    if history_years > 7:
        factors.append(f"Long credit vintage ({int(history_years)} years) adds stability to your profile.")
    elif history_years < 2:
        factors.append("Your credit history is quite new, which limits your maximum score.")
        tips.append("Maintain older credit card accounts to increase your average credit age.")

    # Credit Mix (10%)
    # Secured vs Unsecured
    secured_count = home_loans + car_loans
    unsecured_count = personal_loans + education_loans + active_loans - (home_loans + car_loans)
    unsecured_count = max(0, unsecured_count) # Fallback if active_loans mismatch

    mix_norm = 0.5 # Default
    if secured_count > 0 and unsecured_count > 0:
        mix_norm = 1.0
        factors.append("You have a healthy mix of secured and unsecured loans.")
    elif secured_count > 0:
        mix_norm = 0.8
    elif unsecured_count > 0:
        mix_norm = 0.6
        if unsecured_count > 3:
            factors.append("Too many unsecured loans relative to secured loans.")
            tips.append("Avoid taking out multiple personal loans concurrently.")

    # Credit Inquiries (10%)
    # Global penalty for too many inquiries (>5)
    inquiry_norm = 1.0
    if inquiries == 0:
        inquiry_norm = 1.0
    elif inquiries <= 2:
        inquiry_norm = 0.9
    elif inquiries <= 5:
        inquiry_norm = 0.5
        factors.append(f"{inquiries} recent inquiries indicate credit-seeking behavior.")
    else:
        inquiry_norm = 0.0
        factors.append(f"Excessive recent inquiries ({inquiries}) are dragging down your score.")
        tips.append("Stop applying for new credit cards or loans for the next 6 months.")

    too_many_inquiries_penalty = 1.0
    if inquiries > 5:
        too_many_inquiries_penalty = 0.9 # 10% penalty on final multiplier

    # Income Stability (5%)
    # Derived from Employment, Exp, and EMI-to-Income
    income_norm = 0.8
    if employment in ["Salaried", "Self-employed"] and experience > 3:
        income_norm = 1.0
    elif employment == "Unemployed":
        income_norm = 0.2
        factors.append("Lack of stable employment negatively impacts perceived capacity.")

    emi_ratio = emi / max(income, 1.0)
    if emi_ratio > 0.6:
        income_norm *= 0.5
        factors.append(f"Extremely high EMI-to-Income ratio ({int(emi_ratio*100)}%) signals debt stress.")
        tips.append("Try to foreclose high-interest loans to free up monthly cash flow.")

    # 2. Final Score Calculation
    # Weights: Repayment (35%), Util (25%), History (15%), Mix (10%), Inquiries (10%), Stability (5%)
    weighted_norm = (
        repayment_norm * 0.35 +
        util_norm * 0.25 +
        history_norm * 0.15 +
        mix_norm * 0.10 +
        inquiry_norm * 0.10 +
        income_norm * 0.05
    )

    # Global penalties applied to the normalized score
    if default_history == "Yes":
        weighted_norm *= 0.7 # 30% flat penalty for defaults on top of 0 repayment score
    
    weighted_norm *= high_util_penalty
    weighted_norm *= too_many_inquiries_penalty

    # Formula: Score = 300 + (Normalized Score × 600)
    final_score = 300.0 + (weighted_norm * 600.0)
    final_score = float(np.clip(final_score, 300, 900))

    # Category determination
    if final_score < 600:
        category = "Poor"
    elif final_score < 650:
        category = "Risky"
    elif final_score < 700:
        category = "Fair"
    elif final_score < 750:
        category = "Good"
    else:
        category = "Excellent"

    # Fallback tips if none
    if not tips and final_score < 800:
        tips.append("Keep your credit card usage low and pay EMIs on time to reach excellent tiers.")
    elif not tips:
        tips.append("Keep doing exactly what you're doing. Your profile is exceptionally strong.")

    # Take top 4 factors/tips for UI cleanliness
    return {
        "cibil_score": round(final_score, 0),
        "category": category,
        "factors": factors[:4],
        "tips": tips[:4]
    }


# =====================================================
# MAIN PREDICTION LOGIC (BACKEND)
# =====================================================

FEATURE_COLUMNS = [
    "no_of_dependents",
    "education",
    "self_employed",
    "income_annum",
    "loan_amount",
    "loan_term",
    "cibil_score",
    "residential_assets_value",
    "commercial_assets_value",
    "luxury_assets_value",
    "bank_asset_value",
]

# Generate standard normal dummy data (mean 0, std 1) mimicking scaled bounds for KernelExplainer
import shap
dummy_X_scaled = np.random.randn(20, len(FEATURE_COLUMNS))
try:
    explainer = shap.KernelExplainer(model.predict, dummy_X_scaled)
except:
    explainer = None


def run_prediction(
    dependents: float,
    education: str,
    self_employed: str,
    income: float,
    loan_amount: float,
    loan_term: float,
    cibil: float,
    res_assets: float,
    com_assets: float,
    lux_assets: float,
    bank_assets: float,
):
    # Encode categorical
    education_val = 1 if education == "Graduate" else 0
    self_val = 1 if self_employed == "Yes" else 0

    X = pd.DataFrame(
        [
            [
                dependents,
                education_val,
                self_val,
                income,
                loan_amount,
                loan_term,
                cibil,
                res_assets,
                com_assets,
                lux_assets,
                bank_assets,
            ]
        ],
        columns=FEATURE_COLUMNS,
    )

    # Scale and predict
    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]
    loan_status_model = "Yes" if prediction == 0 else "No"

    # Financial calculations
    rate = calculate_interest(cibil)
    emi = calculate_emi(loan_amount, rate, loan_term)
    dti = calculate_dti(emi, income)
    maxloan = max_loan(income, rate, loan_term)
    lti = calculate_lti(loan_amount, income)
    assets_value = total_assets(res_assets, com_assets, lux_assets, bank_assets)
    aai = calculate_aai(cibil, dti, lti, assets_value, income)
    risk = risk_category(aai)
    cibil_cat = cibil_category(cibil)
    loan_type = loan_type_recommendation(
        loan_amount,
        income,
        res_assets,
        com_assets,
        lux_assets,
        education,
        cibil,
    )
    bank_comparison = multi_bank_emi_comparison(
        loan_amount, loan_term, loan_type, cibil, dti, rate
    )

    # Advisory text
    advisory = []
    # Guardrails so the UI doesn't show "Eligible" for clearly unaffordable inputs.
    loan_status = loan_status_model
    if income <= 0 or loan_amount <= 0 or loan_term <= 0:
        loan_status = "No"
        advisory.append("Missing/invalid income, loan amount, or tenure can make a loan ineligible.")
    else:
        # If requested loan exceeds the calculated safe affordability ceiling, mark ineligible.
        if maxloan > 0 and loan_amount > (maxloan * 1.05):
            loan_status = "No"
            advisory.append("Requested loan amount is above your calculated safe eligibility ceiling.")
        # Very high EMI burden is typically a rejection driver.
        if dti > 0.6:
            loan_status = "No"
            advisory.append("DTI is extremely high; most lenders reject at this burden level.")
        # Very low credit score bands typically fail basic lending cutoffs.
        if cibil < 550:
            loan_status = "No"
            advisory.append("CIBIL is very low; many lenders have minimum cutoffs before approval.")

    if cibil < 700:
        advisory.append("Improve your CIBIL score to unlock better interest rates.")
    if loan_amount > maxloan:
        advisory.append("Requested loan amount exceeds your safe eligibility limit.")
    if dti > 0.4:
        advisory.append("Your EMI burden is high compared to your income.")
    if cibil >= 750:
        advisory.append("You are eligible for low-interest loans due to a strong CIBIL score.")

    # SHAP explanations (top 3) - Context Aware Sorting
    if explainer is not None:
        try:
            shap_values_raw = explainer.shap_values(X_scaled)
            values = shap_values_raw[0] if isinstance(shap_values_raw, list) else shap_values_raw[0]
            feature_importance = list(zip(FEATURE_COLUMNS, values))
        except Exception as e:
            print(f"SHAP failed: {e}")
            feature_importance = [(col, X_scaled[0][i]) for i, col in enumerate(FEATURE_COLUMNS)]
    else:
        feature_importance = [(col, X_scaled[0][i]) for i, col in enumerate(FEATURE_COLUMNS)]

    main_reasons = []
    
    # Context-Aware Ranking:
    # Model target: 0 = Approved, 1 = Rejected.
    # Therefore, negative SHAP values drive APPROVAL, positive SHAP values drive REJECTION.
    if loan_status == "Yes":
        # Sort by most negative (strongest approval drivers)
        feature_importance.sort(key=lambda x: x[1])
        for feature, val in feature_importance[:3]:
            if val < 0:
                main_reasons.append(f"{feature} was a key driver securing your APPROVAL.")
            else:
                main_reasons.append(f"Despite {feature} acting as a minor risk factor, your profile was still strong enough to pass.")
    else:
        # Sort by most positive (strongest rejection drivers)
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        for feature, val in feature_importance[:3]:
            if val > 0:
                main_reasons.append(f"{feature} was a major critical reason for REJECTION.")
            else:
                main_reasons.append(f"{feature} was strong, but not enough to outweigh the risks and secure approval.")

    return {
        "loan_status": loan_status,
        "interest_rate": round(rate, 2),
        "emi": round(emi, 2),
        "dti": round(dti, 2),
        "lti": round(lti, 2),
        "aai": round(aai, 2),
        "max_eligible_loan": round(maxloan, 2),
        "risk_category": risk,
        "loan_type": loan_type,
        "cibil_category": cibil_cat,
        "advisory": advisory,
        "main_reasons": main_reasons,
        "bank_comparison": bank_comparison,
    }


# =====================================================
# FLASK ROUTES
# =====================================================


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


@app.route("/")
def home():
    return render_template("home.html", user=current_user())


@app.route("/analyze")
@login_required
def analyze():
    user = current_user()
    last_run = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.created_at.desc()).first()
    return render_template("index.html", user=user, last_run=last_run)


@app.route("/about")
def about():
    return render_template("about.html", user=current_user())


@app.route("/cibil")
@login_required
def cibil_page():
    user = current_user()
    last_run = CibilReport.query.filter_by(user_id=user.id).order_by(CibilReport.created_at.desc()).first()
    return render_template("cibil.html", user=user, last_run=last_run)


@app.route("/analytics")
@login_required
def analytics():
    user = current_user()
    apps = (
        LoanApplication.query.filter_by(user_id=user.id)
        .order_by(LoanApplication.created_at.asc())
        .all()
    )

    labels = [a.created_at.strftime("%d %b") if a.created_at else f"Run {i+1}" for i, a in enumerate(apps)]
    cibil_scores = [a.cibil or 0 for a in apps]
    aai_scores = [a.aai or 0 for a in apps]

    risk_counts = {}
    loan_type_counts = {}
    scatter_points = []
    dti_values = []
    lti_values = []

    for a in apps:
        risk_key = a.risk_category or "Unknown"
        loan_key = a.loan_type or "Other"
        risk_counts[risk_key] = risk_counts.get(risk_key, 0) + 1
        loan_type_counts[loan_key] = loan_type_counts.get(loan_key, 0) + 1
        scatter_points.append({"x": a.income or 0, "y": a.loan_amount or 0})
        if a.dti is not None:
            dti_values.append(a.dti)
        if a.lti is not None:
            lti_values.append(a.lti)

    avg_cibil = round(sum(cibil_scores) / len(cibil_scores), 1) if cibil_scores else 0
    avg_aai = round(sum(aai_scores) / len(aai_scores), 1) if aai_scores else 0
    avg_dti = round(sum(dti_values) / len(dti_values), 3) if dti_values else 0
    avg_lti = round(sum(lti_values) / len(lti_values), 3) if lti_values else 0

    top_risk = max(risk_counts, key=risk_counts.get) if risk_counts else "—"

    # Trend information (first vs last)
    if len(apps) >= 2:
        first = apps[0]
        last = apps[-1]
        cibil_change = (last.cibil or 0) - (first.cibil or 0)
        aai_change = (last.aai or 0) - (first.aai or 0)

        def direction(delta: float) -> str:
            if delta > 5:
                return "up"
            if delta < -5:
                return "down"
            return "flat"

        cibil_dir = direction(cibil_change)
        aai_dir = direction(aai_change)

        risk_order = {"Very Safe": 4, "Safe": 3, "Moderate": 2, "Risky": 1, "Very Risky": 0}
        first_risk_score = risk_order.get(first.risk_category or "", 2)
        last_risk_score = risk_order.get(last.risk_category or "", 2)
        risk_delta = last_risk_score - first_risk_score
        if risk_delta > 0:
            risk_trend = "Improving"
        elif risk_delta < 0:
            risk_trend = "Deteriorating"
        else:
            risk_trend = "Stable"
    else:
        cibil_change = 0
        aai_change = 0
        cibil_dir = "flat"
        aai_dir = "flat"
        risk_trend = "Not enough data"

    # Affordability Engine
    affordability = {}
    if apps:
        import math
        last = apps[-1]
        monthly_income = (last.income or 0) / 12
        safe_emi = monthly_income * 0.20
        actual_emi = last.emi or 0
        
        ratio = actual_emi / monthly_income if monthly_income > 0 else 1
        if ratio <= 0.20:
            interpretation = "This loan is very safe and comfortably manageable."
            status_color = "green"
        elif ratio <= 0.30:
            interpretation = "This is acceptable, but monitor your expenses."
            status_color = "amber"
        else:
            interpretation = "This may strain your finances. Consider reducing loan amount or increasing tenure."
            status_color = "red"

        gap = actual_emi - safe_emi
        gap_insight = f"Your EMI exceeds the safest limit by ₹{gap:,.0f}" if gap > 0 else ""
        
        adjustments = []
        if gap > 0 and monthly_income > 0 and last.interest_rate:
            r = (last.interest_rate / 100) / 12
            n = (last.loan_term or 1) * 12
            P = last.loan_amount or 0
            
            # Reduce principal suggestion
            if r > 0 and n > 0:
                max_p = safe_emi * (((1+r)**n - 1) / (r * (1+r)**n))
                reduce_by = P - max_p
                if reduce_by > 0:
                    adjustments.append(f"Reduce loan by ₹{(reduce_by / 100000):.1f}L to stay within safe EMI.")
            
            # Increase tenure suggestion
            if P * r < safe_emi:
                try:
                    new_n_months = math.log(safe_emi / (safe_emi - P * r)) / math.log(1 + r)
                    new_years = new_n_months / 12
                    current_years = last.loan_term or 1
                    
                    max_allowed_years = 30 if "Home" in str(last.loan_type) else 7
                    
                    if current_years < max_allowed_years:
                        years_to_add = math.ceil(new_years - current_years)
                        if current_years + years_to_add <= max_allowed_years:
                            adjustments.append(f"Increase tenure by {years_to_add} years to reduce EMI safely limit.")
                        else:
                            adjustments.append(f"Even extending tenure to maximum {max_allowed_years} years won't bring EMI under 20%.")
                except Exception:
                    pass
            else:
                adjustments.append("Interest alone surpasses your 20% safe bound; lowering EMI via tenure is impossible without cutting principal.")
                
        affordability = {
            "monthly_income": monthly_income,
            "safe_emi": safe_emi,
            "actual_emi": actual_emi,
            "interpretation": interpretation,
            "status_color": status_color,
            "gap_insight": gap_insight,
            "adjustments": adjustments
        }

    analytics_payload = {
        "summary": {
            "total_runs": len(apps),
            "avg_cibil": avg_cibil,
            "avg_aai": avg_aai,
            "top_risk": top_risk,
        },
        "timeseries": {
            "labels": labels,
            "cibil": cibil_scores,
            "aai": aai_scores,
        },
        "profile": {
            "avg_cibil": avg_cibil,
            "avg_aai": avg_aai,
            "avg_dti": avg_dti,
            "avg_lti": avg_lti,
        },
        "trends": {
            "cibil_change": round(cibil_change, 1),
            "cibil_direction": cibil_dir,
            "aai_change": round(aai_change, 1),
            "aai_direction": aai_dir,
            "risk_trend": risk_trend,
        },
        "risk_counts": risk_counts,
        "loan_type_counts": loan_type_counts,
        "income_loan_points": scatter_points,
        "affordability": affordability
    }

    return render_template("analytics.html", user=user, analytics=analytics_payload)


@app.route("/api/export-report/latest")
@login_required
def export_latest_report():
    from fpdf import FPDF
    import json
    user = current_user()
    last = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.created_at.desc()).first()
    
    if not last:
        flash("No simulation found to export.", "warning")
        return redirect(url_for("analyze"))

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(37, 99, 235) # blue-600
            self.rect(0, 0, 210, 30, 'F')
            self.set_y(10)
            self.set_font("helvetica", "B", 16)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, "Official Loan Advisory Record", align="C")
            self.ln(10)
            self.set_font("helvetica", "", 10)
            self.set_text_color(240, 240, 240)
            self.cell(0, 4, f"Generated for: {user.name.title()} ({user.email})", align="C")
            self.ln(20)
            
        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.add_page()
    
    pdf.set_y(40)
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "1. Eligibility Output", ln=True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.set_fill_color(240, 248, 255)
    pdf.cell(50, 10, "Eligibility Status:", border=1, fill=True)
    
    if last.loan_status == "Yes":
        pdf.set_text_color(22, 163, 74) # green
        status_text = "APPROVED (Eligible)"
    else:
        pdf.set_text_color(220, 38, 38) # red
        status_text = "REJECTED (Ineligible)"
        
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f" {status_text}", border=1, ln=True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(50, 10, "Risk Category:", border=1, fill=True)
    pdf.cell(0, 10, f" {last.risk_category}", border=1, ln=True)
    
    pdf.cell(50, 10, "Suggested Product:", border=1, fill=True)
    pdf.cell(0, 10, f" {last.loan_type}", border=1, ln=True)
    
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "2. Financial Calculation", ln=True)
    
    pdf.set_font("helvetica", "", 11)
    
    def add_row(key, val):
        pdf.cell(70, 8, key, border=1)
        pdf.cell(120, 8, str(val), border=1, ln=True)
        
    add_row("Principal Requested", f"Rs. {last.loan_amount:,.2f}")
    add_row("Income (Annual)", f"Rs. {last.income:,.2f}")
    add_row("CIBIL Score", f"{last.cibil}")
    add_row("Estimated Interest Rate", f"{(last.interest_rate or 0)}%")
    add_row("Projected EMI", f"Rs. {(last.emi or 0):,.2f}")
    add_row("Debt-to-Income (DTI)", f"{(last.dti or 0)*100:.1f}%")
    add_row("Max Eligible Principal Ceiling", f"Rs. {(last.max_eligible_loan or 0):,.2f}")
    
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "3. AI Diagnostic Analysis", ln=True)
    
    try:
        reasons = json.loads(last.reasons) if last.reasons else []
    except:
        reasons = []
        
    try:
        suggestions = json.loads(last.suggestions) if last.suggestions else []
    except:
        suggestions = []
        
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Primary Drivers (SHAP AI Explainer):", ln=True)
    pdf.set_font("helvetica", "", 10)
    if reasons:
        for r in reasons:
            pdf.set_x(10)
            pdf.multi_cell(0, 6, f"- {r}")
    else:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, "- No explicit triggers logged.")
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, "Official Actionable Advice:", ln=True)
    pdf.set_font("helvetica", "", 10)
    if suggestions:
        for s in suggestions:
            pdf.set_x(10)
            pdf.multi_cell(0, 6, f"- {s}")
    else:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, "- No structural suggestions found.")
        
    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=Loan_Profile_Record.pdf'
    return response


@app.route("/history")
@login_required
def history():
    user = current_user()
    apps = (
        LoanApplication.query.filter_by(user_id=user.id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )
    for a in apps:
        try:
            a.parsed_reasons = json.loads(a.reasons) if a.reasons else []
        except:
            a.parsed_reasons = []
        try:
            a.parsed_suggestions = json.loads(a.suggestions) if a.suggestions else []
        except:
            a.parsed_suggestions = []
            
    return render_template("history.html", user=user, apps=apps)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email is already registered. Please log in.", "warning")
            return redirect(url_for("login"))

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        flash("Account created. Welcome!", "success")
        return redirect(url_for("analyze"))

    return render_template("auth_register.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Logged in successfully.", "success")
            return redirect(url_for("analyze"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("auth_login.html", user=current_user())


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/predict", methods=["POST"])
@login_required
def predict():
    data = request.get_json() or request.form

    def to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    dependents = float(np.clip(to_float(data.get("dependents", 0)), 0, 10))
    education = data.get("education", "Graduate")
    self_employed = data.get("self_employed", "No")
    income = float(np.clip(to_float(data.get("income", 0)), 0, 12000000))
    loan_amount = float(np.clip(to_float(data.get("loan_amount", 0)), 0, 50000000))
    loan_term = float(np.clip(to_float(data.get("loan_term", 1)), 1, 40))
    cibil = float(np.clip(to_float(data.get("cibil", 750)), 300, 900))
    res_assets = float(np.clip(to_float(data.get("res_assets", 0)), 0, 100000000))
    com_assets = float(np.clip(to_float(data.get("com_assets", 0)), 0, 100000000))
    lux_assets = float(np.clip(to_float(data.get("lux_assets", 0)), 0, 100000000))
    bank_assets = float(np.clip(to_float(data.get("bank_assets", 0)), 0, 100000000))

    result = run_prediction(
        dependents,
        education,
        self_employed,
        income,
        loan_amount,
        loan_term,
        cibil,
        res_assets,
        com_assets,
        lux_assets,
        bank_assets,
    )

    user = current_user()
    if user:
        app_record = LoanApplication(
            user_id=user.id,
            dependents=int(dependents),
            education=education,
            self_employed=self_employed,
            income=income,
            loan_amount=loan_amount,
            loan_term=loan_term,
            cibil=cibil,
            res_assets=res_assets,
            com_assets=com_assets,
            lux_assets=lux_assets,
            bank_assets=bank_assets,
            loan_status=result["loan_status"],
            interest_rate=result["interest_rate"],
            emi=result["emi"],
            dti=result["dti"],
            lti=result["lti"],
            aai=result["aai"],
            max_eligible_loan=result["max_eligible_loan"],
            risk_category=result["risk_category"],
            loan_type=result["loan_type"],
            cibil_category=result["cibil_category"],
            reasons=json.dumps(result.get("main_reasons", [])),
            suggestions=json.dumps(result.get("advisory", []))
        )
        db.session.add(app_record)
        db.session.commit()

    return jsonify(result)


@app.route("/calc_cibil", methods=["POST"])
@login_required
def calc_cibil():
    data = request.get_json() or dict(request.form)
    result = calculate_cibil_insights(data)
    
    user = current_user()
    if user:
        def to_float(val, default=0.0):
            try:
                return float(val)
            except (TypeError, ValueError):
                return default
                
        report = CibilReport(
            user_id=user.id,
            age=to_float(data.get("age", 0)),
            employment=str(data.get("employment", "Salaried")),
            experience=to_float(data.get("experience", 0)),
            income=to_float(data.get("income", 0)),
            expenses=to_float(data.get("expenses", 0)),
            emi=to_float(data.get("emi", 0)),
            active_loans=to_float(data.get("active_loans", 0)),
            outstanding_loan=to_float(data.get("outstanding_loan", 0)),
            home_loans=to_float(data.get("home_loans", 0)),
            car_loans=to_float(data.get("car_loans", 0)),
            personal_loans=to_float(data.get("personal_loans", 0)),
            education_loans=to_float(data.get("education_loans", 0)),
            credit_cards=to_float(data.get("credit_cards", 0)),
            cc_limit=to_float(data.get("cc_limit", 0)),
            cc_used=to_float(data.get("cc_used", 0)),
            missed_payments=to_float(data.get("missed_payments", 0)),
            max_delay=str(data.get("max_delay", "0 Days")),
            default_history=str(data.get("default_history", "No")),
            settled_loans=str(data.get("settled_loans", "No")),
            history_years=to_float(data.get("history_years", 0)),
            closed_loans=to_float(data.get("closed_loans", 0)),
            inquiries=to_float(data.get("inquiries", 0)),
            cibil_score=result.get("cibil_score", 0),
            category=result.get("category", "")
        )
        db.session.add(report)
        db.session.commit()
        
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)

