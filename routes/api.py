from flask import Blueprint, jsonify
from models import Student, Company, PlacementDrive, Application, User

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/drives')
def get_drives():
    """Get all approved placement drives"""
    drives = PlacementDrive.query.filter_by(status='approved').all()
    result = []
    for d in drives:
        company = Company.query.get(d.company_id)
        result.append({
            'id': d.id,
            'job_title': d.job_title,
            'description': d.description,
            'eligibility': d.eligibility,
            'salary_package': d.salary_package,
            'location': d.location,
            'job_type': d.job_type,
            'deadline': d.deadline.strftime('%Y-%m-%d'),
            'status': d.status,
            'company_name': company.company_name if company else 'N/A'
        })
    return jsonify(result)

@api_bp.route('/students')
def get_students():
    """Get all registered students"""
    students = Student.query.all()
    result = []
    for s in students:
        user = User.query.get(s.user_id)
        result.append({
            'id': s.id,
            'name': s.name,
            'enrollment_no': s.enrollment_no,
            'branch': s.branch,
            'cgpa': s.cgpa,
            'phone': s.phone,
            'email': user.email if user else 'N/A',
            'resume_path': s.resume_path
        })
    return jsonify(result)

@api_bp.route('/companies')
def get_companies():
    """Get all registered companies"""
    companies = Company.query.all()
    result = []
    for c in companies:
        result.append({
            'id': c.id,
            'company_name': c.company_name,
            'hr_contact': c.hr_contact,
            'website': c.website,
            'industry': c.industry,
            'approval_status': c.approval_status
        })
    return jsonify(result)

@api_bp.route('/applications/<int:drive_id>')
def get_applications(drive_id):
    """Get all applications for a specific drive"""
    applications = Application.query.filter_by(drive_id=drive_id).all()
    result = []
    for a in applications:
        student = Student.query.get(a.student_id)
        result.append({
            'id': a.id,
            'student_name': student.name if student else 'Unknown',
            'enrollment_no': student.enrollment_no if student else 'N/A',
            'status': a.status,
            'applied_at': a.applied_at.strftime('%Y-%m-%d')
        })
    return jsonify(result)

@api_bp.route('/stats')
def get_stats():
    """Get platform statistics - useful for dashboard widgets"""
    stats = {
        'total_students': Student.query.count(),
        'total_companies': Company.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'total_applications': Application.query.count(),
        'approved_companies': Company.query.filter_by(approval_status='approved').count(),
        'approved_drives': PlacementDrive.query.filter_by(status='approved').count(),
        'selected_students': Application.query.filter_by(status='Selected').count(),
        'pending_companies': Company.query.filter_by(approval_status='pending').count(),
    }
    return jsonify(stats)
