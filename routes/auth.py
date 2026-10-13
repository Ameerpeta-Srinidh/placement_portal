from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import User, Student, Company
from app import db
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('Your account has been deactivated by the Admin.', 'danger')
                return redirect(url_for('auth.login'))
            if user.role == 'Company':
                company = Company.query.filter_by(user_id=user.id).first()
                if company and company.approval_status == 'pending':
                    flash('Your company registration is pending admin approval. Please wait.', 'warning')
                    return redirect(url_for('auth.login'))
                elif company and company.approval_status == 'rejected':
                    flash('Your company registration has been rejected by the admin.', 'danger')
                    return redirect(url_for('auth.login'))
            
            login_user(user)
            if user.role == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'Student':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'Company':
                return redirect(url_for('company.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not email or not password or not role:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.register'))

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.register'))
        
        if role not in ['Student', 'Company']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('auth.register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered! Try logging in.', 'danger')
            return redirect(url_for('auth.register'))
            
        if role == "Student":
            name = request.form.get('name')
            enrollment_no = request.form.get('enrollment_no')
            phone = request.form.get('phone')
            branch = request.form.get('branch')
            cgpa_str = request.form.get('cgpa')

            if not name or not enrollment_no:
                flash('Name and Enrollment Number are required for students.', 'danger')
                return redirect(url_for('auth.register'))
            
            existing_student = Student.query.filter_by(enrollment_no=enrollment_no).first()
            if existing_student:
                flash('This enrollment number is already registered.', 'danger')
                return redirect(url_for('auth.register'))
            
            cgpa = None
            if cgpa_str:
                try:
                    cgpa = float(cgpa_str)
                    if cgpa < 0 or cgpa > 10:
                        flash('CGPA must be between 0 and 10.', 'danger')
                        return redirect(url_for('auth.register'))
                except ValueError:
                    flash('CGPA must be a valid number.', 'danger')
                    return redirect(url_for('auth.register'))
            
            new_user = User(email=email, password=generate_password_hash(password), role=role)
            db.session.add(new_user)
            db.session.commit()
            
            new_student = Student(
                user_id=new_user.id, name=name, enrollment_no=enrollment_no,
                phone=phone, branch=branch, cgpa=cgpa
            )
            db.session.add(new_student)
            db.session.commit()
            
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('auth.login'))
            
        elif role == "Company":
            company_name = request.form.get('company_name')
            hr_contact = request.form.get('hr_contact')
            website = request.form.get('website')
            industry = request.form.get('industry')
            description = request.form.get('description')

            if not company_name or not hr_contact:
                flash('Company Name and HR Contact are required.', 'danger')
                return redirect(url_for('auth.register'))
            
            new_user = User(email=email, password=generate_password_hash(password), role=role)
            db.session.add(new_user)
            db.session.commit()
            
            new_company = Company(
                user_id=new_user.id, company_name=company_name, hr_contact=hr_contact,
                website=website, industry=industry, description=description
            )
            db.session.add(new_company)
            db.session.commit()
            
            flash('Registration successful! Please wait for Admin approval before logging in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))