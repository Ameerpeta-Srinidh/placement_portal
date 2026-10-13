from flask import Flask, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'A_RANDOM_SECRET_KEY'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db' 
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB max upload

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @app.route('/')
    def home():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if current_user.role == 'Admin':
            return redirect(url_for('admin.dashboard'))
        if current_user.role == 'Student':
            return redirect(url_for('student.dashboard'))
        if current_user.role == 'Company':
            return redirect(url_for('company.dashboard'))

        return redirect(url_for('auth.login'))
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # custom error handlers for nice looking error pages
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    with app.app_context():
        from models import User, Student, Company, PlacementDrive, Application
        db.create_all()
        # check if default admin already exists - if not create one
        admin_exists = User.query.filter_by(role='Admin').first()
        if not admin_exists:
            hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin = User(email="admin@university.edu", password=hashed_pw, role='Admin')
            db.session.add(admin)
            db.session.commit()
            print("Default System Admin created!")

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.company import company_bp
    from routes.student import student_bp
    from routes.api import api_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    return app
