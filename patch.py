import re

with open('templates/cibil.html', 'r', encoding='utf-8') as f:
    content = f.read()

mapping = {
    'age': 'age',
    'experience': 'experience',
    'income': 'income',
    'expenses': 'expenses',
    'emi': 'emi',
    'active_loans': 'active_loans',
    'outstanding_loan': 'outstanding_loan',
    'home_loans': 'home_loans',
    'car_loans': 'car_loans',
    'personal_loans': 'personal_loans',
    'education_loans': 'education_loans',
    'credit_cards': 'credit_cards',
    'cc_limit': 'cc_limit',
    'cc_used': 'cc_used',
    'history_years': 'history_years',
    'closed_loans': 'closed_loans',
    'inquiries': 'inquiries',
    'missed_payments': 'missed_payments'
}

for name, db_field in mapping.items():
    pattern = r'(name="'+name+r'".*?value=")([^"]+)(".*?>)'
    replacement = r'\g<1>{{ last_run.' + db_field + r'|int if last_run and last_run.' + db_field + r' is not none else \'\g<2>\' }}\g<3>'
    content = re.sub(pattern, replacement, content)

dropdowns = {
    'employment': ['Salaried', 'Self-employed', 'Student', 'Unemployed'],
    'max_delay': ['No Delay', '30 Days', '60 Days', '90+ Days'],
    'default_history': ['No', 'Yes'],
    'settled_loans': ['No', 'Yes']
}

for dd_name, options in dropdowns.items():
    for opt in options:
        pattern = r'(<option value="' + opt.replace("+", r"\+") + r'")>'
        replacement = r'\1 {% if last_run and last_run.' + dd_name + r' == \'' + opt + r'\' %}selected{% endif %}>'
        content = re.sub(pattern, replacement, content)

content = re.sub(r'<button\s*type="button"\s*id="generate-cibil"[\s\S]*?</button>', '', content)

with open('templates/cibil.html', 'w', encoding='utf-8') as f:
    f.write(content)
