"""
Excel export service for Moulya College Management System
Handles Excel export for reports
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime

class ExcelExportService:
    """Service for exporting reports to Excel"""
    
    @staticmethod
    def create_workbook():
        """Create a new workbook with default styling"""
        wb = openpyxl.Workbook()
        return wb
    
    @staticmethod
    def style_header_row(ws, row_num, columns):
        """Apply styling to header row"""
        header_font = Font(bold=True, color="FFFFFF")
        # Change header background to black across all management exports
        header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col_num, header in enumerate(columns, 1):
            cell = ws.cell(row=row_num, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
    
    @staticmethod
    def auto_adjust_columns(ws):
        """Auto-adjust column widths"""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    @staticmethod
    def center_all_cells(ws):
        """Center align all populated cells in the given worksheet."""
        try:
            max_row = ws.max_row or 0
            max_col = ws.max_column or 0
            for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col):
                for cell in row:
                    if cell.value is not None:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
        except Exception:
            pass

    @staticmethod
    def set_number(cell, value, align_right=False):
        """Set an integer/float number with alignment preferences."""
        cell.value = value
        cell.alignment = Alignment(horizontal=("right" if align_right else "left"), vertical="center")
        return cell

    @staticmethod
    def set_percentage(cell, percent_0_to_100, align_left=True):
        """Write a numeric percentage (avoid text with green triangle)."""
        try:
            if percent_0_to_100 is None:
                cell.value = None
            else:
                # Convert 65.88 -> 0.6588 and apply percent format
                cell.value = float(percent_0_to_100) / 100.0
                cell.number_format = '0.00%'
        except Exception:
            cell.value = None
        cell.alignment = Alignment(horizontal=("left" if align_left else "right"), vertical="center")
        return cell
    
    @staticmethod
    def export_student_report(report_data):
        """Export individual student report to Excel in a single sheet mirroring the PDF layout."""
        try:
            wb = ExcelExportService.create_workbook()

            # Single sheet for the entire report
            ws = wb.active
            ws.title = "Student Report"

            student = report_data['student']

            # Student info table (Field | Value)
            student_headers = ['Field', 'Value']
            ExcelExportService.style_header_row(ws, 1, student_headers)

            ws.cell(row=2, column=1, value="Name")
            ws.cell(row=2, column=2, value=student['name'])
            ws.cell(row=3, column=1, value="Roll Number")
            ws.cell(row=3, column=2, value=student['roll_number'])
            ws.cell(row=4, column=1, value="Course")
            ws.cell(row=4, column=2, value=student.get('course_display') or student.get('course'))
            row = 5
            if student.get('section'):
                ws.cell(row=row, column=1, value="Section")
                ws.cell(row=row, column=2, value=str(student.get('section')).upper())
                row += 1
            ws.cell(row=row, column=1, value="Academic Year")
            ws.cell(row=row, column=2, value=student['academic_year'])
            row += 1
            ws.cell(row=row, column=1, value="Current Semester")
            ws.cell(row=row, column=2, value=student['current_semester'])

            # Gap
            row += 2

            # Marks Report section
            ws.cell(row=row, column=1, value="Marks Report").font = Font(bold=True)
            row += 1
            marks_headers = ['Subject', 'Code', 'Assessment', 'Marks', 'Max', 'Percent', 'Grade', 'Status']
            ExcelExportService.style_header_row(ws, row, marks_headers)
            row += 1

            marks_row_count = 0
            # Sort subjects by name/code ascending for consistency
            subjects_sorted_for_marks = sorted(
                report_data.get('subjects', []),
                key=lambda s: ((s.get('subject_name') or '').upper(), (s.get('subject_code') or '').upper())
            )
            for subject in subjects_sorted_for_marks:
                for mark in subject.get('marks', []):
                    ws.cell(row=row, column=1, value=subject.get('subject_name'))
                    ws.cell(row=row, column=2, value=subject.get('subject_code'))
                    ws.cell(row=row, column=3, value=mark.get('assessment_type'))
                    ExcelExportService.set_number(ws.cell(row=row, column=4), mark.get('marks_obtained'), align_right=True)
                    ExcelExportService.set_number(ws.cell(row=row, column=5), mark.get('max_marks'), align_right=True)
                    ExcelExportService.set_percentage(ws.cell(row=row, column=6), mark.get('percentage'), align_left=True)
                    ws.cell(row=row, column=7, value=mark.get('grade'))
                    ws.cell(row=row, column=8, value=mark.get('performance_status'))
                    row += 1
                    marks_row_count += 1
            if marks_row_count == 0:
                ws.cell(row=row, column=1, value="No data")
                row += 1

            # Gap
            row += 2

            # Attendance Report section
            ws.cell(row=row, column=1, value="Attendance Report").font = Font(bold=True)
            row += 1
            attendance_headers = ['Subject', 'Code', 'Total', 'Present', 'Absent', 'Percent', 'Status']
            ExcelExportService.style_header_row(ws, row, attendance_headers)
            row += 1

            att_row_count = 0
            subjects_sorted_for_att = sorted(
                report_data.get('subjects', []),
                key=lambda s: ((s.get('subject_name') or '').upper(), (s.get('subject_code') or '').upper())
            )
            for subject in subjects_sorted_for_att:
                attendance = subject.get('attendance', {})
                ws.cell(row=row, column=1, value=subject.get('subject_name'))
                ws.cell(row=row, column=2, value=subject.get('subject_code'))
                ExcelExportService.set_number(ws.cell(row=row, column=3), attendance.get('total_classes'), align_right=True)
                ExcelExportService.set_number(ws.cell(row=row, column=4), attendance.get('present_classes'), align_right=True)
                ExcelExportService.set_number(ws.cell(row=row, column=5), attendance.get('absent_classes'), align_right=True)
                ExcelExportService.set_percentage(ws.cell(row=row, column=6), attendance.get('attendance_percentage'), align_left=True)
                status = "Good" if (attendance.get('attendance_percentage') or 0) >= 75 else (
                    "Poor" if (attendance.get('attendance_percentage') or 0) < 50 else "Average")
                ws.cell(row=row, column=7, value=status)
                row += 1
                att_row_count += 1
            if att_row_count == 0:
                ws.cell(row=row, column=1, value="No data")
                row += 1

            # Center everything and auto-adjust columns
            ExcelExportService.center_all_cells(ws)
            ExcelExportService.auto_adjust_columns(ws)

            return wb

        except Exception as e:
            print(f"Error exporting student report: {e}")
            return None
    
    @staticmethod
    def export_class_marks_report(report_data):
        """Export class marks report to Excel with clean format (no college headers)"""
        try:
            wb = ExcelExportService.create_workbook()
            ws = wb.active
            ws.title = "Class Marks Report"
            
            # Clean subject info table
            subject = report_data['subject']
            subject_headers = ['Field', 'Value']
            ExcelExportService.style_header_row(ws, 1, subject_headers)
            
            ws.cell(row=2, column=1, value="Subject")
            ws.cell(row=2, column=2, value=f"{subject['name']} ({subject['code']})")
            ws.cell(row=3, column=1, value="Course")
            ws.cell(row=3, column=2, value=subject.get('course_display') or subject.get('course'))
            ws.cell(row=4, column=1, value="Year/Semester")
            ws.cell(row=4, column=2, value=f"{subject['year']}/{subject['semester']}")
            # Optional section line
            if subject.get('section'):
                ws.cell(row=5, column=1, value="Section")
                ws.cell(row=5, column=2, value=str(subject.get('section')).upper())
                next_row = 6
            else:
                next_row = 5
            if subject.get('lecturers'):
                ws.cell(row=next_row, column=1, value="Faculty")
                ws.cell(row=next_row, column=2, value=", ".join(subject.get('lecturers') or []))
            
            if report_data['assessment_type']:
                ws.cell(row=5, column=1, value="Assessment Type")
                ws.cell(row=5, column=2, value=report_data['assessment_type'])
            
            # Clean statistics table
            stats = report_data['statistics']
            stats_headers = ['Statistic', 'Value']
            ExcelExportService.style_header_row(ws, next_row + 2, stats_headers)
            
            base = next_row + 3
            ws.cell(row=base + 0, column=1, value="Total Students")
            ws.cell(row=base + 0, column=2, value=stats['total_students'])
            ws.cell(row=base + 1, column=1, value="Class Average")
            ExcelExportService.set_percentage(ws.cell(row=base + 1, column=2), stats['class_average'], align_left=True)
            ws.cell(row=base + 2, column=1, value="Highest Score")
            ExcelExportService.set_percentage(ws.cell(row=base + 2, column=2), stats['highest_score'], align_left=True)
            ws.cell(row=base + 3, column=1, value="Lowest Score")
            ExcelExportService.set_percentage(ws.cell(row=base + 3, column=2), stats['lowest_score'], align_left=True)
            ws.cell(row=base + 4, column=1, value="Passing Students")
            ws.cell(row=base + 4, column=2, value=stats['passing_students'])
            ws.cell(row=base + 5, column=1, value="Failing Students")
            ws.cell(row=base + 5, column=2, value=stats['failing_students'])
            
            # Student marks table
            headers = ['Roll Number', 'Student Name', 'Assessment Type', 'Marks Obtained', 
                      'Max Marks', 'Percentage', 'Grade', 'Status']
            ExcelExportService.style_header_row(ws, base + 7, headers)
            
            row = base + 8
            # Sort by roll number then name
            student_marks_sorted = sorted(
                report_data['student_marks'],
                key=lambda sm: ((sm.get('roll_number') or sm.get('student', {}).roll_number if isinstance(sm.get('student'), object) else '') or '').upper()
            )
            for student_data in student_marks_sorted:
                student = student_data['student']
                for mark in student_data['marks']:
                    ws.cell(row=row, column=1, value=student.roll_number)
                    ws.cell(row=row, column=2, value=student.name)
                    ws.cell(row=row, column=3, value=mark['assessment_type'])
                    ws.cell(row=row, column=4, value=mark['marks_obtained'])
                    ws.cell(row=row, column=5, value=mark['max_marks'])
                    ExcelExportService.set_percentage(ws.cell(row=row, column=6), mark['percentage'], align_left=True)
                    ws.cell(row=row, column=7, value=mark['grade'])
                    ws.cell(row=row, column=8, value=mark['performance_status'])
                    row += 1
            
            ExcelExportService.center_all_cells(ws)
            ExcelExportService.auto_adjust_columns(ws)
            return wb
            
        except Exception as e:
            print(f"Error exporting class marks report: {e}")
            return None
    
    @staticmethod
    def export_class_attendance_report(report_data):
        """Export class attendance report to Excel with clean format (no college headers)"""
        try:
            wb = ExcelExportService.create_workbook()
            ws = wb.active
            ws.title = "Class Attendance Report"
            
            # Clean subject info table
            subject = report_data['subject']
            subject_headers = ['Field', 'Value']
            ExcelExportService.style_header_row(ws, 1, subject_headers)
            
            ws.cell(row=2, column=1, value="Subject")
            ws.cell(row=2, column=2, value=f"{subject['name']} ({subject['code']})")
            ws.cell(row=3, column=1, value="Course")
            course_line = subject.get('course_display') or subject.get('course') or ''
            if subject.get('section'):
                course_line += f" - Section {str(subject['section']).upper()}"
            ws.cell(row=3, column=2, value=course_line)
            ws.cell(row=4, column=1, value="Year/Semester")
            ws.cell(row=4, column=2, value=f"{subject['year']}/{subject['semester']}")
            ws.cell(row=5, column=1, value="Period")
            ws.cell(row=5, column=2, value=f"{report_data['month']}/{report_data['year']}")
            # Optional section line
            if subject.get('section'):
                ws.cell(row=6, column=1, value="Section")
                ws.cell(row=6, column=2, value=str(subject.get('section')).upper())
                next_row2 = 7
            else:
                next_row2 = 6
            if subject.get('lecturers'):
                ws.cell(row=next_row2, column=1, value="Faculty")
                ws.cell(row=next_row2, column=2, value=", ".join(subject.get('lecturers') or []))
            
            # Clean statistics table
            stats = report_data['statistics']
            stats_headers = ['Statistic', 'Value']
            ExcelExportService.style_header_row(ws, next_row2 + 2, stats_headers)
            
            base2 = next_row2 + 3
            ws.cell(row=base2 + 0, column=1, value="Total Students")
            ws.cell(row=base2 + 0, column=2, value=stats['total_students'])
            ws.cell(row=base2 + 1, column=1, value="Total Classes Conducted")
            ws.cell(row=base2 + 1, column=2, value=stats['total_classes_conducted'])
            ws.cell(row=base2 + 2, column=1, value="Class Average Attendance")
            ExcelExportService.set_percentage(ws.cell(row=base2 + 2, column=2), stats['class_average_attendance'], align_left=True)
            ws.cell(row=base2 + 3, column=1, value="Good Attendance (≥75%)")
            ws.cell(row=base2 + 3, column=2, value=stats['students_with_good_attendance'])
            ws.cell(row=base2 + 4, column=1, value="Poor Attendance (<50%)")
            ws.cell(row=base2 + 4, column=2, value=stats['students_with_poor_attendance'])
            
            # Student attendance table
            headers = ['Roll Number', 'Student Name', 'Total Classes', 'Present', 
                      'Absent', 'Attendance %', 'Status']
            ExcelExportService.style_header_row(ws, base2 + 6, headers)
            
            row = base2 + 7
            # Ensure ascending by roll then name
            sa_sorted = sorted(
                report_data['student_attendance'],
                key=lambda s: ((s.get('roll_number') or '').upper(), (s.get('student_name') or '').upper())
            )
            for student in sa_sorted:
                ws.cell(row=row, column=1, value=student['roll_number'])
                ws.cell(row=row, column=2, value=student['student_name'])
                ExcelExportService.set_number(ws.cell(row=row, column=3), student['total_classes'], align_right=True)
                ExcelExportService.set_number(ws.cell(row=row, column=4), student['present_classes'], align_right=True)
                ExcelExportService.set_number(ws.cell(row=row, column=5), student['absent_classes'], align_right=True)
                ExcelExportService.set_percentage(ws.cell(row=row, column=6), student['attendance_percentage'], align_left=True)
                ws.cell(row=row, column=7, value=student['status'])
                row += 1
            
            ExcelExportService.center_all_cells(ws)
            ExcelExportService.auto_adjust_columns(ws)
            return wb
            
        except Exception as e:
            print(f"Error exporting class attendance report: {e}")
            return None
    
    @staticmethod
    def export_course_overview_report(report_data):
        """Export course overview report to Excel with clean format (no college headers)"""
        try:
            wb = ExcelExportService.create_workbook()
            ws = wb.active
            ws.title = "Course Overview"
            
            # Clean course info table
            course = report_data['course']
            course_headers = ['Field', 'Value']
            ExcelExportService.style_header_row(ws, 1, course_headers)
            
            ws.cell(row=2, column=1, value="Course")
            ws.cell(row=2, column=2, value=f"{course['name']} ({course['code']})")
            ws.cell(row=3, column=1, value="Duration")
            ws.cell(row=3, column=2, value=f"{course['duration_years']} years ({course['total_semesters']} semesters)")
            ws.cell(row=4, column=1, value="Total Students")
            ws.cell(row=4, column=2, value=report_data['total_students'])
            ws.cell(row=5, column=1, value="Total Subjects")
            ws.cell(row=5, column=2, value=report_data['total_subjects'])
            
            # Subject-wise report
            headers = ['Subject Code', 'Subject Name', 'Year', 'Semester', 'Enrolled Students',
                      'Total Assessments', 'Average Marks %', 'Passing Rate %', 'Average Attendance %']
            ExcelExportService.style_header_row(ws, 7, headers)
            
            row = 8
            # Sort subjects for overview export
            subjects_sorted = sorted(
                report_data['subjects'],
                key=lambda s: ((s.get('subject_code') or '').upper(), (s.get('subject_name') or '').upper())
            )
            for subject in subjects_sorted:
                ws.cell(row=row, column=1, value=subject['subject_code'])
                ws.cell(row=row, column=2, value=subject['subject_name'])
                ws.cell(row=row, column=3, value=subject['year'])
                ws.cell(row=row, column=4, value=subject['semester'])
                ws.cell(row=row, column=5, value=subject['enrolled_students'])
                ws.cell(row=row, column=6, value=subject['marks_statistics']['total_assessments'])
                ExcelExportService.set_percentage(ws.cell(row=row, column=7), subject['marks_statistics']['average_marks'], align_left=True)
                ExcelExportService.set_percentage(ws.cell(row=row, column=8), subject['marks_statistics']['passing_rate'], align_left=True)
                ExcelExportService.set_percentage(ws.cell(row=row, column=9), subject['attendance_statistics']['average_attendance'], align_left=True)
                row += 1
            
            ExcelExportService.center_all_cells(ws)
            ExcelExportService.auto_adjust_columns(ws)
            return wb
            
        except Exception as e:
            print(f"Error exporting course overview report: {e}")
            return None
    
    @staticmethod
    def workbook_to_bytes(workbook):
        """Convert workbook to bytes for download"""
        try:
            output = BytesIO()
            workbook.save(output)
            output.seek(0)
            return output.getvalue()
        except Exception as e:
            print(f"Error converting workbook to bytes: {e}")
            return None