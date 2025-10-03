"""
Attendance models for Moulya College Management System
AttendanceRecord and MonthlyAttendanceSummary models
"""

from database import db
from datetime import datetime, date

class AttendanceRecord(db.Model):
    """Daily attendance record for students"""
    __tablename__ = 'attendance_record'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False)  # 'present' or 'absent'
    remarks = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate attendance for same student, subject, date
    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', 'date', name='unique_student_subject_date_attendance'),)
    
    def mark_present(self):
        """Mark student as present"""
        self.status = 'present'
        self.updated_at = datetime.utcnow()
    
    def mark_absent(self):
        """Mark student as absent"""
        self.status = 'absent'
        self.updated_at = datetime.utcnow()
    
    def is_present(self):
        """Check if student was present"""
        return self.status == 'present'
    
    def is_absent(self):
        """Check if student was absent"""
        return self.status == 'absent'
    
    @staticmethod
    def get_attendance_for_month(student_id, subject_id, month, year):
        """Get attendance records for a specific month"""
        return AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.subject_id == subject_id,
            db.extract('month', AttendanceRecord.date) == month,
            db.extract('year', AttendanceRecord.date) == year
        ).all()
    
    @staticmethod
    def get_attendance_percentage(student_id, subject_id, start_date=None, end_date=None):
        """Calculate attendance percentage for a student in a subject"""
        query = AttendanceRecord.query.filter_by(
            student_id=student_id,
            subject_id=subject_id
        )
        
        if start_date:
            query = query.filter(AttendanceRecord.date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.date <= end_date)
        
        total_records = query.count()
        if total_records == 0:
            return 0
        
        present_records = query.filter_by(status='present').count()
        return round((present_records / total_records) * 100, 2)
    
    def to_dict(self):
        """Convert attendance record to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'student_roll_number': self.student.roll_number if self.student else None,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
            'lecturer_id': self.lecturer_id,
            'lecturer_name': self.lecturer.name if self.lecturer else None,
            'date': self.date.isoformat() if self.date else None,
            'status': self.status,
            'remarks': self.remarks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        student_roll = self.student.roll_number if self.student else "Unknown"
        subject_code = self.subject.code if self.subject else "Unknown"
        return f'<AttendanceRecord {student_roll} - {subject_code} - {self.date} - {self.status}>'

class MonthlyAttendanceSummary(db.Model):
    """Monthly attendance summary for subjects"""
    __tablename__ = 'monthly_attendance_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_classes = db.Column(db.Integer, nullable=False)
    total_students = db.Column(db.Integer, nullable=False, default=0)
    average_attendance = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for subject, lecturer, month, year
    __table_args__ = (db.UniqueConstraint('subject_id', 'lecturer_id', 'month', 'year', name='unique_subject_lecturer_month_year'),)
    
    def calculate_average_attendance(self):
        """Calculate and update average attendance for the month"""
        # Get all attendance records for this subject and month
        attendance_records = AttendanceRecord.query.filter(
            AttendanceRecord.subject_id == self.subject_id,
            db.extract('month', AttendanceRecord.date) == self.month,
            db.extract('year', AttendanceRecord.date) == self.year
        ).all()
        
        if not attendance_records:
            self.average_attendance = 0.0
            return
        
        # Calculate average attendance percentage
        total_records = len(attendance_records)
        present_records = len([r for r in attendance_records if r.status == 'present'])
        
        self.average_attendance = round((present_records / total_records) * 100, 2) if total_records > 0 else 0.0
        self.updated_at = datetime.utcnow()
    
    def get_student_attendance_summary(self):
        """Get attendance summary for all students in this subject for the month"""
        from models.student import Student
        
        # Get all students enrolled in this subject
        enrolled_students = Student.query.join('enrollments').filter_by(
            subject_id=self.subject_id,
            is_active=True
        ).all()
        
        summary = []
        for student in enrolled_students:
            attendance_records = AttendanceRecord.query.filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.subject_id == self.subject_id,
                db.extract('month', AttendanceRecord.date) == self.month,
                db.extract('year', AttendanceRecord.date) == self.year
            ).all()
            
            total_classes = len(attendance_records)
            present_classes = len([r for r in attendance_records if r.status == 'present'])
            percentage = round((present_classes / total_classes) * 100, 2) if total_classes > 0 else 0
            
            summary.append({
                'student_id': student.id,
                'student_name': student.name,
                'roll_number': student.roll_number,
                'total_classes': total_classes,
                'present_classes': present_classes,
                'absent_classes': total_classes - present_classes,
                'attendance_percentage': percentage
            })
        
        return summary
    
    @staticmethod
    def get_or_create(subject_id, lecturer_id, month, year, total_classes):
        """Get existing summary or create new one"""
        summary = MonthlyAttendanceSummary.query.filter_by(
            subject_id=subject_id,
            lecturer_id=lecturer_id,
            month=month,
            year=year
        ).first()
        
        if not summary:
            summary = MonthlyAttendanceSummary(
                subject_id=subject_id,
                lecturer_id=lecturer_id,
                month=month,
                year=year,
                total_classes=total_classes
            )
            db.session.add(summary)
        else:
            summary.total_classes = total_classes
            summary.updated_at = datetime.utcnow()
        
        summary.calculate_average_attendance()
        return summary
    
    def to_dict(self):
        """Convert monthly summary to dictionary"""
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
            'lecturer_id': self.lecturer_id,
            'lecturer_name': self.lecturer.name if self.lecturer else None,
            'month': self.month,
            'year': self.year,
            'total_classes': self.total_classes,
            'total_students': self.total_students,
            'average_attendance': self.average_attendance,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        subject_code = self.subject.code if self.subject else "Unknown"
        return f'<MonthlyAttendanceSummary {subject_code} - {self.month}/{self.year}>'


class MonthlyStudentAttendance(db.Model):
    """Per-student monthly attendance (supports multiple classes per day).

    Stores the number of classes a student attended in a given month for a subject/lecturer.
    This allows present count to exceed calendar days when multiple classes occur on the same day.
    """
    __tablename__ = 'monthly_student_attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturer.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    present_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'lecturer_id', 'month', 'year',
                            name='unique_student_subject_lecturer_month_year_attendance'),
    )

    @staticmethod
    def get_or_create(student_id, subject_id, lecturer_id, month, year):
        rec = MonthlyStudentAttendance.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            lecturer_id=lecturer_id,
            month=month,
            year=year
        ).first()
        if not rec:
            rec = MonthlyStudentAttendance(
                student_id=student_id,
                subject_id=subject_id,
                lecturer_id=lecturer_id,
                month=month,
                year=year,
                present_count=0
            )
            db.session.add(rec)
        return rec