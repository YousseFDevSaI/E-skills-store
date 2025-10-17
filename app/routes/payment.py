from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
import stripe

from app.models.user import User
from app.utils.edx_api import OpenEdxAPI
from ..models.cart import Cart
from ..models.course import Course
from .. import db
import logging

logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/checkout')
@login_required
def checkout():
    """Display the checkout page"""
    try:
        # Get cart items
        cart = current_user.shopping_cart
        if not cart or not cart.items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('cart.view'))
            
        # Calculate total
        total = sum(item.price for item in cart.items if item.price is not None)
        
        return render_template('payment/checkout.html',
                             cart=cart,
                             total=total,
                             stripe_public_key=current_app.config['STRIPE_PUBLIC_KEY'])
                             
    except Exception as e:
        logger.error(f"Error in checkout: {str(e)}")
        flash('Error loading checkout page', 'error')
        return redirect(url_for('cart.view'))

@payment_bp.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    """Create a Stripe payment intent"""
    try:
        # Get cart items
        cart = current_user.shopping_cart
        if not cart or not cart.items:
            return jsonify({'error': 'Cart is empty'}), 400
            
        # Calculate total
        total = sum(item.price for item in cart.items if item.price is not None)
        
        # Initialize Stripe
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),  # Convert to cents
            currency=current_app.config['STRIPE_CURRENCY'],
            metadata={
                'user_id': current_user.id,
                'cart_id': cart.id
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks"""
    try:
        # Get the webhook secret
        webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
        
        # Get the webhook data
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        edx_api = OpenEdxAPI()
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            return jsonify({'error': 'Invalid signature'}), 400
            
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            # Get cart and user from metadata
            cart_id = payment_intent['metadata']['cart_id']
            user_id = payment_intent['metadata']['user_id']
            user = User.query.get(user_id)
            # Get cart
            cart = Cart.query.get(cart_id)
            if not cart:
                logger.error(f"Cart not found: {cart_id}")
                return jsonify({'error': 'Cart not found'}), 404
                
            # Enroll user in courses
            logger.info(f"Enrolling user in courses: {cart.items}")
            
            for item in cart.items:
                # Enroll user in course
                
                success, error = edx_api.enroll(
                    user.username,
                    item.course_id,
                    item.mode
                )
                if not success:
                    logger.error(f"Error enrolling user in course: {error}")
                    
            # Clear cart
            cart.clear()
            db.session.commit()
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/success')
@login_required
def success():
    """Display success page after payment"""
    return render_template('payment/success.html') 