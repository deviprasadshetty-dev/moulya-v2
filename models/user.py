"""
User models for Moulya College Management System
Management and Lecturer user models
"""

from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re

class Management(db.Model):
    """Management user model for administrative access"""
    __tablename__ = 'management'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<Management {self.username}>'

class Lecturer(db.Model):
    """Lecturer user model"""
    __tablename__ = 'lecturer'
    
    id = db.Column(db.Integer, primary_key=True)
    lecturer_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(120), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=True)  # Encrypted password for management access
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    subject_assignments = db.relationship('SubjectAssignment', backref='lecturer', lazy='dynamic')
    attendance_records = db.relationship('AttendanceRecord', backref='lecturer', lazy='dynamic')
    monthly_summaries = db.relationship('MonthlyAttendanceSummary', backref='lecturer', lazy='dynamic')
    student_marks = db.relationship('StudentMarks', backref='lecturer', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash and encrypted password for management access"""
        from utils.encryption import password_encryptor
        self.password_hash = generate_password_hash(password)
        self.password_encrypted = password_encryptor.encrypt_password(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_assigned_subjects(self):
        """Get subjects actively assigned to this lecturer for the current academic year"""
        from datetime import datetime
        current_year = datetime.now().year
        active_assignments_current_year = (
            self.subject_assignments
                .filter_by(academic_year=current_year, is_active=True)
                .all()
        )
        return [assignment.subject for assignment in active_assignments_current_year]
    
    def is_assigned_to_subject(self, subject_id):
        """Check if lecturer is assigned to a specific subject"""
        return self.subject_assignments.filter_by(subject_id=subject_id).first() is not None
    
    def get_decrypted_password(self):
        """Get decrypted password for management access"""
        from utils.encryption import password_encryptor
        if self.password_encrypted:
            return password_encryptor.decrypt_password(self.password_encrypted)
        return None
    
    @staticmethod
    def generate_username(name, lecturer_id):
        """Generate username from name and lecturer ID in BBHC format"""
        # Take first name and add BBHC format
        first_name = name.split()[0].lower()
        # Sanitize lecturer_id to only contain valid username characters (letters, numbers, underscores)
        sanitized_lecturer_id = re.sub(r'[^A-Za-z0-9_]', '_', lecturer_id.lower())
        return f"bbhc_{first_name}_{sanitized_lecturer_id}"
    
    @staticmethod
    def generate_password():
        """Generate a random password for new lecturers"""
        import random
        import string
        
        # Generate 8-character password with letters and numbers
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(8))
    
    def to_dict(self):
        """Convert lecturer to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'lecturer_id': self.lecturer_id,
            'name': self.name,
            'username': self.username,
            'assigned_subjects': [subject.name for subject in self.get_assigned_subjects()],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Lecturer {self.lecturer_id}: {self.name}>'


class Administrator(db.Model):
    """Administrator model for high-level system control"""
    __tablename__ = 'administrator'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(120), nullable=False)
    secret_path = db.Column(db.String(36), unique=True, nullable=False)  # UUID for secret access
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    permissions = db.Column(db.Text, default='all')  # JSON string of permissions

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def has_permission(self, permission):
        """Check if admin has specific permission"""
        if self.permissions == 'all':
            return True
        permissions = self.permissions.split(',') if self.permissions else []
        return permission in permissions

    def get_permissions_list(self):
        """Get list of permissions"""
        if self.permissions == 'all':
            return ['all']
        return self.permissions.split(',') if self.permissions else []

    @staticmethod
    def generate_secret_path():
        """Generate a random UUID for secret path access"""
        import uuid
        return str(uuid.uuid4())

    def __repr__(self):
        return f'<Administrator {self.username}>'