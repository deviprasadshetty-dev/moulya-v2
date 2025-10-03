from app import create_app
from database import db
from models.attendance import MonthlyStudentAttendance

app = create_app()
with app.app_context():
    MonthlyStudentAttendance.__table__.create(bind=db.engine, checkfirst=True)
    print("Created monthly_student_attendance (if missing)")