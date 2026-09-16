from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, )
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class IdempotencyKey(db.Model):
    key = db.Column(db.String, primary_key=True)          
    status = db.Column(db.String, nullable=False)         
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True) 
    created_at = db.Column(db.DateTime, server_default=db.func.now())