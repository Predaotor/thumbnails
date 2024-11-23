from models import StoreModel
from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from schemas import StoreSchema
from db import db 
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

blp = Blueprint("stores", __name__, description="Operations on Stores")


@blp.route("/store/<int:store_id>", methods=["GET", "DELETE"])
class Store(MethodView):
    # Get Store with Id 
    @blp.response(200, StoreSchema)
    def get(self, store_id):
        store=StoreModel.query.get_or_404(store_id)
        
        return store

    def delete(self, store_id):
        store=StoreModel.query.get_or_404(store_id)
        db.session.delete(store)
        db.session.commit()
        return {"message": "Store deleted successfully"}, 200
    
@blp.route("/store", methods=["GET", "POST"])
class StoreList(MethodView):
    # Get all stores
    @blp.response(200, StoreSchema(many=True))
    def get(self):
        stores=StoreModel.query.all() 
        return stores

    # Create a new store
    @blp.arguments(StoreSchema)
    @blp.response(200, StoreSchema)
    def post(self, store_data):
        store=StoreModel(**store_data) 
        try:

            db.session.add(store)
            db.session.commit()
        except IntegrityError:
            abort(400, message="A store with that name already exists")
        except SQLAlchemyError:
            abort(500, message="An error occurred while creating the store")
        return store