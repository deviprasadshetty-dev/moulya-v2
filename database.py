"""
Database configuration and initialization for Moulya College Management System
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

# Initialize SQLAlchemy instance
db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def init_db(app):
    """Initialize database with application context"""
    with app.app_context():
        # Import all models to ensure they are registered
        from models import (
            Management, Lecturer, Course, Subject, AcademicYear,
            Student, StudentEnrollment, AttendanceRecord,
            MonthlyAttendanceSummary, StudentMarks, SubjectAssignment
        )
        
        # Create all tables
        db.create_all()
        
        # Create default management user if not exists
        create_default_management_user()
        
        print("Database initialized successfully!")

def create_default_management_user():
    """Create default management user for initial access"""
    from models.user import Management
    from werkzeug.security import generate_password_hash
    
    # Check if management user already exists
    existing_user = Management.query.filter_by(username='admin').first()
    
    if not existing_user:
        default_user = Management(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        
        try:
            db.session.add(default_user)
            db.session.commit()
            print("Default management user created: admin/admin123")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default user: {e}")

def reset_database(app):
    """Reset database - WARNING: This will delete all data"""
    with app.app_context():
        # Disable foreign key constraints temporarily
        db.engine.execute("PRAGMA foreign_keys=OFF")
        
        # Drop all tables
        db.drop_all()
        
        # Re-enable foreign key constraints
        db.engine.execute("PRAGMA foreign_keys=ON")
        
        # Create all tables
        db.create_all()
        
        # Create default management user
        create_default_management_user()
        print("Database reset completed!")

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

def handle_db_error(func):
    """Decorator to handle database errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
    return wrapper