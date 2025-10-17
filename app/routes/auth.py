from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from ..models.user import User
from .. import db
import re
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

def validate_username(username):
    """Validate username format and requirements"""
    if not username or len(username) < 2 or len(username) > 30:
        return "Username must be between 2 and 30 characters long."
    if not re.match(r'^[\w.-]+$', username):
        return "Username can only contain letters, numbers, dots, and underscores."
    return None

def validate_email(email):
    """Validate email format"""
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return "Please enter a valid email address."
    return None

def validate_password(password):
    """Validate password requirements"""
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return "Password must contain at least one number."
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('auth/login.html')
        
        try:
            # Check local database only
            user = User.query.filter_by(email=email).first()
            
            if not user:
                flash('No account found with this email address', 'error')
                return render_template('auth/login.html')
            
            # Check local password
            if not user.check_password(password):
                flash('Invalid password', 'error')
                return render_template('auth/login.html')
            
            # If we get here, authentication succeeded
            login_user(user, remember=True)
            next_page = request.args.get('next')
            
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
                
            return redirect(next_page)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get and clean form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        country = request.form.get('country', '')
        level_of_education = request.form.get('level_of_education', '')
        gender = request.form.get('gender', '')
        honor_code = request.form.get('honor_code') == 'on'
        marketing_emails_opt_in = request.form.get('marketing_emails_opt_in') == 'on'
        
        # Log the received data for debugging
        logger.info(f"Received registration data - Username: {username}, Email: {email}, Name: {name}")
        
        # Check if username or email already exists in our database
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        try:
            # Import OpenEdxAPI only for registration
            from ..utils.edx_api import OpenEdxAPI
            edx_api = OpenEdxAPI()
            
            # Log the data being sent to OpenEDX
            logger.info(f"Sending to OpenEDX - Username: {username}, Email: {email}, Name: {name}")
            
            edx_user, error_message, edx_username = edx_api.create_user(
                username=username,
                email=email,
                password=password,
                name=name,
                country=country,
                level_of_education=level_of_education,
                gender=gender,
                honor_code=honor_code,
                marketing_emails_opt_in=marketing_emails_opt_in
            )
            
            if edx_user:
                # Create user in our store
                user = User(
                    username=edx_username,
                    email=email,
                    edx_user_id=edx_user.get('id'),
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                # Log successful registration
                logger.info(f"Successfully created user: {username}")
                
                # Log the user in
                login_user(user)
                
                flash('Account created successfully! Welcome to eSkills.', 'success')
                return redirect(url_for('main.index'))
            
            else:
                flash(f'Failed to create account in OpenEdX {error_message}', 'error')
                return render_template('auth/register.html')
                
        except Exception as e:
            # Log the error
            logger.error(f"Error during registration: {str(e)}")
            
            # Rollback database changes if any
            db.session.rollback()
            
            # Flash appropriate error message
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index')) 