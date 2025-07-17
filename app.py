from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from extensions import db, login_manager
from models import User, Stock, Transaction, Portfolio
import os
from datetime import datetime
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Sample stock data for demonstration
SAMPLE_STOCKS = [
    {'name': 'Apple Inc.', 'ticker': 'AAPL', 'price': 175.50, 'sector': 'Technology'},
    {'name': 'Microsoft Corporation', 'ticker': 'MSFT', 'price': 338.25, 'sector': 'Technology'},
    {'name': 'Amazon.com Inc.', 'ticker': 'AMZN', 'price': 127.80, 'sector': 'Consumer Discretionary'},
    {'name': 'Alphabet Inc.', 'ticker': 'GOOGL', 'price': 125.30, 'sector': 'Technology'},
    {'name': 'Tesla Inc.', 'ticker': 'TSLA', 'price': 248.50, 'sector': 'Consumer Discretionary'},
    {'name': 'NVIDIA Corporation', 'ticker': 'NVDA', 'price': 465.75, 'sector': 'Technology'},
    {'name': 'Meta Platforms Inc.', 'ticker': 'META', 'price': 298.40, 'sector': 'Technology'},
    {'name': 'Netflix Inc.', 'ticker': 'NFLX', 'price': 385.60, 'sector': 'Communication Services'},
]

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@stocker.com',
                is_admin=True,
                balance=50000.0
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Add sample stocks if not exists
        for stock_data in SAMPLE_STOCKS:
            stock = Stock.query.filter_by(ticker=stock_data['ticker']).first()
            if not stock:
                stock = Stock(
                    name=stock_data['name'],
                    ticker=stock_data['ticker'],
                    current_price=stock_data['price'],
                    sector=stock_data['sector']
                )
                db.session.add(stock)
        
        db.session.commit()

@app.route('/')
def index():
    stocks = Stock.query.limit(6).all()
    return render_template('index.html', stocks=stocks)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('signup.html')
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    total_users = User.query.count()
    total_transactions = Transaction.query.count()
    recent_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         total_users=total_users,
                         total_transactions=total_transactions,
                         recent_transactions=recent_transactions)

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    portfolio_value = current_user.get_portfolio_value()
    total_value = current_user.balance + portfolio_value
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(5).all()
    
    return render_template('user_dashboard.html',
                         balance=current_user.balance,
                         portfolio_value=portfolio_value,
                         total_value=total_value,
                         recent_transactions=recent_transactions)

@app.route('/portfolio')
@login_required
def portfolio():
    holdings = Portfolio.query.filter_by(user_id=current_user.id).all()
    total_value = sum(holding.get_current_value() for holding in holdings)
    total_gain_loss = sum(holding.get_gain_loss() for holding in holdings)
    
    return render_template('portfolio.html',
                         holdings=holdings,
                         total_value=total_value,
                         total_gain_loss=total_gain_loss)

@app.route('/trade')
@login_required
def trade():
    stocks = Stock.query.all()
    search_query = request.args.get('search', '')
    
    if search_query:
        stocks = Stock.query.filter(
            Stock.name.contains(search_query) | 
            Stock.ticker.contains(search_query)
        ).all()
    
    return render_template('trade.html', stocks=stocks, search_query=search_query)

@app.route('/buy/<int:stock_id>')
@login_required
def buy(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    return render_template('buy.html', stock=stock)

@app.route('/process_buy', methods=['POST'])
@login_required
def process_buy():
    stock_id = int(request.form['stock_id'])
    quantity = int(request.form['quantity'])
    
    stock = Stock.query.get_or_404(stock_id)
    total_cost = stock.current_price * quantity
    
    if current_user.balance < total_cost:
        flash('Insufficient funds', 'error')
        return redirect(url_for('buy', stock_id=stock_id))
    
    # Update user balance
    current_user.balance -= total_cost
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        stock_id=stock_id,
        type='buy',
        quantity=quantity,
        price=stock.current_price,
        total_amount=total_cost
    )
    db.session.add(transaction)
    
    # Update portfolio
    holding = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock_id).first()
    if holding:
        # Update existing holding
        total_shares = holding.shares + quantity
        total_cost_basis = (holding.shares * holding.avg_price) + total_cost
        holding.avg_price = total_cost_basis / total_shares
        holding.shares = total_shares
    else:
        # Create new holding
        holding = Portfolio(
            user_id=current_user.id,
            stock_id=stock_id,
            shares=quantity,
            avg_price=stock.current_price
        )
        db.session.add(holding)
    
    db.session.commit()
    flash(f'Successfully bought {quantity} shares of {stock.ticker}', 'success')
    return redirect(url_for('portfolio'))

@app.route('/sell/<int:stock_id>')
@login_required
def sell(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    holding = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock_id).first()
    
    if not holding:
        flash('You do not own this stock', 'error')
        return redirect(url_for('portfolio'))
    
    return render_template('sell.html', stock=stock, holding=holding)

@app.route('/process_sell', methods=['POST'])
@login_required
def process_sell():
    stock_id = int(request.form['stock_id'])
    quantity = int(request.form['quantity'])
    
    stock = Stock.query.get_or_404(stock_id)
    holding = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock_id).first()
    
    if not holding or holding.shares < quantity:
        flash('Insufficient shares to sell', 'error')
        return redirect(url_for('sell', stock_id=stock_id))
    
    total_proceeds = stock.current_price * quantity
    
    # Update user balance
    current_user.balance += total_proceeds
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        stock_id=stock_id,
        type='sell',
        quantity=quantity,
        price=stock.current_price,
        total_amount=total_proceeds
    )
    db.session.add(transaction)
    
    # Update portfolio
    holding.shares -= quantity
    if holding.shares == 0:
        db.session.delete(holding)
    
    db.session.commit()
    flash(f'Successfully sold {quantity} shares of {stock.ticker}', 'success')
    return redirect(url_for('portfolio'))

@app.route('/admin_manage')
@login_required
def admin_manage():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    users = User.query.all()
    return render_template('admin_manage.html', users=users)

@app.route('/admin_history')
@login_required
def admin_history():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    return render_template('admin_history.html', transactions=transactions)

@app.route('/help')
def help():
    return render_template('help.html')

# API endpoint to update stock prices (for demonstration)
@app.route('/api/update_prices')
def update_prices():
    stocks = Stock.query.all()
    for stock in stocks:
        # Simulate price changes (+/- 5%)
        change_percent = random.uniform(-0.05, 0.05)
        stock.current_price = round(stock.current_price * (1 + change_percent), 2)
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Prices updated'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8000)
