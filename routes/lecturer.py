"""
Lecturer portal routes for Moulya College Management System
Handles all lecturer functionality
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from routes.auth import login_required
from services.lecturer_service import LecturerService
from models.academic import Subject
from services.reporting_service import ReportingService
from database import db
from models.student import Student
from models.attendance import AttendanceRecord, MonthlyAttendanceSummary
from datetime import datetime, date

lecturer_bp = Blueprint('lecturer', __name__)

@lecturer_bp.route('/dashboard')
@login_required('lecturer')
def dashboard():
    """Lecturer dashboard with overview statistics"""
    try:
        lecturer_id = session.get('user_id')
        stats = LecturerService.get_lecturer_dashboard_stats(lecturer_id)
        return render_template('lecturer/dashboard.html', stats=stats)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('lecturer/dashboard.html', stats={})

@lecturer_bp.route('/subjects')
@login_required('lecturer')
def subjects():
    """View assigned subjects"""
    try:
        lecturer_id = session.get('user_id')
        subjects_list = LecturerService.get_assigned_subjects(lecturer_id)
        return render_template('lecturer/subjects.html', subjects=subjects_list)
    except Exception as e:
        flash(f'Error loading subjects: {str(e)}', 'error')
        return render_template('lecturer/subjects.html', subjects=[])

@lecturer_bp.route('/subjects/<int:subject_id>/students')
@login_required('lecturer')
def subject_students(subject_id):
    """View students enrolled in a subject"""
    try:
        lecturer_id = session.get('user_id')
        students = LecturerService.get_subject_students(subject_id, lecturer_id)
        subject = Subject.query.get_or_404(subject_id)
        
        # Get all students for enrollment - only those from the same course as the subject
        # Sort by roll number (and name as tiebreaker) for consistent ordering in UI
        from utils.sorting_helpers import SortingHelpers
        all_students_unsorted = (Student.query
            .filter_by(is_active=True, course_id=subject.course_id)
            .all())
        all_students = SortingHelpers.sort_students(all_students_unsorted)
        
        return render_template('lecturer/subject_students.html', 
                             subject=subject, 
                             students=students,
                             all_students=all_students)
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'error')
        return redirect(url_for('lecturer.subjects'))

@lecturer_bp.route('/subjects/<int:subject_id>/students/add', methods=['POST'])
@login_required('lecturer')
def add_students_to_subject(subject_id):
    """Add students to subject"""
    try:
        lecturer_id = session.get('user_id')
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            flash('No students selected', 'error')
            return redirect(url_for('lecturer.subject_students', subject_id=subject_id))
        
        success, message = LecturerService.enroll_students(subject_id, student_ids, lecturer_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
    except Exception as e:
        flash(f'Error adding students: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.subject_students', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/students/remove', methods=['POST'])
@login_required('lecturer')
def remove_students_from_subject(subject_id):
    """Remove students from subject"""
    try:
        lecturer_id = session.get('user_id')
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            flash('No students selected', 'error')
            return redirect(url_for('lecturer.subject_students', subject_id=subject_id))
        
        success, message = LecturerService.unenroll_students(subject_id, student_ids, lecturer_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
    except Exception as e:
        flash(f'Error removing students: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.subject_students', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/attendance')
@login_required('lecturer')
def attendance_management(subject_id):
    """Attendance management for a subject"""
    try:
        lecturer_id = session.get('user_id')
        students = LecturerService.get_subject_students(subject_id, lecturer_id)
        subject = Subject.query.get_or_404(subject_id)
        
        # Get selected date from query params
        selected_date = request.args.get('date')
        if selected_date:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            selected_date = date.today()
        
        # Get existing attendance for the date
        from models.attendance import AttendanceRecord, MonthlyAttendanceSummary
        existing_attendance = {}
        for student in students:
            record = AttendanceRecord.query.filter_by(
                student_id=student.id,
                subject_id=subject_id,
                date=selected_date
            ).first()
            if record:
                existing_attendance[student.id] = record.status
        
        # Get monthly summary for current month
        monthly_summary = MonthlyAttendanceSummary.query.filter_by(
            subject_id=subject_id,
            lecturer_id=lecturer_id,
            month=selected_date.month,
            year=selected_date.year
        ).first()
        
        # Compute cumulative totals up to previous month for validation hints
        from sqlalchemy import func
        prior_total_classes = (db.session.query(func.coalesce(func.sum(MonthlyAttendanceSummary.total_classes), 0))
            .filter(
                MonthlyAttendanceSummary.subject_id == subject_id,
                MonthlyAttendanceSummary.lecturer_id == lecturer_id,
                ((MonthlyAttendanceSummary.year < selected_date.year) |
                 ((MonthlyAttendanceSummary.year == selected_date.year) & (MonthlyAttendanceSummary.month < selected_date.month)))
            ).scalar() or 0)

        # Per-student present count up to previous month (use MonthlyStudentAttendance sums)
        from datetime import date as _date
        from sqlalchemy import func
        from models.attendance import MonthlyStudentAttendance as MSA
        prev_cutoff = _date(selected_date.year, selected_date.month, 1)
        prev_present_map = {}
        for s in students:
            prev_present = (db.session.query(func.coalesce(func.sum(MSA.present_count), 0))
                .filter(
                    MSA.student_id == s.id,
                    MSA.subject_id == subject_id,
                    MSA.lecturer_id == lecturer_id,
                    ((MSA.year < prev_cutoff.year) | ((MSA.year == prev_cutoff.year) & (MSA.month < prev_cutoff.month)))
                ).scalar() or 0)
            prev_present_map[s.id] = int(prev_present)

        # Build prior totals map for all months/years to support client-side validation when month/year changes
        # Map keys as f"{year}-{month:02d}" to cumulative total till previous month
        prior_totals_map = {}
        summaries = (MonthlyAttendanceSummary.query
            .filter(
                MonthlyAttendanceSummary.subject_id == subject_id,
                MonthlyAttendanceSummary.lecturer_id == lecturer_id
            )
            .order_by(MonthlyAttendanceSummary.year.asc(), MonthlyAttendanceSummary.month.asc())
            ).all()
        # Accumulate totals in chronological order
        cumulative_by_year_month = {}
        cumulative_total = 0
        for s in summaries:
            key = f"{s.year}-{s.month:02d}"
            # prior for this month is current cumulative
            prior_totals_map[key] = cumulative_total
            cumulative_total += int(s.total_classes or 0)
            cumulative_by_year_month[key] = cumulative_total

        # Build previous-presents map per month-year for each student
        # Keys: 'YYYY-MM' -> { studentId: prevPresentsBeforeMonth }
        from datetime import date as _date
        from models.attendance import MonthlyStudentAttendance as MSA
        prev_present_by_month_map = {}
        # Include months present in summaries and the current selected month
        months_to_prepare = {(s.year, s.month) for s in summaries}
        months_to_prepare.add((selected_date.year, selected_date.month))
        for (yr, mo) in sorted(months_to_prepare):
            cutoff = _date(yr, mo, 1)
            per_student = {}
            for s in students:
                count_prev = (db.session.query(func.coalesce(func.sum(MSA.present_count), 0))
                    .filter(
                        MSA.student_id == s.id,
                        MSA.subject_id == subject_id,
                        MSA.lecturer_id == lecturer_id,
                        ((MSA.year < cutoff.year) | ((MSA.year == cutoff.year) & (MSA.month < cutoff.month)))
                    ).scalar() or 0)
                per_student[s.id] = int(count_prev)
            prev_present_by_month_map[f"{yr}-{mo:02d}"] = per_student

        # Get monthly attendance data if requested
        monthly_attendance_data = None
        view_month = request.args.get('view_month', selected_date.month, type=int)
        view_year = request.args.get('view_year', selected_date.year, type=int)
        
        if request.args.get('view') == 'monthly' or request.args.get('view_month') or request.args.get('view_year'):
            monthly_attendance_data = LecturerService.get_monthly_attendance_data(
                subject_id, lecturer_id, view_month, view_year
            )
        
        return render_template('lecturer/attendance.html', 
                             subject=subject, 
                             students=students,
                             selected_date=selected_date,
                             existing_attendance=existing_attendance,
                             monthly_summary=monthly_summary,
                             monthly_attendance_data=monthly_attendance_data,
                             prior_total_classes=prior_total_classes,
                             prev_present_map=prev_present_map,
                             prior_totals_map=prior_totals_map,
                             prev_present_by_month_map=prev_present_by_month_map)
    except Exception as e:
        flash(f'Error loading attendance: {str(e)}', 'error')
        return redirect(url_for('lecturer.subjects'))

@lecturer_bp.route('/subjects/<int:subject_id>/attendance/daily', methods=['POST'])
@login_required('lecturer')
def record_daily_attendance(subject_id):
    """Record daily attendance"""
    try:
        lecturer_id = session.get('user_id')
        attendance_date_str = request.form.get('attendance_date')
        
        if not attendance_date_str:
            flash('Attendance date is required', 'error')
            return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))
        
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
        
        # Build attendance data - exclude system fields
        attendance_data = {}
        
        for key, value in request.form.items():
            # Only process attendance fields that are not system fields
            if key.startswith('attendance_') and key != 'attendance_date' and value:
                try:
                    student_id_str = key.replace('attendance_', '')
                    # Make sure it's a valid integer (student ID)
                    if student_id_str.isdigit():
                        student_id = int(student_id_str)
                        if value in ['present', 'absent']:  # Validate attendance status
                            attendance_data[student_id] = value
                except (ValueError, TypeError):
                    continue
        
        if not attendance_data:
            flash('No attendance data provided', 'error')
            return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))
        
        success, message = LecturerService.record_daily_attendance(
            subject_id, lecturer_id, attendance_data, attendance_date
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
    except ValueError as ve:
        flash(f'Invalid date format: {str(ve)}', 'error')
    except Exception as e:
        flash(f'Error recording attendance: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.attendance_management', subject_id=subject_id, date=attendance_date_str))

@lecturer_bp.route('/subjects/<int:subject_id>/attendance/monthly/validate', methods=['POST'])
@login_required('lecturer')
def validate_monthly_attendance(subject_id):
    """Validate monthly attendance data via API"""
    try:
        lecturer_id = session.get('user_id')
        data = request.get_json()
        
        month = int(data.get('month'))
        year = int(data.get('year'))
        total_classes = int(data.get('total_classes', 0))
        student_id = data.get('student_id')
        attended_classes = data.get('attended_classes')
        
        from sqlalchemy import func
        from datetime import date as _date
        
        # Compute prior cumulative classes up to previous month
        prior_total_classes = (db.session.query(func.coalesce(func.sum(MonthlyAttendanceSummary.total_classes), 0))
            .filter(
                MonthlyAttendanceSummary.subject_id == subject_id,
                MonthlyAttendanceSummary.lecturer_id == lecturer_id,
                ((MonthlyAttendanceSummary.year < year) |
                 ((MonthlyAttendanceSummary.year == year) & (MonthlyAttendanceSummary.month < month)))
            ).scalar() or 0)
        
        # Classes actually conducted in the selected month
        month_classes = max(total_classes - prior_total_classes, 0)
        
        # Validation 1: Cumulative total classes rule
        if total_classes < prior_total_classes:
            return jsonify({
                'valid': False,
                'error_type': 'cumulative_total',
                'message': f'Total classes must be at least {prior_total_classes} (cumulative from previous months)',
                'min_value': prior_total_classes
            })
        
        # Validation 2: Student attendance range (if student_id and attended_classes provided)
        if student_id is not None and attended_classes is not None:
            # Previous cumulative presents from MonthlyStudentAttendance up to prior month
            from models.attendance import MonthlyStudentAttendance as MSA
            from sqlalchemy import func
            prev_present = (db.session.query(func.coalesce(func.sum(MSA.present_count), 0))
                .filter(
                    MSA.student_id == int(student_id),
                    MSA.subject_id == subject_id,
                    MSA.lecturer_id == lecturer_id,
                    ((MSA.year < year) | ((MSA.year == year) & (MSA.month < month)))
                ).scalar() or 0)
            
            min_allowed = max(prev_present, 0)
            max_allowed = prev_present + month_classes
            
            if attended_classes < min_allowed or attended_classes > max_allowed:
                return jsonify({
                    'valid': False,
                    'error_type': 'student_range',
                    'message': f'Attendance must be between {min_allowed} and {max_allowed}',
                    'min_value': min_allowed,
                    'max_value': max_allowed
                })
        
        return jsonify({
            'valid': True,
            'message': 'Validation passed'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error_type': 'server_error',
            'message': f'Validation error: {str(e)}'
        }), 500

@lecturer_bp.route('/subjects/<int:subject_id>/attendance/monthly', methods=['POST'])
@login_required('lecturer')
def record_monthly_attendance(subject_id):
    """Record monthly attendance for all students"""
    try:
        lecturer_id = session.get('user_id')
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))
        total_classes = int(request.form.get('total_classes'))
        
        # Build attendance data from form with server-side range validation
        attendance_data = {}
        from sqlalchemy import func
        from datetime import date as _date
        from models.attendance import MonthlyStudentAttendance as MSA
        # Compute prior cumulative classes up to previous month
        prior_total_classes = (db.session.query(func.coalesce(func.sum(MonthlyAttendanceSummary.total_classes), 0))
            .filter(
                MonthlyAttendanceSummary.subject_id == subject_id,
                MonthlyAttendanceSummary.lecturer_id == lecturer_id,
                ((MonthlyAttendanceSummary.year < year) |
                 ((MonthlyAttendanceSummary.year == year) & (MonthlyAttendanceSummary.month < month)))
            ).scalar() or 0)
        # Classes actually conducted in the selected month
        month_classes = max(total_classes - prior_total_classes, 0)
        # Cutoff for previous presents is first day of selected month
        prev_cutoff = _date(year, month, 1)
        # Build per-student previous presents map using MonthlyStudentAttendance sums
        students = LecturerService.get_subject_students(subject_id, lecturer_id)
        prev_present_map = {}
        for s in students:
            prev_present = (db.session.query(func.coalesce(func.sum(MSA.present_count), 0))
                .filter(
                    MSA.student_id == s.id,
                    MSA.subject_id == subject_id,
                    MSA.lecturer_id == lecturer_id,
                    ((MSA.year < year) | ((MSA.year == year) & (MSA.month < month)))
                ).scalar() or 0)
            prev_present_map[s.id] = int(prev_present)

        for key, value in request.form.items():
            if key.startswith('attended_') and value is not None and value != '':
                try:
                    student_id_str = key.replace('attended_', '')
                    student_id = int(student_id_str)
                    attended_classes = int(value)
                    # Determine allowed range for this student: [prev_presents, prev_presents + month_classes]
                    prev_presents = prev_present_map.get(student_id, 0)
                    min_allowed = max(prev_presents, 0)
                    max_allowed = prev_presents + month_classes
                    if attended_classes < min_allowed or attended_classes > max_allowed:
                        flash(f"Invalid attended value for student {student_id}. Allowed range: {min_allowed}-{max_allowed}.", 'error')
                        return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))
                    # Also cap by overall total cumulative to be safe
                    if attended_classes > total_classes:
                        flash(f"Attended cannot exceed total cumulative classes {total_classes}.", 'error')
                        return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))
                    attendance_data[student_id] = attended_classes
                except ValueError:
                    continue
        
        if not attendance_data:
            flash('No attendance data provided', 'error')
            return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))
        
        success, message = LecturerService.record_monthly_attendance(
            subject_id, lecturer_id, month, year, total_classes, attendance_data
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
    except Exception as e:
        flash(f'Error recording monthly attendance: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/attendance/summary', methods=['POST'])
@login_required('lecturer')
def record_monthly_summary(subject_id):
    """Record monthly attendance summary"""
    try:
        lecturer_id = session.get('user_id')
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))
        total_classes = int(request.form.get('total_classes'))
        
        success, message = LecturerService.record_monthly_summary(
            subject_id, lecturer_id, month, year, total_classes
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
    except Exception as e:
        flash(f'Error recording monthly summary: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.attendance_management', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/marks')
@login_required('lecturer')
def marks_management(subject_id):
    """Marks management for a subject"""
    try:
        lecturer_id = session.get('user_id')
        students = LecturerService.get_subject_students(subject_id, lecturer_id)
        subject = Subject.query.get_or_404(subject_id)
        
        # Get existing marks for students
        from models.marks import StudentMarks
        existing_marks = {}
        for student in students:
            marks = StudentMarks.query.filter_by(
                student_id=student.id,
                subject_id=subject_id
            ).all()
            existing_marks[student.id] = {mark.assessment_type: mark for mark in marks}
        
        return render_template('lecturer/marks.html', 
                             subject=subject, 
                             students=students,
                             existing_marks=existing_marks)
    except Exception as e:
        flash(f'Error loading marks: {str(e)}', 'error')
        return redirect(url_for('lecturer.subjects'))

@lecturer_bp.route('/subjects/<int:subject_id>/marks/add', methods=['POST'])
@login_required('lecturer')
def add_marks(subject_id):
    """Add marks for students"""
    try:
        lecturer_id = session.get('user_id')
        assessment_type = request.form.get('assessment_type')
        max_marks = float(request.form.get('max_marks'))
        
        # Build marks data
        marks_data = []
        for key, value in request.form.items():
            if key.startswith('marks_'):
                student_id = int(key.replace('marks_', ''))
                if value:  # Only process if marks are provided
                    marks_data.append({
                        'student_id': student_id,
                        'assessment_type': assessment_type,
                        'marks_obtained': float(value),
                        'max_marks': max_marks,
                        'assessment_date': date.today()
                    })
        
        if marks_data:
            success, message = LecturerService.add_marks(subject_id, lecturer_id, marks_data)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
        else:
            flash('No marks data provided', 'error')
            
    except Exception as e:
        flash(f'Error adding marks: {str(e)}', 'error')
    
    return redirect(url_for('lecturer.marks_management', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/reports')
@login_required('lecturer')
def subject_reports(subject_id):
    """View reports for a subject"""
    try:
        lecturer_id = session.get('user_id')
        subject = Subject.query.get_or_404(subject_id)
        
        # Generate attendance report
        attendance_report, att_message = LecturerService.generate_attendance_report(subject_id, lecturer_id)
        
        # Generate marks report
        marks_report_result, marks_message = LecturerService.generate_marks_report(subject_id, lecturer_id)
        
        # Extract marks report data and metadata
        marks_report = None
        has_internal1 = False
        has_internal2 = False
        
        if marks_report_result:
            marks_report = marks_report_result.get('report_data', [])
            has_internal1 = marks_report_result.get('has_internal1', False)
            has_internal2 = marks_report_result.get('has_internal2', False)
        
        return render_template('lecturer/reports.html', 
                             subject=subject,
                             attendance_report=attendance_report,
                             marks_report=marks_report,
                             has_internal1=has_internal1,
                             has_internal2=has_internal2)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return redirect(url_for('lecturer.subjects'))

# ---------------- PDF Export for Lecturer Reports ----------------
@lecturer_bp.route('/subjects/<int:subject_id>/reports/marks/pdf')
@login_required('lecturer')
def export_subject_marks_report_pdf(subject_id):
    try:
        lecturer_id = session.get('user_id')
        subject = Subject.query.get_or_404(subject_id)
        marks_report_result, _ = LecturerService.generate_marks_report(subject_id, lecturer_id)
        marks_report = marks_report_result.get('report_data', []) if marks_report_result else []
        pdf_bytes = ReportingService.generate_subject_marks_report_pdf(subject, marks_report)
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=marks_report_{subject.code}.pdf'
        return response
    except Exception as e:
        flash(f'Error exporting marks PDF: {str(e)}', 'error')
        return redirect(url_for('lecturer.subject_reports', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/reports/attendance/pdf')
@login_required('lecturer')
def export_subject_attendance_report_pdf(subject_id):
    try:
        lecturer_id = session.get('user_id')
        subject = Subject.query.get_or_404(subject_id)
        attendance_report, _ = LecturerService.generate_attendance_report(subject_id, lecturer_id)
        pdf_bytes = ReportingService.generate_subject_attendance_report_pdf(subject, attendance_report)
        from flask import make_response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{subject.code}.pdf'
        return response
    except Exception as e:
        flash(f'Error exporting attendance PDF: {str(e)}', 'error')
        return redirect(url_for('lecturer.subject_reports', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/reports/marks/excel')
@login_required('lecturer')
def export_subject_marks_report_excel(subject_id):
    try:
        lecturer_id = session.get('user_id')
        subject = Subject.query.get_or_404(subject_id)
        marks_report_result, _ = LecturerService.generate_marks_report(subject_id, lecturer_id)
        marks_report = marks_report_result.get('report_data', []) if marks_report_result else []
        excel_bytes = ReportingService.generate_subject_marks_report_excel(subject, marks_report)
        from flask import make_response
        response = make_response(excel_bytes)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=marks_report_{subject.code}.xlsx'
        return response
    except Exception as e:
        flash(f'Error exporting marks Excel: {str(e)}', 'error')
        return redirect(url_for('lecturer.subject_reports', subject_id=subject_id))

@lecturer_bp.route('/subjects/<int:subject_id>/reports/attendance/excel')
@login_required('lecturer')
def export_subject_attendance_report_excel(subject_id):
    try:
        lecturer_id = session.get('user_id')
        subject = Subject.query.get_or_404(subject_id)
        attendance_report, _ = LecturerService.generate_attendance_report(subject_id, lecturer_id)
        excel_bytes = ReportingService.generate_subject_attendance_report_excel(subject, attendance_report)
        from flask import make_response
        response = make_response(excel_bytes)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{subject.code}.xlsx'
        return response
    except Exception as e:
        flash(f'Error exporting attendance Excel: {str(e)}', 'error')
        return redirect(url_for('lecturer.subject_reports', subject_id=subject_id))

@lecturer_bp.route('/reports/attendance-shortage')
@login_required('lecturer')
def attendance_shortage_report():
    """Overall attendance shortage report"""
    try:
        lecturer_id = session.get('user_id')
        subjects = LecturerService.get_assigned_subjects(lecturer_id)
        
        # Get threshold from query parameter, default to 75%
        threshold = request.args.get('threshold', 75, type=int)
        
        shortage_data = []
        for subject in subjects:
            report, message = LecturerService.generate_attendance_report(subject.id, lecturer_id)
            if report:
                # Filter students based on custom threshold
                shortage_students = [r for r in report if r['attendance_percentage'] < threshold]
                if shortage_students:
                    shortage_data.append({
                        'subject': subject,
                        'shortage_students': shortage_students
                    })
        
        return render_template('lecturer/attendance_shortage.html', 
                             shortage_data=shortage_data, 
                             threshold=threshold)
    except Exception as e:
        flash(f'Error loading attendance shortage report: {str(e)}', 'error')
        return render_template('lecturer/attendance_shortage.html', 
                             shortage_data=[], 
                             threshold=75)

@lecturer_bp.route('/reports/marks-deficiency')
@login_required('lecturer')
def marks_deficiency_report():
    """Overall marks deficiency report"""
    try:
        lecturer_id = session.get('user_id')
        subjects = LecturerService.get_assigned_subjects(lecturer_id)
        
        # Get threshold from query parameter, default to 50%
        threshold = request.args.get('threshold', 50, type=int)
        
        deficiency_data = []
        for subject in subjects:
            report_result, message = LecturerService.generate_marks_report(subject.id, lecturer_id)
            if report_result:
                report = report_result.get('report_data', [])
                # Filter students based on custom threshold
                deficient_students = [r for r in report if r['overall_percentage'] < threshold]
                if deficient_students:
                    deficiency_data.append({
                        'subject': subject,
                        'deficient_students': deficient_students
                    })
        
        return render_template('lecturer/marks_deficiency.html', 
                             deficiency_data=deficiency_data, 
                             threshold=threshold)
    except Exception as e:
        flash(f'Error loading marks deficiency report: {str(e)}', 'error')
        return render_template('lecturer/marks_deficiency.html', 
                             deficiency_data=[], 
                             threshold=50)