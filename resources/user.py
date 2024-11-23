from flask.views import MethodView 
from flask_smorest import Blueprint, abort 
from passlib.hash import pbkdf2_sha256 
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity
from datetime import timedelta 
from db import db 
from flask import jsonify 
from redis1 import redis_client 
from models import UserModel 
from schemas import UserSchema

blp = Blueprint("Users", "users", description="Operations on users")

@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        if UserModel.query.filter(UserModel.username == user_data["username"]).first():
            abort(409, message="A user with that username already exists")
        
        user = UserModel(
            username=user_data["username"],
            password=pbkdf2_sha256.hash(user_data["password"])
        )
        db.session.add(user)
        db.session.commit()
        return {"message": "User has been registered."}, 201 


@blp.route("/login")    
class UserLogin(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        user = UserModel.query.filter(UserModel.username == user_data["username"]).first()
        if user and pbkdf2_sha256.verify(user_data["password"], user.password): 
            # Check if there's already a token in Redis
            stored_token = redis_client.get(f"user:{user.id}:token")
           
            if stored_token:
                return jsonify(access_token=stored_token), 200
            
            # Create a new access token with an expiration of 1 day
            access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=1), fresh=True)
            refresh_token=create_refresh_token(identity=user.id)
            # Store the new token in Redis with an expiration time (e.g., 1 day)
            redis_client.setex(f"user:{user.id}:token", 86400, access_token)  # Token will expire in 1 day
            
            return {"access_token":access_token, "refresh_token":refresh_token}
        
        abort(401, message="Invalid Credentials.")

@blp.route("/refresh") 
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        current_user=get_jwt_identity()
        new_token=create_access_token(identity=current_user, fresh=False)
        jti=get_jwt()["jti"]
        redis_client.setex(f"refresh_token:{jti}", timedelta(days=3))
        return {"access_token":new_token}


@blp.route("/log_out") 
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        # Get the JWT identity (user) and the jti (JWT ID)
        jti = get_jwt()["jti"]  # Get the unique identifier (JTI) from the JWT.
        
        # Mark the token as revoked in Redis
        redis_client.setex(f"revoked_token:{jti}", timedelta(days=7), "revoked")
        
        # Optionally remove the token from Redis (this might be done already in some setups)
        current_user_id = get_jwt_identity()  # Get the user ID from the JWT identity
        redis_client.delete(f"user:{current_user_id}:token")  # Remove the token from Redis
        
        return jsonify(message="Successfully logged out")
        
@blp.route("/user/<int:user_id>") 
class User(MethodView):
    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user 
    
    def delete(self, user_id):
        user = UserModel.query.get_or_404(user_id) 
        db.session.delete(user) 
        db.session.commit() 
        return {"message": "User successfully deleted"}, 200
