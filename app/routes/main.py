from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from flask_login import current_user, login_required
import logging
from datetime import datetime
from app.models.user import User
from app.models.course import Course
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    try:
        # Import OpenEdxAPI only when needed
        from ..utils.edx_api import OpenEdxAPI
        api = OpenEdxAPI()
        
        # Get featured courses from OpenEdX API
        current_app.logger.info("Starting to fetch courses from OpenEdX API")
        response = api.get_courses()
        current_app.logger.info(f"OpenEdX API response type: {type(response)}")
        current_app.logger.info(f"OpenEdX API response: {response}")
        
        # Always get courses regardless of login status
        courses = response.get('results', []) if response else []
        current_app.logger.info(f"Successfully fetched {len(courses)} courses")
        
        # Get user's enrolled courses if logged in
        enrolled_courses = []
        if current_user.is_authenticated:
            current_app.logger.info(f"User {current_user.id} is authenticated, fetching enrolled courses")
            enrolled_courses = current_user.get_enrolled_courses()
            current_app.logger.info(f"User {current_user.id} has {len(enrolled_courses)} enrolled courses")
            
            # Log enrolled course IDs
            for course in enrolled_courses:
                current_app.logger.info(f"Enrolled course ID: {course.course_id}")
        
        # Create a set of enrolled course IDs for faster lookup
        enrolled_course_ids = {course.course_id for course in enrolled_courses}
        current_app.logger.info(f"Enrolled course IDs set: {enrolled_course_ids}")
        
        # Add enrollment status to each course
        for course in courses:
            course_id = course.get('id')
            current_app.logger.info(f"Checking course ID: {course_id}")
            course['is_enrolled'] = course_id in enrolled_course_ids
            current_app.logger.info(f"Course {course_id} enrollment status: {course['is_enrolled']}")
            
        return render_template('main/index.html',
                             courses=courses,
                             enrolled_courses=enrolled_courses)
                             
    except Exception as e:
        current_app.logger.error(f"Error loading homepage: {str(e)}")
        return render_template('main/index.html',
                             courses=[],
                             enrolled_courses=[])

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('main/contact.html')

@main_bp.route('/enroll/<course_id>', methods=['POST'])
@login_required
def enroll_course(course_id):
    try:
        # Check if user is already enrolled
        if course_id in [course.id for course in current_user.enrolled_courses]:
            flash('You are already enrolled in this course.', 'info')
            return redirect(url_for('main.home'))

        # Add course to user's enrolled courses
        course = Course.query.get_or_404(course_id)
        current_user.enrolled_courses.append(course)
        db.session.commit()

        flash('Successfully enrolled in the course!', 'success')
        return redirect(url_for('main.home'))
    except Exception as e:
        current_app.logger.error(f"Error enrolling in course: {str(e)}")
        flash('An error occurred while enrolling in the course.', 'error')
        return redirect(url_for('main.home'))

@main_bp.route('/unenroll/<course_id>', methods=['POST'])
@login_required
def unenroll_course(course_id):
    try:
        # Remove course from user's enrolled courses
        course = Course.query.get_or_404(course_id)
        if course in current_user.enrolled_courses:
            current_user.enrolled_courses.remove(course)
            db.session.commit()
            flash('Successfully unenrolled from the course.', 'success')
        else:
            flash('You are not enrolled in this course.', 'info')
    except Exception as e:
        current_app.logger.error(f"Error unenrolling from course: {str(e)}")
        flash('An error occurred while unenrolling from the course.', 'error')
    
    return redirect(url_for('main.home')) 