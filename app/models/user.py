from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db, login_manager
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    edx_user_id = db.Column(db.String(255), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='user', lazy=True)
    shopping_cart = db.relationship('Cart', back_populates='user', uselist=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return str(self.id)

    def is_enrolled(self, course_id):
        """Check if user is enrolled in a specific course"""
        return any(enrollment.course_id == course_id for enrollment in self.enrollments)

    def get_enrolled_courses(self):
        """Get all courses the user is enrolled in"""
        return self.enrollments

    def __repr__(self):
        return f'<User {self.username}>' 