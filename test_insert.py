from app import db, create_app
from models import User, Company, PlacementDrive
from datetime import datetime

app = create_app()
with app.app_context():
    company = Company.query.first()
    if not company:
        print("No company found.")
    else:
        try:
            deadline = datetime.strptime("2024-05-05", "%Y-%m-%d")
            new_drive = PlacementDrive(
                company_id=company.id,
                job_title="Test",
                description="Test",
                eligibility="Test",
                deadline=deadline,
                status="pending"
            )
            db.session.add(new_drive)
            db.session.commit()
            print("Successfully inserted test drive.")
        except Exception as e:
            print("Error inserting:", str(e))
