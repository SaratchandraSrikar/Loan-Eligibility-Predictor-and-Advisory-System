from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

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
