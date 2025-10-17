from .. import db
from datetime import datetime

class Enrollment(db.Model):
    """Enrollment model for tracking user course enrollments"""
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(255), db.ForeignKey('courses.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    mode = db.Column(db.String(32), default='audit')  # audit, verified, professional
    status = db.Column(db.String(32), default='active')  # active, completed, dropped
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Enrollment {self.user_id} - {self.course_id}>'
    
    def to_dict(self):
        """Convert enrollment to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'enrollment_date': self.enrollment_date.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'is_active': self.is_active,
            'mode': self.mode,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 