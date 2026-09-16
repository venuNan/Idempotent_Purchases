from flask import Flask, jsonify, request
from sqlalchemy.exc import IntegrityError
from .models import db, Order, IdempotencyKey, Product


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "max_overflow": 5,
    "pool_pre_ping": True,
}
db.init_app(app)


@app.route("/products", methods=["POST"])
def products():
    data = request.get_json()
    product_name = data.get("product_name")
    if product_name:
        try:
            smt = db.select(Product).where(Product.name == product_name)
            res = db.session.execute(smt).scalar()
            if not res:
                entry = Product(name=product_name, stock=10)
                db.session.add(entry)
                db.session.flush()
                product_id = entry.id
                db.session.commit()
                return jsonify({"Msg":f"Succesfully created {product_name} product with product_id of {product_id} and stock of 10.", "product_id":product_id}), 201
            else:
                return jsonify({"Error": f"{product_name} product already exists with stock {res.stock} available"}), 400
        except IntegrityError:
            db.session.rollback()
            return jsonify({"Error":"Internal Server Error"}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"Error":"Internal Server Error"}), 500
    else:
        return jsonify({"Error":"Missing required data fields"}), 400

@app.route("/purchase", methods=["POST"])
def purchase():
    data = request.get_json()
    product_id = data.get("product_id")
    idempotent_key = data.get("idempotent_key")
    if product_id and idempotent_key:
        try:
            with db.session.begin():
                key_entry = IdempotencyKey(key=idempotent_key, status = "Processing")
                db.session.add(key_entry)
                smt = db.select(Product).where(Product.id == product_id).with_for_update()
                res = db.session.execute(smt).scalar()
                if res.stock > 0:
                    product_update = db.update(Product).where(Product.id == product_id).values(stock = Product.stock - 1)
                    db.session.execute(product_update)
                    order_entry = Order(product_id=product_id)
                    db.session.add(order_entry)
                    db.session.flush()
                    order_id = order_entry.id
                    idempotent_key_status_update = db.update(IdempotencyKey).where(IdempotencyKey.key == idempotent_key).values(status="Successfull")
                    db.session.execute(idempotent_key_status_update)
                    idempotency_table_order_id = db.update(IdempotencyKey).where(IdempotencyKey.key == idempotent_key).values(order_id = order_id)
                    db.session.execute(idempotency_table_order_id)
                    return jsonify({"Msg":f"Completed the order successfully. Order_id = {order_id}"}), 201
                else:
                    idempotent_key_status_update = db.update(IdempotencyKey).where(IdempotencyKey.key == idempotent_key).values(status="Out of Stock")
                    db.session.execute(idempotent_key_status_update)
                    return jsonify({"Msg":"The product is out of stock."}), 200


        except IntegrityError:
            smt = db.select(IdempotencyKey).where(IdempotencyKey.key == idempotent_key)
            res = db.session.execute(smt).scalar()
            return jsonify({"Error": f"The order is {"being" if res.status=="Processing" else ""} {res.status}"}), 200
        except Exception:
            return jsonify({"Error": "Internal Server Error"}), 500
    else:
        return jsonify({"Error":"Missing required data fields"}), 400



    

with app.app_context():
    db.create_all()