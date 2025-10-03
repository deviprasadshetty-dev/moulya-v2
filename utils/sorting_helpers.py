"""
Sorting helper utilities for Moulya College Management System
Provides consistent sorting logic for lecturers and students
"""

import re

class SortingHelpers:
    """Helper class for sorting operations"""
    
    @staticmethod
    def get_lecturer_sort_key(lecturer):
        """
        Get sort key for lecturer based on ID priority
        Priority: BBHCF001 (first), BBHCFN001/BBHCFN01 (second), then alphabetical
        """
        lecturer_id = lecturer.lecturer_id.upper()
        
        # First priority: BBHCF001 format (exact match)
        if lecturer_id == 'BBHCF001':
            return (0, lecturer_id)
        
        # Second priority: BBHCFN001 or BBHCFN01 format
        if lecturer_id.startswith('BBHCFN') and (lecturer_id.endswith('001') or lecturer_id.endswith('01')):
            return (1, lecturer_id)
        
        # Third priority: Other BBHCF patterns
        if lecturer_id.startswith('BBHCF'):
            return (2, lecturer_id)
        
        # Fourth priority: Other patterns
        return (3, lecturer_id)
    
    @staticmethod
    def get_student_sort_key(student):
        """
        Get sort key for student based on course and roll number
        Priority: I BCA courses first, then other courses, then by roll number
        """
        course_name = student.course.name if student.course else ""
        course_priority = 0
        
        # Priority order for courses
        if "I BCA" in course_name.upper():
            course_priority = 1
        elif "BCA" in course_name.upper():
            course_priority = 2
        elif "BCOM" in course_name.upper():
            course_priority = 3
        elif "BBA" in course_name.upper():
            course_priority = 4
        else:
            course_priority = 5
        
        # Then sort by roll number within course
        roll_number = student.roll_number.upper()
        
        # Extract numeric part for proper sorting
        numeric_match = re.search(r'(\d+)', roll_number)
        if numeric_match:
            numeric_part = int(numeric_match.group(1))
        else:
            numeric_part = 999999  # Put non-numeric at end
        
        return (course_priority, course_name, numeric_part, roll_number)
    
    @staticmethod
    def sort_lecturers(lecturers):
        """Sort lecturers using the standard sorting logic"""
        return sorted(lecturers, key=SortingHelpers.get_lecturer_sort_key)
    
    @staticmethod
    def sort_students(students):
        """Sort students using the standard sorting logic"""
        return sorted(students, key=SortingHelpers.get_student_sort_key)
