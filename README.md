# Loan Eligibility Prediction App

A Flask web application for predicting loan eligibility using machine learning models.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

The app will be available at http://127.0.0.1:5001

## Features

- User registration and login
- Loan eligibility prediction
- Financial calculations (EMI, DTI, LTI, etc.)
- Analytics dashboard
- CIBIL score calculator
- Bank comparison for EMIs

## Dependencies

- Flask
- Flask-SQLAlchemy
- scikit-learn
- pandas
- numpy
- shap
- xgboost
- joblib