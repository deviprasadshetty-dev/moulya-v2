"""
Database migration script to add password fields to student table
Run this script to update the database schema for student password functionality
"""

from database import db
from app import create_app

def migrate_student_password_fields():
    """Add password fields to student table"""

    app = create_app()

    with app.app_context():
        try:
            # Get database connection
            connection = db.engine.connect()

            # Check if password columns already exist
            result = connection.execute(db.text("PRAGMA table_info(student)"))
            columns = [row[1] for row in result.fetchall()]

            if 'password_hash' in columns and 'password_encrypted' in columns and 'username' in columns:
                print("Password fields already exist in student table.")
                connection.close()
                return True

            print("Adding password fields to student table...")

            # Disable foreign key constraints temporarily
            print("Disabling foreign key constraints...")
            connection.execute(db.text("PRAGMA foreign_keys = OFF"))

            # Backup existing data from dependent tables
            print("Backing up dependent table data...")
            enrollment_data = connection.execute(db.text("""
                SELECT id, student_id, subject_id, academic_year, enrolled_at, is_active
                FROM student_enrollment
            """)).fetchall()

            marks_data = connection.execute(db.text("""
                SELECT id, student_id, subject_id, lecturer_id, assessment_type, marks_obtained, max_marks, percentage, grade, remarks, assessment_date, created_at, updated_at
                FROM student_marks
            """)).fetchall()

            attendance_data = connection.execute(db.text("""
                SELECT id, student_id, subject_id, lecturer_id, date, status, remarks, created_at, updated_at
                FROM attendance_record
            """)).fetchall()

            # Backup existing student data
            print("Backing up existing student data...")
            students_data = connection.execute(db.text("""
                SELECT id, roll_number, name, course_id, academic_year, current_semester,
                       email, phone, address, date_of_birth, admission_date, created_at, is_active
                FROM student
            """)).fetchall()

            # Drop dependent tables
            print("Dropping dependent tables...")
            connection.execute(db.text("DROP TABLE IF EXISTS student_enrollment"))
            connection.execute(db.text("DROP TABLE IF EXISTS student_marks"))
            connection.execute(db.text("DROP TABLE IF EXISTS attendance_record"))

            # Drop and recreate student table
            print("Recreating student table with password fields...")
            connection.execute(db.text("DROP TABLE student"))

            # Recreate all tables (this will use the new model definitions)
            db.create_all()

            # Generate passwords and restore student data
            print("Restoring student data with generated passwords...")
            from models.student import Student

            for student_data in students_data:
                # Generate username and password for existing students
                roll_number = student_data[1]
                username = Student.generate_username(roll_number)
                password = Student.generate_password()

                # Create student object and set password
                student = Student(
                    id=student_data[0],
                    roll_number=roll_number,
                    name=student_data[2],
                    username=username,
                    course_id=student_data[3],
                    academic_year=student_data[4],
                    current_semester=student_data[5],
                    email=student_data[6],
                    phone=student_data[7],
                    address=student_data[8],
                    date_of_birth=student_data[9],
                    admission_date=student_data[10],
                    created_at=student_data[11],
                    is_active=student_data[12]
                )
                student.set_password(password)

                # Add to database
                db.session.add(student)

            # Restore dependent table data
            print("Restoring dependent table data...")

            # Restore enrollment data
            for enrollment in enrollment_data:
                connection.execute(db.text("""
                    INSERT INTO student_enrollment (id, student_id, subject_id, academic_year, enrolled_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """), (enrollment[0], enrollment[1], enrollment[2], enrollment[3], enrollment[4], enrollment[5]))

            # Restore marks data
            for mark in marks_data:
                connection.execute(db.text("""
                    INSERT INTO student_marks (id, student_id, subject_id, lecturer_id, assessment_type, marks_obtained, max_marks, percentage, grade, remarks, assessment_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """), (mark[0], mark[1], mark[2], mark[3], mark[4], mark[5], mark[6], mark[7], mark[8], mark[9], mark[10], mark[11], mark[12]))

            # Restore attendance data
            for attendance in attendance_data:
                connection.execute(db.text("""
                    INSERT INTO attendance_record (id, student_id, subject_id, lecturer_id, date, status, remarks, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """), (attendance[0], attendance[1], attendance[2], attendance[3], attendance[4], attendance[5], attendance[6], attendance[7], attendance[8]))

            # Re-enable foreign key constraints
            print("Re-enabling foreign key constraints...")
            connection.execute(db.text("PRAGMA foreign_keys = ON"))

            db.session.commit()
            print("Migration completed successfully!")
            print("All existing students have been assigned generated usernames and passwords.")
            print("Usernames are based on roll numbers, passwords are randomly generated.")

            connection.close()

        except Exception as e:
            print(f"Migration failed: {str(e)}")
            print("Please backup your database before running this script.")
            db.session.rollback()
            return False

    return True

if __name__ == "__main__":
    print("Starting database migration for student password fields...")
    print("WARNING: This will modify your database structure.")
    print("Make sure to backup your database before proceeding.")
    print()

    confirm = input("Do you want to continue? (yes/no): ")
    if confirm.lower() == 'yes':
        if migrate_student_password_fields():
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
    else:
        print("Migration cancelled.")