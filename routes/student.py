from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from models import Student, PlacementDrive, Application, Company, User
from app import db
from datetime import datetime
from werkzeug.utils import secure_filename
import os

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    """Decorator to check if current user is Student"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Student':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # only show approved drives that havent passed their deadline
    available_drives = PlacementDrive.query.filter(
        PlacementDrive.status == 'approved',
        PlacementDrive.deadline >= datetime.now()
    ).all()
    
    my_applications = Application.query.filter_by(student_id=student.id).all() if student else []
    applied_drive_ids = [app.drive_id for app in my_applications]

    return render_template('student/dashboard.html', 
                           student=student, 
                           available_drives=available_drives, 
                           my_applications=my_applications,
                           applied_drive_ids=applied_drive_ids)


@student_bp.route('/apply/<int:drive_id>', methods=['POST'])
@login_required
@student_required
def apply(drive_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    # check drive is actually approved and open
    if drive.status != 'approved':
        flash('This drive is not actively accepting applications.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # check if deadline has passed
    if drive.deadline < datetime.now():
        flash('The deadline for this drive has passed.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # prevent duplicate applications
    existing_app = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing_app:
        flash('You have already applied to this drive!', 'warning')
        return redirect(url_for('student.dashboard'))
        
    new_app = Application(student_id=student.id, drive_id=drive.id, status='Applied')
    db.session.add(new_app)
    db.session.commit()
    
    flash('Successfully applied to ' + drive.job_title + '!', 'success')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@student_required
def edit_profile():
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        student.name = request.form.get('name', student.name)
        student.phone = request.form.get('phone')
        student.branch = request.form.get('branch')
        
        cgpa_str = request.form.get('cgpa')
        if cgpa_str:
            try:
                cgpa = float(cgpa_str)
                if 0 <= cgpa <= 10:
                    student.cgpa = cgpa
                else:
                    flash('CGPA must be between 0 and 10.', 'danger')
                    return redirect(url_for('student.edit_profile'))
            except ValueError:
                flash('CGPA must be a valid number.', 'danger')
                return redirect(url_for('student.edit_profile'))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/edit_profile.html', student=student)


@student_bp.route('/history')
@login_required
@student_required
def history():
    """View past placement history - all applications and their outcomes"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # get all applications with drive and company info
    applications = db.session.query(Application, PlacementDrive, Company).join(
        PlacementDrive, Application.drive_id == PlacementDrive.id
    ).join(
        Company, PlacementDrive.company_id == Company.id
    ).filter(
        Application.student_id == student.id
    ).order_by(Application.applied_at.desc()).all()
    
    return render_template('student/history.html', student=student, applications=applications)


@student_bp.route('/upload-resume', methods=['POST'])
@login_required
@student_required
def upload_resume():
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if 'resume' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    file = request.files['resume']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    if not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    filename = secure_filename(f"{student.enrollment_no}_{file.filename}")
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    student.resume_path = url_for('static', filename='uploads/' + filename)
    db.session.commit()
    
    flash('Resume uploaded successfully!', 'success')
    return redirect(url_for('student.dashboard'))


@student_bp.route('/drive/<int:drive_id>')
@login_required
@student_required
def drive_detail(drive_id):
    """View full details of a placement drive before applying"""
    student = Student.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    company = Company.query.get_or_404(drive.company_id)
    
    # check if student already applied
    existing_app = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    has_applied = existing_app is not None
    
    # check if deadline passed
    deadline_passed = drive.deadline < datetime.now()
    
    return render_template('student/drive_detail.html', 
                           student=student, drive=drive, company=company,
                           has_applied=has_applied, deadline_passed=deadline_passed)

