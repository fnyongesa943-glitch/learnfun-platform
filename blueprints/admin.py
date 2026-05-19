from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Payment, DigitalProduct
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ADMIN_PIN = '1234'


@admin_bp.route('/')
def login():
    if session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
    pin_param = request.args.get('pin', '')
    if pin_param == ADMIN_PIN:
        session['is_admin'] = True
        return redirect(url_for('admin.dashboard'))
    return render_template('admin_login.html')


@admin_bp.route('/login', methods=['POST'])
def check_pin():
    pin = request.form.get('pin', '').strip()
    if pin == ADMIN_PIN:
        session['is_admin'] = True
        flash('Welcome to the Admin Dashboard!', 'success')
        return redirect(url_for('admin.dashboard'))
    flash('Wrong PIN!', 'error')
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))

    users = User.query.order_by(User.created_at.desc()).all()
    payments = Payment.query.order_by(Payment.timestamp.desc()).limit(50).all()
    products = DigitalProduct.query.all()

    total_users = len(users)
    premium_users = sum(1 for u in users if u.is_premium)
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='success').scalar() or 0
    total_payments = Payment.query.filter_by(status='success').count()

    now = datetime.utcnow()
    expired_users = User.query.filter(
        User.is_premium == True,
        User.subscription_expiry < now
    ).count()

    return render_template('admin_dashboard.html',
                           users=users,
                           payments=payments,
                           products=products,
                           total_users=total_users,
                           premium_users=premium_users,
                           total_revenue=total_revenue,
                           total_payments=total_payments,
                           expired_users=expired_users)


@admin_bp.route('/toggle-premium/<int:user_id>')
def toggle_premium(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    user = User.query.get_or_404(user_id)
    user.is_premium = not user.is_premium
    if user.is_premium:
        user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
    else:
        user.subscription_expiry = None
    db.session.commit()
    flash(f"{user.username} premium set to {user.is_premium}", 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/products')
def manage_products():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    products = DigitalProduct.query.order_by(DigitalProduct.created_at.desc()).all()
    return render_template('admin_products.html', products=products)


@admin_bp.route('/products/add', methods=['POST'])
def add_product():
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    name = request.form.get('name', '').strip()
    price = request.form.get('price', '0').strip()
    description = request.form.get('description', '').strip()
    emoji = request.form.get('emoji', '📄').strip()
    category = request.form.get('category', 'worksheet').strip()

    if not name or not price:
        flash('Name and price required', 'error')
        return redirect(url_for('admin.manage_products'))

    product = DigitalProduct(
        name=name,
        price=int(price),
        description=description,
        emoji=emoji,
        category=category
    )
    db.session.add(product)
    db.session.commit()
    flash(f'Product "{name}" added!', 'success')
    return redirect(url_for('admin.manage_products'))


@admin_bp.route('/products/toggle/<int:product_id>')
def toggle_product(product_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin.login'))
    product = DigitalProduct.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    return redirect(url_for('admin.manage_products'))


@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))
