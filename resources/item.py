from flask import request
from models import ItemModel 
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from db import db
from flask_smorest import Blueprint, abort
from flask.views import MethodView 
from schemas import ItemSchema, ItemUpdateSchema

blp = Blueprint("Items", __name__, description="Operations on items")


@blp.route("/item", methods=["GET", "POST"])
class ItemList(MethodView):
    # Create Item Using store Id
    @jwt_required(fresh=True)
    @blp.arguments(ItemSchema)
    @blp.response(201, ItemSchema)
    def post(self, item_data):
       item=ItemModel(**item_data)
       try:
          db.session.add(item) 
          db.session.commit()
       except IntegrityError: 
          abort(400, message="An item with this name is already exists")
       except SQLAlchemyError:
          abort(500, message="An error occurred while inserting the data")
       return item, 200
    # Get all items
    @blp.response(200, ItemSchema(many=True))
    @jwt_required()
    def get(self):
        items=ItemModel.query.all()
        return items
         

@blp.route("/item/<int:item_id>", methods=["GET", "DELETE", "PUT"])
class Item(MethodView):
    @jwt_required()
    @blp.response(200, ItemSchema)
    def get(self, item_id):
        item=ItemModel.query.get_or_404(item_id) 
        return item

    # Delete item with item_id
    @jwt_required()
    def delete(self, item_id):
        jwt=get_jwt()
        if not jwt.get("is_admin"):
          abort(401, message="Admin privilege  required. ")
        item=ItemModel.query.get_or_404(item_id)
        try:
            db.session.delete(item) 
            db.session.commit() 
            return {"message":"Item deleted successfully"}, 200 
        except SQLAlchemyError:
            abort(500, "An error occurred while deleting the item")
   
    # Update item with item_id
    @jwt_required()
    @blp.arguments(ItemUpdateSchema)
    @blp.response(200, ItemSchema)
    def put(self, item_data, item_id):
        item=ItemModel.query.get_or_404(item_id)
        try:
            for key, value in item_data.items():
                setattr(item, key, value)
            db.session.commit()
            return item 
        except SQLAlchemyError:
            abort(500, message="An Error occurred when updating an item")