import numpy as np

def calculate_cibil_insights(data: dict) -> dict:
    """
    Computes an Estimated CIBIL-like score based on detailed behavioral and financial inputs.
    This is an educational simulation, not an official credit bureau score.
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

    factors = []
    tips = []

    # Repayment History (35%)
    repayment_norm = 1.0
    if missed_payments > 0:
        penalty = min(0.5, missed_payments * 0.1)
        repayment_norm -= penalty
        factors.append(f"Missed {missed_payments} payment(s) negatively impacts credit vintage.")
        tips.append("Always pay EMIs and card dues on or before the due date.")

    if max_delay == "30 Days":
        repayment_norm -= 0.15
        factors.append("A recent 30-day payment delay was noted.")
    elif max_delay == "60 Days":
        repayment_norm -= 0.3
        factors.append("A 60-day delay in payments shows moderate repayment risk.")
        tips.append("Clear all overdue accounts immediately to stop further score damage.")
    elif max_delay == "90+ Days":
        repayment_norm -= 0.5
        factors.append("A 90+ day delay severely damages credit score standing.")
        tips.append("Contact your lender to restructure or clear 90+ day overdues.")

    if settled_loans == "Yes":
        repayment_norm -= 0.3
        factors.append("'Settled' loans remain on report and reduce score.")
        tips.append("Try to fully pay off and 'Close' accounts rather than settling them.")

    if default_history == "Yes":
        repayment_norm = 0.0
        factors.append("A previous default is dragging down your credit standing.")
        tips.append("Rebuild credit by obtaining a secured credit card and making timely payments.")

    repayment_norm = max(0.0, repayment_norm)
    if repayment_norm == 1.0:
        factors.append("Flawless repayment history is strongly boosting your rating.")

    # Credit Utilization (25%)
    cc_limit_total = max(cc_limit, 1.0)
    utilization_ratio = cc_used / cc_limit_total if credit_cards > 0 else 0.0
    
    if credit_cards == 0:
        util_norm = 0.5
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

    high_util_penalty = 1.0
    if utilization_ratio > 0.7:
        high_util_penalty = 0.9

    # Credit History Length (15%)
    history_norm = min(1.0, history_years / 10.0) 
    if history_years > 7:
        factors.append(f"Long credit history vintage ({int(history_years)} years) adds stability.")
    elif history_years < 2:
        factors.append("Your credit history is quite new, which limits your maximum score.")
        tips.append("Maintain older credit card accounts to increase average credit age.")

    # Credit Mix (10%)
    secured_count = home_loans + car_loans
    unsecured_count = personal_loans + education_loans + active_loans - (home_loans + car_loans)
    unsecured_count = max(0, unsecured_count)

    mix_norm = 0.5
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
    inquiry_norm = 1.0
    if inquiries == 0:
        inquiry_norm = 1.0
    elif inquiries <= 2:
        inquiry_norm = 0.9
    elif inquiries <= 5:
        inquiry_norm = 0.5
        factors.append(f"{inquiries} recent inquiries indicate active credit-seeking behavior.")
    else:
        inquiry_norm = 0.0
        factors.append(f"Excessive recent inquiries ({inquiries}) are dragging down your score.")
        tips.append("Stop applying for new credit cards or loans for the next 6 months.")

    too_many_inquiries_penalty = 1.0
    if inquiries > 5:
        too_many_inquiries_penalty = 0.9

    # Income Stability (5%)
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

    # Final Score Calculation
    weighted_norm = (
        repayment_norm * 0.35 +
        util_norm * 0.25 +
        history_norm * 0.15 +
        mix_norm * 0.10 +
        inquiry_norm * 0.10 +
        income_norm * 0.05
    )

    if default_history == "Yes":
        weighted_norm *= 0.7
    
    weighted_norm *= high_util_penalty
    weighted_norm *= too_many_inquiries_penalty

    # Formula: Score = 300 + (Normalized Score x 600)
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

    if not tips and final_score < 800:
        tips.append("Keep credit card usage low and pay EMIs on time to reach excellent tiers.")
    elif not tips:
        tips.append("Keep doing exactly what you're doing. Your profile is exceptionally strong.")

    return {
        "cibil_score": round(final_score, 0),
        "category": category,
        "factors": factors[:4],
        "tips": tips[:4]
    }
