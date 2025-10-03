"""
Authentication service for Moulya College Management System
Handles login, password management, and session utilities
"""

from werkzeug.security import generate_password_hash, check_password_hash
from models.user import Management, Lecturer
from database import db
from datetime import datetime
import random
import string

class AuthService:
    """Authentication service class"""
    
    @staticmethod
    def authenticate_management(username, password):
        """Authenticate management user"""
        try:
            # Case-insensitive username match
            from sqlalchemy import func
            normalized = (username or '').strip()
            user = (
                Management.query
                .filter(func.lower(Management.username) == func.lower(normalized))
                .filter_by(is_active=True)
                .first()
            )
            
            if user and user.check_password(password):
                user.update_last_login()
                return True, user, "Login successful"
            
            return False, None, "Invalid username or password"
        
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    @staticmethod
    def authenticate_lecturer(username, password):
        """Authenticate lecturer user"""
        try:
            # Case-insensitive username match
            from sqlalchemy import func
            normalized = (username or '').strip()
            user = (
                Lecturer.query
                .filter(func.lower(Lecturer.username) == func.lower(normalized))
                .filter_by(is_active=True)
                .first()
            )
            
            if user and user.check_password(password):
                user.update_last_login()
                return True, user, "Login successful"
            
            return False, None, "Invalid username or password"
        
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    @staticmethod
    def authenticate_student(username, password):
        """Authenticate student user"""
        try:
            # Case-insensitive username match
            from sqlalchemy import func
            from models.student import Student
            normalized = (username or '').strip()
            user = (
                Student.query
                .filter(func.lower(Student.username) == func.lower(normalized))
                .filter_by(is_active=True)
                .first()
            )
            
            if user and user.check_password(password):
                return True, user, "Login successful"
            
            return False, None, "Invalid username or password"
        
        except Exception as e:
            return False, None, f"Authentication error: {str(e)}"
    
    @staticmethod
    def generate_lecturer_credentials(name, lecturer_id, manual_username=None, manual_password=None):
        """Generate username and password for lecturer"""
        try:
            # Generate username
            if manual_username:
                username = manual_username
            else:
                # Use lecturer_id as the base username (sanitized to allowed characters)
                import re
                base_username = re.sub(r'[^A-Za-z0-9_]', '_', str(lecturer_id).strip())
                username = base_username.lower() or 'lecturer'
                
                # Ensure username is unique
                counter = 1
                original_username = username
                while Lecturer.query.filter_by(username=username).first():
                    username = f"{original_username}_{counter}"
                    counter += 1
            
            # Generate password
            if manual_password:
                password = manual_password
            else:
                password = Lecturer.generate_password()
            
            return True, username, password, "Credentials generated successfully"
        
        except Exception as e:
            return False, None, None, f"Error generating credentials: {str(e)}"
    
    @staticmethod
    def hash_password(password):
        """Hash password using Werkzeug"""
        try:
            return generate_password_hash(password)
        except Exception as e:
            raise Exception(f"Error hashing password: {str(e)}")
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against hash"""
        try:
            return check_password_hash(password_hash, password)
        except Exception as e:
            return False
    
    @staticmethod
    def change_password(user_type, user_id, old_password, new_password):
        """Change user password"""
        try:
            if user_type == 'management':
                user = Management.query.get(user_id)
            elif user_type == 'lecturer':
                user = Lecturer.query.get(user_id)
            elif user_type == 'student':
                from models.student import Student
                user = Student.query.get(user_id)
            else:
                return False, "Invalid user type"
            
            if not user:
                return False, "User not found"
            
            if not user.check_password(old_password):
                return False, "Current password is incorrect"
            
            user.set_password(new_password)
            db.session.commit()
            
            return True, "Password changed successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error changing password: {str(e)}"
    
    @staticmethod
    def reset_lecturer_password(lecturer_id):
        """Reset lecturer password to a new random password"""
        try:
            lecturer = Lecturer.query.filter_by(lecturer_id=lecturer_id).first()
            
            if not lecturer:
                return False, None, "Lecturer not found"
            
            new_password = Lecturer.generate_password()
            lecturer.set_password(new_password)
            db.session.commit()
            
            return True, new_password, "Password reset successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, None, f"Error resetting password: {str(e)}"
    
    @staticmethod
    def create_management_user(username, password):
        """Create new management user"""
        try:
            # Check if username already exists
            existing_user = Management.query.filter_by(username=username).first()
            if existing_user:
                return False, None, "Username already exists"
            
            # Create new management user
            user = Management(username=username)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            return True, user, "Management user created successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, None, f"Error creating management user: {str(e)}"
    
    @staticmethod
    def deactivate_user(user_type, user_id):
        """Deactivate user account"""
        try:
            if user_type == 'management':
                user = Management.query.get(user_id)
            elif user_type == 'lecturer':
                user = Lecturer.query.get(user_id)
            else:
                return False, "Invalid user type"
            
            if not user:
                return False, "User not found"
            
            user.is_active = False
            db.session.commit()
            
            return True, "User deactivated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error deactivating user: {str(e)}"
    
    @staticmethod
    def activate_user(user_type, user_id):
        """Activate user account"""
        try:
            if user_type == 'management':
                user = Management.query.get(user_id)
            elif user_type == 'lecturer':
                user = Lecturer.query.get(user_id)
            else:
                return False, "Invalid user type"
            
            if not user:
                return False, "User not found"
            
            user.is_active = True
            db.session.commit()
            
            return True, "User activated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error activating user: {str(e)}"
    
    @staticmethod
    def get_user_info(user_type, user_id):
        """Get user information"""
        try:
            if user_type == 'management':
                user = Management.query.get(user_id)
            elif user_type == 'lecturer':
                user = Lecturer.query.get(user_id)
            elif user_type == 'student':
                from models.student import Student
                user = Student.query.get(user_id)
            else:
                return None, "Invalid user type"
            
            if not user:
                return None, "User not found"
            
            return user, "User found"
        
        except Exception as e:
            return None, f"Error getting user info: {str(e)}"

class SessionManager:
    """Session management utilities"""
    
    @staticmethod
    def create_session(session, user_type, user_id, username):
        """Create user session"""
        session['user_type'] = user_type
        session['user_id'] = user_id
        session['username'] = username
        session['login_time'] = datetime.utcnow().isoformat()
        session.permanent = True
    
    @staticmethod
    def clear_session(session):
        """Clear user session"""
        session.clear()
    
    @staticmethod
    def is_authenticated(session):
        """Check if user is authenticated"""
        return 'user_type' in session and 'user_id' in session
    
    @staticmethod
    def is_management(session):
        """Check if current user is management"""
        return session.get('user_type') == 'management'
    
    @staticmethod
    def is_lecturer(session):
        """Check if current user is lecturer"""
        return session.get('user_type') == 'lecturer'
    
    @staticmethod
    def is_student(session):
        """Check if current user is student"""
        return session.get('user_type') == 'student'
    
    @staticmethod
    def get_current_user_id(session):
        """Get current user ID from session"""
        return session.get('user_id')
    
    @staticmethod
    def get_current_username(session):
        """Get current username from session"""
        return session.get('username')
    
    @staticmethod
    def get_session_info(session):
        """Get complete session information"""
        if not SessionManager.is_authenticated(session):
            return None
        
        return {
            'user_type': session.get('user_type'),
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'login_time': session.get('login_time')
        }