from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, default=10000.0)  # Starting balance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    portfolio = db.relationship('Portfolio', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_portfolio_value(self):
        total_value = 0
        for holding in self.portfolio:
            total_value += holding.shares * holding.stock.current_price
        return total_value
    
    def __repr__(self):
        return f'<User {self.username}>'

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    sector = db.Column(db.String(50), default='Technology')
    
    # Relationships
    transactions = db.relationship('Transaction', backref='stock', lazy=True)
    portfolio = db.relationship('Portfolio', backref='stock', lazy=True)
    
    def __repr__(self):
        return f'<Stock {self.ticker}: ${self.current_price}>'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Transaction {self.type}: {self.quantity} shares of {self.stock.ticker}>'

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    avg_price = db.Column(db.Float, nullable=False)
    
    def get_current_value(self):
        return self.shares * self.stock.current_price
    
    def get_gain_loss(self):
        current_value = self.get_current_value()
        cost_basis = self.shares * self.avg_price
        return current_value - cost_basis
    
    def get_gain_loss_percentage(self):
        cost_basis = self.shares * self.avg_price
        if cost_basis == 0:
            return 0
        return (self.get_gain_loss() / cost_basis) * 100
    
    def __repr__(self):
        return f'<Portfolio {self.shares} shares of {self.stock.ticker}>'
