from app import create_app, db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.cart import Cart, CartItem

app = create_app()

with app.app_context():
    # Drop all tables
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    print("Database initialized successfully!") 