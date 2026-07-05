import os
import logging
import joblib
import pandas as pd
import numpy as np
import shap
from financial_engine import (
    calculate_interest,
    calculate_emi,
    calculate_dti,
    max_loan,
    calculate_lti,
    total_assets,
    calculate_aai,
    risk_category,
    cibil_category,
    loan_type_recommendation,
    multi_bank_emi_comparison,
)

logger = logging.getLogger("flask.app")

# Constants
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

# Load saved ML pipeline
BASE_DIR = os.path.dirname(__file__)
PIPELINE_PATH = os.path.join(BASE_DIR, "loan_model_pipeline.pkl")

try:
    pipeline = joblib.load(PIPELINE_PATH)
    # Extract components for SHAP explainer
    encoder = pipeline.named_steps['encoder']
    scaler = pipeline.named_steps['scaler']
    classifier = pipeline.named_steps['classifier']
    rf_model = classifier.named_estimators_['rf']
    # TreeExplainer on RandomForest works cleanly and is robust
    explainer = shap.TreeExplainer(rf_model)
except Exception as e:
    logger.exception("Failed to initialize ML pipeline or SHAP explainer")
    pipeline = None
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
    if pipeline is None:
        raise RuntimeError("ML model pipeline is not loaded.")

    # Create DataFrame matching training columns
    X = pd.DataFrame(
        [
            [
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
            ]
        ],
        columns=FEATURE_COLUMNS,
    )

    # Perform prediction
    prediction = pipeline.predict(X)[0]
    # Model target: 0 = Approved, 1 = Rejected
    loan_status_model = "Yes" if prediction == 0 else "No"

    # Preprocess values for SHAP and intermediate stats
    try:
        X_encoded = encoder.transform(X)
        X_scaled = scaler.transform(X_encoded)
    except Exception:
        logger.exception("Failed preprocessing for SHAP values calculation")
        X_scaled = None

    # Core Financial Calculations
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

    # Business Rule Guardrails for Demo UI
    advisory = []
    loan_status = loan_status_model
    if income <= 0 or loan_amount <= 0 or loan_term <= 0:
        loan_status = "No"
        advisory.append("Missing/invalid income, loan amount, or tenure can make a loan ineligible.")
    else:
        if maxloan > 0 and loan_amount > (maxloan * 1.05):
            loan_status = "No"
            advisory.append("Requested loan amount is above your calculated safe eligibility ceiling.")
        if dti > 0.6:
            loan_status = "No"
            advisory.append("DTI is extremely high; most lenders reject at this burden level.")
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

    # SHAP explanations (Top 3 drivers)
    main_reasons = []
    feature_importance = None

    if explainer is not None and X_scaled is not None:
        try:
            # shap_values shape for RandomForest is (samples, features, classes)
            shap_vals_all_classes = explainer.shap_values(X_scaled)
            # Use class 0 (Approved) SHAP values if approved, else class 1 (Rejected)
            class_idx = 0 if loan_status == "Yes" else 1
            
            # Failsafe if shape differs
            if isinstance(shap_vals_all_classes, list):
                # Older SHAP versions return list of arrays per class
                values = shap_vals_all_classes[class_idx][0]
            elif len(shap_vals_all_classes.shape) == 3:
                # Shape (1, 11, 2)
                values = shap_vals_all_classes[0, :, class_idx]
            else:
                # Fallback if 2D array
                values = shap_vals_all_classes[0]
                
            feature_importance = list(zip(FEATURE_COLUMNS, values))
        except Exception:
            logger.exception("SHAP values calculation failed")

    # If SHAP fails or is missing, use simple feature direction as fallback
    if feature_importance is None:
        # Dummy direction based on scaled value offsets from 0
        if X_scaled is not None:
            feature_importance = [(col, X_scaled[0][i]) for i, col in enumerate(FEATURE_COLUMNS)]
        else:
            # Simplest fallback
            feature_importance = [(col, 1.0 if col == "cibil_score" else -1.0) for col in FEATURE_COLUMNS]

    # Rank features contextually
    if loan_status == "Yes":
        # For Class 0 (Approved), positive SHAP values drive Approval.
        # If using fallback scaled values, CIBIL and assets are positive (good), loan_amount is negative (bad).
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        for feature, val in feature_importance[:3]:
            # Map column names to readable strings
            readable_feature = feature.replace("_", " ").title()
            if val > 0:
                main_reasons.append(f"Strong {readable_feature} was a key driver securing your APPROVAL.")
            else:
                main_reasons.append(f"Despite {readable_feature} acting as a minor risk factor, your profile was still strong enough to pass.")
    else:
        # For Class 1 (Rejected), positive SHAP values drive Rejection.
        # If using fallback scaled values, high loan_amount/DTI are positive, high CIBIL is negative.
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        for feature, val in feature_importance[:3]:
            readable_feature = feature.replace("_", " ").title()
            if val > 0:
                main_reasons.append(f"{readable_feature} was a major critical reason for REJECTION.")
            else:
                main_reasons.append(f"{readable_feature} was strong, but not enough to outweigh the risks and secure approval.")

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
