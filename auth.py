import re
from functools import wraps
from flask import render_template, request, redirect, url_for, session, flash
from models import db, User

EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("You must be logged in to view this page.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


def init_auth(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("All fields are required.", "danger")
                return redirect(url_for("register"))

            if not EMAIL_REGEX.match(email):
                flash("Invalid email format.", "danger")
                return redirect(url_for("register"))

            if len(password) < 6:
                flash("Password must be at least 6 characters long.", "danger")
                return redirect(url_for("register"))

            if User.query.filter_by(email=email).first():
                flash("Email is already registered. Please log in.", "warning")
                return redirect(url_for("login"))

            try:
                user = User(name=name, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                session["user_id"] = user.id
                flash("Account created. Welcome!", "success")
                return redirect(url_for("analyze"))
            except Exception:
                db.session.rollback()
                flash("An error occurred. Please try again.", "danger")
                return redirect(url_for("register"))

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
