from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user

from app.utils.edx_api import OpenEdxAPI
from ..models.cart import Cart, CartItem
from ..models.course import Course
from .. import db
import logging

logger = logging.getLogger(__name__)

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/')
@login_required
def view():
    """View cart contents"""
    try:
        # Get or create cart
        cart = current_user.shopping_cart
        if not cart:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.commit()
            
        return render_template('cart/view.html', cart=cart)
        
    except Exception as e:
        logger.error(f"Error viewing cart: {str(e)}")
        flash('Error loading cart', 'error')
        return redirect(url_for('courses.index'))

@cart_bp.route('/add/<course_id>', methods=['POST'])
@login_required
def add(course_id):
    """Add a course to cart"""
    try:
        # Get or create cart
        cart = current_user.shopping_cart
        if not cart:
            cart = Cart(user_id=current_user.id)
            db.session.add(cart)
            db.session.commit()
            
        # Check if course exists
        api = OpenEdxAPI()
        
        # First try the catalog API
        course = api.get_course_details(course_id)
        logger.info(f"THIS IS THE COURSE FROM CART{course}")
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('courses.index'))
            
        # Get course mode and price
        mode = course.get('mode', 'audit')
        price = course.get('price') if course.get('price') > 0 else None
        currency = course.get('currency') if course.get('currency') else 'USD'
            
        # Add to cart
        logger.info(f"Adding course to cart: {course_id} with mode: {mode} and price: {price} and currency: {currency}")
        if cart.add_item(course_id, mode=mode, price=price, currency=currency, course=course):
            flash('Course added to cart', 'success')
        else:
            flash('Course already in cart', 'info')
            
        return redirect(url_for('cart.view'))
        
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        flash('Error adding course to cart', 'error')
        return redirect(url_for('courses.index'))

@cart_bp.route('/remove/<course_id>', methods=['POST'])
@login_required
def remove(course_id):
    """Remove a course from cart"""
    try:
        cart = current_user.shopping_cart
        if not cart:
            flash('Cart not found', 'error')
            return redirect(url_for('cart.view'))
            
        if cart.remove_item(course_id):
            flash('Course removed from cart', 'success')
        else:
            flash('Course not in cart', 'error')
            
        return redirect(url_for('cart.view'))
        
    except Exception as e:
        logger.error(f"Error removing from cart: {str(e)}")
        flash('Error removing course from cart', 'error')
        return redirect(url_for('cart.view'))

@cart_bp.route('/clear', methods=['POST'])
@login_required
def clear():
    """Clear all items from cart"""
    try:
        cart = current_user.shopping_cart
        if not cart:
            flash('Cart not found', 'error')
            return redirect(url_for('cart.view'))
            
        cart.clear()
        flash('Cart cleared', 'success')
        return redirect(url_for('cart.view'))
        
    except Exception as e:
        logger.error(f"Error clearing cart: {str(e)}")
        flash('Error clearing cart', 'error')
        return redirect(url_for('cart.view'))

@cart_bp.route('/checkout')
@login_required
def checkout():
    """Proceed to checkout"""
    try:
        cart = current_user.shopping_cart
        if not cart or not cart.items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('cart.view'))
            
        return redirect(url_for('payment.checkout'))
        
    except Exception as e:
        logger.error(f"Error proceeding to checkout: {str(e)}")
        flash('Error proceeding to checkout', 'error')
        return redirect(url_for('cart.view')) 