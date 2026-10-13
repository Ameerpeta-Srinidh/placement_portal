from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import User, Student, Company, PlacementDrive, Application
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to check if current user is Admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # gather all the stats for the dashboard cards
    stats = {
        'total_students': Student.query.count(),
        'total_companies': Company.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'total_applications': Application.query.count(),
        'approved_companies': Company.query.filter_by(approval_status='approved').count(),
        'pending_companies': Company.query.filter_by(approval_status='pending').count(),
        'approved_drives': PlacementDrive.query.filter_by(status='approved').count(),
        'pending_drives': PlacementDrive.query.filter_by(status='pending').count(),
        'selected_students': Application.query.filter_by(status='Selected').count(),
    }

    pending_companies = Company.query.filter_by(approval_status='pending').all()
    pending_drives = PlacementDrive.query.filter_by(status='pending').all()
    
    # get recent applications for the activity feed
    recent_applications = db.session.query(Application, Student, PlacementDrive).join(
        Student, Application.student_id == Student.id
    ).join(
        PlacementDrive, Application.drive_id == PlacementDrive.id
    ).order_by(Application.applied_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, 
                           pending_companies=pending_companies, 
                           pending_drives=pending_drives,
                           recent_applications=recent_applications)


@admin_bp.route('/approve-company/<int:company_id>/<action>')
@login_required
@admin_required
def approve_company(company_id, action):
    company = Company.query.get_or_404(company_id)
    if action == 'approve':
        company.approval_status = 'approved'
        flash(f'Company "{company.company_name}" has been approved.', 'success')
    elif action == 'reject':
        company.approval_status = 'rejected'
        flash(f'Company "{company.company_name}" has been rejected.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/approve-drive/<int:drive_id>/<action>')
@login_required
@admin_required
def approve_drive(drive_id, action):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if action == 'approve':
        drive.status = 'approved'
        flash(f'Placement Drive "{drive.job_title}" approved!', 'success')
    elif action == 'reject':
        drive.status = 'rejected'
        flash(f'Placement Drive "{drive.job_title}" rejected.', 'warning')
        
    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/search')
@login_required
@admin_required
def search():
    q = request.args.get('q', '')
    students = []
    companies = []

    if q:
        students = db.session.query(Student, User).join(User, Student.user_id == User.id).filter(
            (Student.name.ilike(f'%{q}%')) | (Student.enrollment_no.ilike(f'%{q}%')) | 
            (User.email.ilike(f'%{q}%')) | (Student.phone.ilike(f'%{q}%'))
        ).all()

        companies = db.session.query(Company, User).join(User, Company.user_id == User.id).filter(
            (Company.company_name.ilike(f'%{q}%')) | (Company.hr_contact.ilike(f'%{q}%')) | 
            (User.email.ilike(f'%{q}%'))
        ).all()

    return render_template('admin/search.html', q=q, students=students, companies=companies)


@admin_bp.route('/toggle-active/<int:user_id>')
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'Admin':
        flash('Cannot deactivate an Admin account.', 'danger')
        return redirect(url_for('admin.search'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    if user.is_active:
        flash(f'User {user.email} has been reactivated.', 'success')
    else:
        flash(f'User {user.email} has been deactivated/blacklisted.', 'warning')
    
    return redirect(request.referrer or url_for('admin.search'))


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a student or company account permanently"""
    user = User.query.get_or_404(user_id)
    if user.role == 'Admin':
        flash('Cannot delete an Admin account.', 'danger')
        return redirect(url_for('admin.search'))
    
    # delete related records first depending on role
    if user.role == 'Student':
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            Application.query.filter_by(student_id=student.id).delete()
            db.session.delete(student)
    elif user.role == 'Company':
        company = Company.query.filter_by(user_id=user.id).first()
        if company:
            drives = PlacementDrive.query.filter_by(company_id=company.id).all()
            for drive in drives:
                Application.query.filter_by(drive_id=drive.id).delete()
                db.session.delete(drive)
            db.session.delete(company)
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.email} and all related records have been deleted.', 'success')
    return redirect(request.referrer or url_for('admin.search'))


@admin_bp.route('/all-drives')
@login_required
@admin_required
def all_drives():
    """View all placement drives with optional status filter"""
    status_filter = request.args.get('status', 'all')
    
    if status_filter != 'all':
        drives = db.session.query(PlacementDrive, Company).join(
            Company, PlacementDrive.company_id == Company.id
        ).filter(PlacementDrive.status == status_filter).order_by(PlacementDrive.created_at.desc()).all()
    else:
        drives = db.session.query(PlacementDrive, Company).join(
            Company, PlacementDrive.company_id == Company.id
        ).order_by(PlacementDrive.created_at.desc()).all()
    
    return render_template('admin/all_drives.html', drives=drives, status_filter=status_filter)


@admin_bp.route('/all-applications')
@login_required
@admin_required
def all_applications():
    """View all applications across all drives"""
    status_filter = request.args.get('status', 'all')
    
    query = db.session.query(Application, Student, PlacementDrive, Company).join(
        Student, Application.student_id == Student.id
    ).join(
        PlacementDrive, Application.drive_id == PlacementDrive.id
    ).join(
        Company, PlacementDrive.company_id == Company.id
    )
    
    if status_filter != 'all':
        query = query.filter(Application.status == status_filter)
    
    results = query.order_by(Application.applied_at.desc()).all()
    
    return render_template('admin/all_applications.html', results=results, status_filter=status_filter)


@admin_bp.route('/all-students')
@login_required
@admin_required
def all_students():
    """View and manage all registered students"""
    students = db.session.query(Student, User).join(
        User, Student.user_id == User.id
    ).order_by(Student.name).all()
    
    return render_template('admin/all_students.html', students=students)


@admin_bp.route('/all-companies')
@login_required
@admin_required
def all_companies():
    """View and manage all registered companies"""
    status_filter = request.args.get('status', 'all')
    
    query = db.session.query(Company, User).join(User, Company.user_id == User.id)
    
    if status_filter != 'all':
        query = query.filter(Company.approval_status == status_filter)
    
    companies = query.order_by(Company.company_name).all()
    
    return render_template('admin/all_companies.html', companies=companies, status_filter=status_filter)


@admin_bp.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    """Admin can edit any student's profile"""
    student = Student.query.get_or_404(student_id)
    user = User.query.get_or_404(student.user_id)
    
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
                    return redirect(url_for('admin.edit_student', student_id=student.id))
            except ValueError:
                flash('CGPA must be a valid number.', 'danger')
                return redirect(url_for('admin.edit_student', student_id=student.id))
        else:
            student.cgpa = None
        
        db.session.commit()
        flash(f'Student "{student.name}" profile updated successfully!', 'success')
        return redirect(url_for('admin.all_students'))
    
    return render_template('admin/edit_student.html', student=student, user=user)


@admin_bp.route('/edit-company/<int:company_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_company(company_id):
    """Admin can edit any company's profile"""
    company = Company.query.get_or_404(company_id)
    user = User.query.get_or_404(company.user_id)
    
    if request.method == 'POST':
        company.company_name = request.form.get('company_name', company.company_name)
        company.hr_contact = request.form.get('hr_contact', company.hr_contact)
        company.website = request.form.get('website')
        company.industry = request.form.get('industry')
        company.description = request.form.get('description')
        
        # admin can also change approval status from the edit form
        new_status = request.form.get('approval_status')
        if new_status in ['pending', 'approved', 'rejected']:
            company.approval_status = new_status
        
        db.session.commit()
        flash(f'Company "{company.company_name}" profile updated successfully!', 'success')
        return redirect(url_for('admin.all_companies'))
    
    return render_template('admin/edit_company.html', company=company, user=user)
