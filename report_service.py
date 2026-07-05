import json
from flask import redirect, url_for, flash, make_response
from fpdf import FPDF
from models import LoanApplication
from auth import current_user, login_required

def init_report(app):
    @app.route("/api/export-report/latest")
    @login_required
    def export_latest_report():
        user = current_user()
        last = LoanApplication.query.filter_by(user_id=user.id).order_by(LoanApplication.created_at.desc()).first()
        
        if not last:
            flash("No simulation found to export.", "warning")
            return redirect(url_for("analyze"))

        class PDF(FPDF):
            def header(self):
                # Background Header
                self.set_fill_color(37, 99, 235)  # blue-600
                self.rect(0, 0, 210, 30, 'F')
                self.set_y(10)
                self.set_font("helvetica", "B", 16)
                self.set_text_color(255, 255, 255)
                self.cell(0, 10, "Loan Advisory Simulation Report", align="C")
                self.ln(10)
                self.set_font("helvetica", "", 10)
                self.set_text_color(240, 240, 240)
                self.cell(0, 4, f"Generated for: {user.name.title()} ({user.email})", align="C")
                self.ln(20)
                
            def footer(self):
                self.set_y(-15)
                self.set_font("helvetica", "I", 8)
                self.set_text_color(150, 150, 150)
                self.cell(0, 10, f"Page {self.page_no()} | Simulation Report (Non-Official)", align="C")

        pdf = PDF()
        pdf.add_page()
        
        pdf.set_y(40)
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "1. Eligibility Simulation Output", ln=True)
        
        pdf.set_font("helvetica", "", 12)
        pdf.set_fill_color(240, 248, 255)
        pdf.cell(50, 10, "Eligibility Status:", border=1, fill=True)
        
        if last.loan_status == "Yes":
            pdf.set_text_color(22, 163, 74)  # green
            status_text = "APPROVED (Eligible)"
        else:
            pdf.set_text_color(220, 38, 38)  # red
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
        pdf.cell(0, 10, "2. Simulated Financial Calculations", ln=True)
        
        pdf.set_font("helvetica", "", 11)
        
        def add_row(key, val):
            pdf.cell(70, 8, key, border=1)
            pdf.cell(120, 8, str(val), border=1, ln=True)
            
        add_row("Principal Requested", f"Rs. {last.loan_amount:,.2f}")
        add_row("Income (Annual)", f"Rs. {last.income:,.2f}")
        add_row("Estimated CIBIL-like Score", f"{last.cibil}")
        add_row("Estimated Interest Rate", f"{(last.interest_rate or 0)}%")
        add_row("Projected EMI", f"Rs. {(last.emi or 0):,.2f}")
        add_row("Debt-to-Income (DTI)", f"{(last.dti or 0)*100:.1f}%")
        add_row("Max Eligible Principal Ceiling", f"Rs. {(last.max_eligible_loan or 0):,.2f}")
        
        pdf.ln(10)
        
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "3. AI Diagnostic Analysis (Simulation)", ln=True)
        
        try:
            reasons = json.loads(last.reasons) if last.reasons else []
        except Exception:
            reasons = []
            
        try:
            suggestions = json.loads(last.suggestions) if last.suggestions else []
        except Exception:
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
        pdf.cell(0, 8, "Simulated Actionable Advice:", ln=True)
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
        response.headers['Content-Disposition'] = 'attachment; filename=Loan_Simulation_Report.pdf'
        return response
