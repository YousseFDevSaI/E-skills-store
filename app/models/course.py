from .. import db
from datetime import datetime

class Course(db.Model):
    """Course model for storing course information"""
    __tablename__ = 'courses'
    
    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    org = db.Column(db.String(255))
    number = db.Column(db.String(255))
    short_description = db.Column(db.Text)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    enrollment_start = db.Column(db.DateTime)
    enrollment_end = db.Column(db.DateTime)
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    
    def __repr__(self):
        return f'<Course {self.name}>'
    
    def to_dict(self):
        """Convert course to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'org': self.org,
            'number': self.number,
            'short_description': self.short_description,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'enrollment_start': self.enrollment_start.isoformat() if self.enrollment_start else None,
            'enrollment_end': self.enrollment_end.isoformat() if self.enrollment_end else None,
            'price': self.price,
            'currency': self.currency,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 