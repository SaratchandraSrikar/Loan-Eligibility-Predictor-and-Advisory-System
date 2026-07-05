import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, User, LoanApplication
from auth import init_auth, current_user, login_required
from report_service import init_report
from ml_service import run_prediction
from cibil_service import calculate_cibil_insights
from analytics_service import build_analytics_payload

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flask.app")

app = Flask(__name__)

# Security: Secret Key from Environment
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-default-secret-key")

# Security: Session Cookie Configurations
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Secure cookie only in production (HTTPS)
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("ENV") == "production"

# Database Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "loan_app.db")

db_url = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

with app.app_context():
    db.create_all()

# Register View/Auth Routes directly
init_auth(app)
init_report(app)


# =====================================================
# VIEW ROUTES
# =====================================================

@app.route("/")
def home():
    return render_template("home.html", user=current_user())


@app.route("/analyze")
@login_required
def analyze():
    return render_template("index.html", user=current_user())


@app.route("/about")
def about():
    return render_template("about.html", user=current_user())


@app.route("/cibil")
@login_required
def cibil_page():
    user = current_user()
    from models import CibilReport
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
    if not apps:
        flash("Please complete at least one loan prediction run to view analytics.", "info")
        return redirect(url_for("analyze"))
        
    analytics_payload = build_analytics_payload(apps)
    return render_template("analytics.html", user=user, analytics=analytics_payload)


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
        except Exception:
            a.parsed_reasons = []
        try:
            a.parsed_suggestions = json.loads(a.suggestions) if a.suggestions else []
        except Exception:
            a.parsed_suggestions = []
            
    return render_template("history.html", user=user, apps=apps)


# =====================================================
# API / CALCULATION ENDPOINTS
# =====================================================

def parse_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@app.route("/predict", methods=["POST"])
@login_required
def predict():
    data = request.get_json() or request.form

    # Explicit input validations
    dependents = parse_float(data.get("dependents"))
    if dependents is None or dependents < 0 or dependents > 10:
        return jsonify({"error": "Dependents must be a positive integer between 0 and 10."}), 400

    education = data.get("education")
    if education not in ["Graduate", "Not Graduate"]:
        return jsonify({"error": "Education must be 'Graduate' or 'Not Graduate'."}), 400

    self_employed = data.get("self_employed")
    if self_employed not in ["Yes", "No"]:
        return jsonify({"error": "Self-employed status must be 'Yes' or 'No'."}), 400

    income = parse_float(data.get("income"))
    if income is None or income <= 0 or income > 12000000:
        return jsonify({"error": "Annual income must be a positive number up to 12,000,000."}), 400

    loan_amount = parse_float(data.get("loan_amount"))
    if loan_amount is None or loan_amount <= 0 or loan_amount > 50000000:
        return jsonify({"error": "Loan amount must be a positive number up to 50,000,000."}), 400

    loan_term = parse_float(data.get("loan_term"))
    if loan_term is None or loan_term < 1 or loan_term > 40:
        return jsonify({"error": "Loan tenure must be between 1 and 40 years."}), 400

    cibil = parse_float(data.get("cibil"))
    if cibil is None or cibil < 300 or cibil > 900:
        return jsonify({"error": "CIBIL score must be between 300 and 900."}), 400

    res_assets = parse_float(data.get("res_assets", 0))
    if res_assets is None or res_assets < 0 or res_assets > 100000000:
        return jsonify({"error": "Residential assets value must be a non-negative number."}), 400

    com_assets = parse_float(data.get("com_assets", 0))
    if com_assets is None or com_assets < 0 or com_assets > 100000000:
        return jsonify({"error": "Commercial assets value must be a non-negative number."}), 400

    lux_assets = parse_float(data.get("lux_assets", 0))
    if lux_assets is None or lux_assets < 0 or lux_assets > 100000000:
        return jsonify({"error": "Luxury assets value must be a non-negative number."}), 400

    bank_assets = parse_float(data.get("bank_assets", 0))
    if bank_assets is None or bank_assets < 0 or bank_assets > 100000000:
        return jsonify({"error": "Bank assets value must be a non-negative number."}), 400

    # Run pipeline prediction and explanations
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

    # Validate inputs
    age = parse_float(data.get("age"))
    if age is None or age < 18 or age > 100:
        return jsonify({"error": "Age must be between 18 and 100."}), 400

    employment = data.get("employment")
    if employment not in ["Salaried", "Self-employed", "Student", "Unemployed"]:
        return jsonify({"error": "Invalid employment type."}), 400

    experience = parse_float(data.get("experience"))
    if experience is None or experience < 0 or experience > age:
        return jsonify({"error": "Experience must be non-negative and less than age."}), 400

    income = parse_float(data.get("income"))
    if income is None or income <= 0:
        return jsonify({"error": "Income must be greater than zero."}), 400

    expenses = parse_float(data.get("expenses"))
    if expenses is None or expenses < 0:
        return jsonify({"error": "Expenses must be a non-negative number."}), 400

    emi = parse_float(data.get("emi"))
    if emi is None or emi < 0:
        return jsonify({"error": "EMI must be a non-negative number."}), 400

    # Calculate insights
    result = calculate_cibil_insights(data)
    
    user = current_user()
    if user:
        from models import CibilReport
        report = CibilReport(
            user_id=user.id,
            age=age,
            employment=employment,
            experience=experience,
            income=income,
            expenses=expenses,
            emi=emi,
            active_loans=parse_float(data.get("active_loans", 0)),
            outstanding_loan=parse_float(data.get("outstanding_loan", 0)),
            home_loans=parse_float(data.get("home_loans", 0)),
            car_loans=parse_float(data.get("car_loans", 0)),
            personal_loans=parse_float(data.get("personal_loans", 0)),
            education_loans=parse_float(data.get("education_loans", 0)),
            credit_cards=parse_float(data.get("credit_cards", 0)),
            cc_limit=parse_float(data.get("cc_limit", 0)),
            cc_used=parse_float(data.get("cc_used", 0)),
            missed_payments=parse_float(data.get("missed_payments", 0)),
            max_delay=str(data.get("max_delay", "No Delay")),
            default_history=str(data.get("default_history", "No")),
            settled_loans=str(data.get("settled_loans", "No")),
            history_years=parse_float(data.get("history_years", 0)),
            closed_loans=parse_float(data.get("closed_loans", 0)),
            inquiries=parse_float(data.get("inquiries", 0)),
            cibil_score=result.get("cibil_score", 0),
            category=result.get("category", "")
        )
        db.session.add(report)
        db.session.commit()
        
    return jsonify(result)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
