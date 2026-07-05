import numpy as np

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
    cibil_component = np.clip((cibil - 300) / 600 * 60, 0, 60)

    # DTI component
    if dti <= 0.3:
        dti_component = 20
    elif dti <= 0.4:
        dti_component = 14
    elif dti <= 0.5:
        dti_component = 8
    else:
        dti_component = 3

    # LTI component
    if lti <= 2:
        lti_component = 10
    elif lti <= 4:
        lti_component = 6
    elif lti <= 6:
        lti_component = 3
    else:
        lti_component = 1

    # Asset buffer
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
    if loan_amount >= income_annum * 3 or res_assets > 0.5 * loan_amount:
        return "Home Loan"

    if income_annum * 0.8 <= loan_amount <= income_annum * 2.5 and lux_assets > 0:
        return "Car Loan"

    if income_annum < loan_amount * 1.5 and education == "Graduate" and cibil >= 650:
        return "Education Loan"

    return "Personal Loan"


def multi_bank_emi_comparison(loan_amount: float, term_years: float, loan_type: str, cibil: float, dti: float, ai_rate: float):
    """
    Compare EMI across mock bank profiles using dynamic rates based on loan_type and CIBIL,
    along with Approval Probability based on DTI and CIBIL criteria.
    Note: These are mock simulations for educational purposes, not real-time values.
    """
    bank_profiles = {
        "HDFC Bank (Simulated)": {"Home Loan": 8.5, "Car Loan": 8.75, "Personal Loan": 10.5, "Education Loan": 9.5, "nbfc": False},
        "SBI (Simulated)": {"Home Loan": 8.4, "Car Loan": 8.65, "Personal Loan": 11.0, "Education Loan": 8.5, "nbfc": False},
        "ICICI Bank (Simulated)": {"Home Loan": 8.75, "Car Loan": 8.9, "Personal Loan": 10.75, "Education Loan": 9.5, "nbfc": False},
        "Bajaj Finserv (Simulated)": {"Home Loan": 9.0, "Car Loan": 10.0, "Personal Loan": 12.0, "Education Loan": 10.5, "nbfc": True},
    }
    
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
        
        prob = "Low"
        is_nbfc = profile["nbfc"]
        
        if not is_nbfc:
            if cibil >= 750 and dti <= 0.4:
                prob = "High"
            elif cibil >= 700 and dti <= 0.5:
                prob = "Medium"
        else:
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
            "is_user_profile": False
        })
        
    ai_emi = calculate_emi(loan_amount, ai_rate, term_years)
    comparison.append({
        "bank": "Your Profile (Simulated AI Fit)",
        "rate": round(ai_rate, 2),
        "emi": round(ai_emi, 2),
        "prob": "Current Fit",
        "is_user_profile": True
    })
    
    comparison.sort(key=lambda x: x["emi"])
    return comparison
