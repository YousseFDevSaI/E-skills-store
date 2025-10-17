from .. import db
from datetime import datetime

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id', name='fk_cart_items_cart_id'), nullable=False)
    course_id = db.Column(db.String(255), db.ForeignKey('courses.id', name='fk_cart_items_course_id'), nullable=False)
    mode = db.Column(db.String(32), nullable=False, default='audit')
    price = db.Column(db.Float)
    currency = db.Column(db.String(3), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cart = db.relationship('Cart', backref=db.backref('items', lazy=True))
    course = db.Column(db.PickleType)

class Cart(db.Model):
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_carts_user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='shopping_cart')
    
    def add_item(self, course_id, course, mode='audit', price=None, currency='USD'):
        """Add a course to the cart"""
        if not self.has_item(course_id):
            item = CartItem(
                cart_id=self.id,
                course_id=course_id,
                mode=mode,
                price=price,
                currency=currency,
                course=course
            )
            db.session.add(item)
            db.session.commit()
            return True
        return False
    
    def remove_item(self, course_id):
        """Remove a course from the cart"""
        item = CartItem.query.filter_by(cart_id=self.id, course_id=course_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return True
        return False
    
    def has_item(self, course_id):
        """Check if a course is in the cart"""
        return CartItem.query.filter_by(cart_id=self.id, course_id=course_id).first() is not None
    
    def clear(self):
        """Clear all items from the cart"""
        CartItem.query.filter_by(cart_id=self.id).delete()
        db.session.commit()
    
    @property
    def total(self):
        """Calculate the total price of all items in the cart"""
        return sum(item.price for item in self.items if item.price is not None) 