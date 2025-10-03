"""
Moulya College Management System
Main Flask application entry point
"""

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import db, init_db

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions with app
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Add CSRF token to template context
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.management import management_bp
    from routes.lecturer import lecturer_bp
    from routes.student import student_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(management_bp, url_prefix='/management')
    app.register_blueprint(lecturer_bp, url_prefix='/lecturer')
    app.register_blueprint(student_bp, url_prefix='/student')
    
    # Initialize database
    init_db(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8000, debug=True)