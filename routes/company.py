from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import User, Company, PlacementDrive, Application, Student
from app import db
from datetime import datetime

company_bp = Blueprint('company', __name__, url_prefix='/company')


def company_required(f):
    """Decorator to check if current user is Company"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Company':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@company_bp.route('/dashboard')
@login_required
@company_required
def dashboard():
    company = Company.query.filter_by(user_id=current_user.id).first()
    drives = PlacementDrive.query.filter_by(company_id=company.id).all() if company else []
    
    # count applicants for each drive so we can show it on dashboard
    drive_applicant_counts = {}
    total_applicants = 0
    for drive in drives:
        count = Application.query.filter_by(drive_id=drive.id).count()
        drive_applicant_counts[drive.id] = count
        total_applicants += count

    # summary stats for the dashboard header
    drive_ids = [d.id for d in drives]
    stats = {
        'total_drives': len(drives),
        'active_drives': sum(1 for d in drives if d.status == 'approved'),
        'total_applicants': total_applicants,
        'shortlisted': Application.query.filter(
            Application.drive_id.in_(drive_ids), Application.status == 'Shortlisted'
        ).count() if drive_ids else 0,
        'selected': Application.query.filter(
            Application.drive_id.in_(drive_ids), Application.status == 'Selected'
        ).count() if drive_ids else 0,
        'pending_drives': sum(1 for d in drives if d.status == 'pending'),
    }

    return render_template('company/dashboard.html', company=company, drives=drives,
                           drive_applicant_counts=drive_applicant_counts, stats=stats)


@company_bp.route('/create-drive', methods=['POST'])
@login_required
@company_required
def create_drive():
    company = Company.query.filter_by(user_id=current_user.id).first()
    if not company or company.approval_status != 'approved':
        flash("You cannot post drives until Admin approves your account.", "danger")
        return redirect(url_for('company.dashboard'))
    
    job_title = request.form.get('job_title')
    description = request.form.get('description')
    eligibility = request.form.get('eligibility')
    deadline_str = request.form.get('deadline')
    salary_package = request.form.get('salary_package')
    location = request.form.get('location')
    job_type = request.form.get('job_type', 'Full-Time')

    # backend validation
    if not job_title or not description or not eligibility or not deadline_str:
        flash("All required fields must be filled.", "danger")
        return redirect(url_for('company.dashboard'))
    
    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        if deadline <= datetime.now():
            flash("Deadline must be a future date.", "danger")
            return redirect(url_for('company.dashboard'))
        new_drive = PlacementDrive(
            company_id=company.id,
            job_title=job_title,
            description=description,
            eligibility=eligibility,
            deadline=deadline,
            salary_package=salary_package,
            location=location,
            job_type=job_type,
            status='pending' 
        )
        db.session.add(new_drive)
        db.session.commit()
        flash("Placement Drive submitted to Admin for approval!", "success")
    except ValueError:
        flash("Error: Date must be valid. Please ensure you picked a deadline.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"An unexpected error occurred: {str(e)}", "danger")
    return redirect(url_for('company.dashboard'))


@company_bp.route('/edit-drive/<int:drive_id>', methods=['GET', 'POST'])
@login_required
@company_required
def edit_drive(drive_id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != company.id:
        flash("You do not own this drive.", "danger")
        return redirect(url_for('company.dashboard'))
    
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title', drive.job_title)
        drive.description = request.form.get('description', drive.description)
        drive.eligibility = request.form.get('eligibility', drive.eligibility)
        drive.salary_package = request.form.get('salary_package')
        drive.location = request.form.get('location')
        drive.job_type = request.form.get('job_type', 'Full-Time')
        
        deadline_str = request.form.get('deadline')
        if deadline_str:
            try:
                drive.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid date format.", "danger")
                return redirect(url_for('company.edit_drive', drive_id=drive.id))
        
        db.session.commit()
        flash("Drive updated successfully!", "success")
        return redirect(url_for('company.dashboard'))
    
    return render_template('company/edit_drive.html', drive=drive, company=company)


@company_bp.route('/delete-drive/<int:drive_id>', methods=['POST'])
@login_required
@company_required
def delete_drive(drive_id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != company.id:
        flash("You do not own this drive.", "danger")
        return redirect(url_for('company.dashboard'))
    
    # delete all applications for this drive first
    Application.query.filter_by(drive_id=drive.id).delete()
    db.session.delete(drive)
    db.session.commit()
    flash("Drive deleted successfully.", "success")
    return redirect(url_for('company.dashboard'))


@company_bp.route('/close-drive/<int:drive_id>', methods=['POST'])
@login_required
@company_required
def close_drive(drive_id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != company.id:
        flash("You do not own this drive.", "danger")
        return redirect(url_for('company.dashboard'))
    
    drive.status = 'closed'
    db.session.commit()
    flash("Drive has been closed. Students can no longer apply.", "success")
    return redirect(url_for('company.dashboard'))


@company_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@company_required
def edit_profile():
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        company.company_name = request.form.get('company_name', company.company_name)
        company.hr_contact = request.form.get('hr_contact', company.hr_contact)
        company.website = request.form.get('website')
        company.industry = request.form.get('industry')
        company.description = request.form.get('description')
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('company.dashboard'))
    
    return render_template('company/edit_profile.html', company=company)


@company_bp.route('/view-applications/<int:drive_id>')
@login_required
@company_required
def view_applications(drive_id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.company_id != company.id:
        flash("You do not own this drive.", "danger")
        return redirect(url_for('company.dashboard'))
    
    # optional status filter
    status_filter = request.args.get('status', 'all')
    
    query = db.session.query(Application, Student, User).join(
        Student, Application.student_id == Student.id
    ).join(
        User, Student.user_id == User.id
    ).filter(Application.drive_id == drive.id)
    
    if status_filter != 'all':
        query = query.filter(Application.status == status_filter)
    
    results = query.order_by(Application.applied_at.desc()).all()
    
    # counts for the filter badges
    app_counts = {
        'all': Application.query.filter_by(drive_id=drive.id).count(),
        'Applied': Application.query.filter_by(drive_id=drive.id, status='Applied').count(),
        'Shortlisted': Application.query.filter_by(drive_id=drive.id, status='Shortlisted').count(),
        'Selected': Application.query.filter_by(drive_id=drive.id, status='Selected').count(),
        'Rejected': Application.query.filter_by(drive_id=drive.id, status='Rejected').count(),
    }
    
    return render_template('company/applications.html', drive=drive, results=results,
                           status_filter=status_filter, app_counts=app_counts)


@company_bp.route('/application/<int:app_id>/status/<string:status>', methods=['POST'])
@login_required
@company_required
def update_status(app_id, status):
    application = Application.query.get_or_404(app_id)
    drive = PlacementDrive.query.get(application.drive_id)
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    if drive.company_id != company.id:
        flash("You do not own this drive.", "danger")
        return redirect(url_for('company.dashboard'))
    
    if status in ['Shortlisted', 'Selected', 'Rejected']:
        application.status = status
        db.session.commit()
        flash(f"Application status updated to {status}!", "success")
    else:
        flash("Invalid status.", "danger")
            
    return redirect(url_for('company.view_applications', drive_id=drive.id))

