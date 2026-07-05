import math

def build_analytics_payload(apps):
    """
    Builds the structured analytics and trends payload from a list of user loan simulations.
    """
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
    cibil_change = 0
    aai_change = 0
    cibil_dir = "flat"
    aai_dir = "flat"
    risk_trend = "Not enough data"

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

    # Affordability Engine
    affordability = {}
    if apps:
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
                # Formula: P_max = EMI_safe * (((1+r)**n - 1) / (r * (1+r)**n))
                try:
                    max_p = safe_emi * (((1+r)**n - 1) / (r * (1+r)**n))
                    reduce_by = P - max_p
                    if reduce_by > 0:
                        adjustments.append(f"Reduce loan by ₹{(reduce_by / 100000):.1f}L to stay within safe EMI.")
                except Exception:
                    pass
            
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
                            adjustments.append(f"Increase tenure by {years_to_add} years to reduce EMI safely.")
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

    return {
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
