"""
Student routes for Moulya College Management System
Handles student dashboard, course details, subjects, attendance, and marks
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import login_required
from models.student import Student
from models.academic import Course, Subject
from models.attendance import AttendanceRecord
from models.marks import StudentMarks
from services.auth_service import SessionManager
from database import db
from datetime import datetime

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required('student')
def dashboard():
    """Student dashboard showing course details and subjects"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('auth.student_login'))
    
    # Get current subjects for the student
    current_subjects = student.get_current_subjects()
    
    # Get overall attendance and marks
    overall_attendance = student.get_overall_attendance_percentage()
    overall_marks = student.get_overall_marks_percentage()
    
    # Prepare subject data with attendance and marks
    subjects_data = []
    for subject in current_subjects:
        attendance_percentage = student.get_subject_attendance_percentage(subject.id)
        marks_summary = student.get_subject_marks_summary(subject.id)
        
        subjects_data.append({
            'subject': subject,
            'attendance_percentage': attendance_percentage,
            'marks_summary': marks_summary
        })
    
    stats = {
        'overall_attendance': overall_attendance,
        'overall_marks': overall_marks,
        'total_subjects': len(current_subjects),
        'subjects_data': subjects_data
    }
    
    return render_template('student/dashboard.html', student=student, stats=stats)

@student_bp.route('/course-details')
@login_required('student')
def course_details():
    """Display course details for the student"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student or not student.course:
        flash('Course information not found', 'error')
        return redirect(url_for('student.dashboard'))
    
    course = student.course
    
    # Get all subjects in the course
    all_subjects = course.subjects.order_by(Subject.year, Subject.semester).all()
    
    # Group subjects by year and semester
    subjects_by_year_semester = {}
    for subject in all_subjects:
        key = f"Year {subject.year}, Semester {subject.semester}"
        if key not in subjects_by_year_semester:
            subjects_by_year_semester[key] = []
        subjects_by_year_semester[key].append(subject)
    
    return render_template('student/course_details.html', 
                         student=student, 
                         course=course, 
                         subjects_by_year_semester=subjects_by_year_semester)

@student_bp.route('/subjects')
@login_required('student')
def subjects():
    """Display all subjects for the student"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('auth.student_login'))
    
    # Get current subjects
    current_subjects = student.get_current_subjects()
    
    # Get enrolled subjects data
    subjects_data = []
    for subject in current_subjects:
        attendance_percentage = student.get_subject_attendance_percentage(subject.id)
        marks_summary = student.get_subject_marks_summary(subject.id)
        
        subjects_data.append({
            'subject': subject,
            'attendance_percentage': attendance_percentage,
            'marks_summary': marks_summary,
            'is_enrolled': True
        })
    
    return render_template('student/subjects.html', student=student, subjects_data=subjects_data)

@student_bp.route('/subject/<int:subject_id>')
@login_required('student')
def subject_details(subject_id):
    """Display detailed view of a specific subject with attendance and marks"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('auth.student_login'))
    
    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject not found', 'error')
        return redirect(url_for('student.subjects'))
    
    # Check if student is enrolled in this subject
    if not student.is_enrolled_in_subject(subject_id):
        flash('You are not enrolled in this subject', 'error')
        return redirect(url_for('student.subjects'))
    
    # Get attendance records for this subject
    attendance_records = AttendanceRecord.query.filter_by(
        student_id=student_id,
        subject_id=subject_id
    ).order_by(AttendanceRecord.date.desc()).all()
    
    # Calculate attendance statistics
    total_classes = len(attendance_records)
    present_classes = len([r for r in attendance_records if r.status == 'present'])
    attendance_percentage = round((present_classes / total_classes * 100), 2) if total_classes > 0 else 0
    
    # Get marks for this subject
    marks_records = StudentMarks.query.filter_by(
        student_id=student_id,
        subject_id=subject_id
    ).all()
    
    # Group marks by assessment type
    marks_by_type = {}
    for mark in marks_records:
        assessment_type = mark.assessment_type
        if assessment_type not in marks_by_type:
            marks_by_type[assessment_type] = []
        marks_by_type[assessment_type].append(mark)
    
    # Calculate overall marks for the subject
    total_obtained = sum(mark.marks_obtained for mark in marks_records)
    total_max = sum(mark.max_marks for mark in marks_records)
    overall_percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0
    
    subject_data = {
        'subject': subject,
        'attendance_records': attendance_records,
        'attendance_percentage': attendance_percentage,
        'total_classes': total_classes,
        'present_classes': present_classes,
        'absent_classes': total_classes - present_classes,
        'marks_by_type': marks_by_type,
        'overall_percentage': overall_percentage,
        'total_obtained': total_obtained,
        'total_max': total_max
    }
    
    return render_template('student/subject_details.html', student=student, subject_data=subject_data)

@student_bp.route('/attendance')
@login_required('student')
def attendance():
    """Display overall attendance summary"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('auth.student_login'))
    
    # Get attendance data for all subjects
    current_subjects = student.get_current_subjects()
    attendance_data = []
    
    for subject in current_subjects:
        records = AttendanceRecord.query.filter_by(
            student_id=student_id,
            subject_id=subject.id
        ).order_by(AttendanceRecord.date.desc()).limit(10).all()
        
        total_classes = AttendanceRecord.query.filter_by(
            student_id=student_id,
            subject_id=subject.id
        ).count()
        
        present_classes = AttendanceRecord.query.filter_by(
            student_id=student_id,
            subject_id=subject.id,
            status='present'
        ).count()
        
        percentage = round((present_classes / total_classes * 100), 2) if total_classes > 0 else 0
        
        attendance_data.append({
            'subject': subject,
            'recent_records': records,
            'total_classes': total_classes,
            'present_classes': present_classes,
            'absent_classes': total_classes - present_classes,
            'percentage': percentage
        })
    
    overall_attendance = student.get_overall_attendance_percentage()
    
    return render_template('student/attendance.html', 
                         student=student, 
                         attendance_data=attendance_data,
                         overall_attendance=overall_attendance)

@student_bp.route('/marks')
@login_required('student')
def marks():
    """Display overall marks summary"""
    student_id = SessionManager.get_current_user_id(session)
    student = Student.query.get(student_id)
    
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('auth.student_login'))
    
    # Get marks data for all subjects
    current_subjects = student.get_current_subjects()
    marks_data = []
    
    for subject in current_subjects:
        marks_records = StudentMarks.query.filter_by(
            student_id=student_id,
            subject_id=subject.id
        ).all()
        
        if marks_records:
            total_obtained = sum(mark.marks_obtained for mark in marks_records)
            total_max = sum(mark.max_marks for mark in marks_records)
            percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0
            
            marks_data.append({
                'subject': subject,
                'marks_records': marks_records,
                'total_obtained': total_obtained,
                'total_max': total_max,
                'percentage': percentage
            })
    
    overall_marks = student.get_overall_marks_percentage()
    
    return render_template('student/marks.html', 
                         student=student, 
                         marks_data=marks_data,
                         overall_marks=overall_marks)