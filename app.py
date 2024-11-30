import os
from redis1 import redis_client  # Ensure redis_client is properly initialized
from flask import Flask, jsonify
from flask_smorest import Api
from resources.user import blp as UserBlueprint
from db import db  # Assuming db is SQLAlchemy instance
from resources.item import blp as ItemBlueprint
from resources.store import blp as StoreBlueprint 
from resources.tag import blp as TagBlueprint
from models import StoreModel, ItemModel, UserModel
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate 
from dotenv import load_dotenv


def create_app(db_url=None):
    app = Flask(__name__)
    load_dotenv()
    app.config['DEBUG'] = True
    app.config['FLASK_ENV'] = 'development'
    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "Stores REST API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # Corrected from SQLALCHEMY_TRACK_NOTIFICATIONS
    app.config["JWT_SECRET_KEY"]="0e989c56390d1163901ab6e1944c3da3a52ec2755f7e34505e3dc9d62eba9eb6"
    migrate=Migrate(app, db)
    jwt = JWTManager(app)

    # Revoked Token Callback
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        try:
            jti = jwt_payload["jti"]
            # Check if the token's unique identifier (jti) is in the revoked list (stored in Redis)
            if redis_client.get(f"revoked_token:{jti}"):
                return jsonify({"message": "The token has been revoked.", "error": "token_revoked"}), 401
        except Exception as e:
            # Log error if Redis operation fails
            app.logger.error(f"Error checking revoked token: {str(e)}")
            return jsonify({"message": "Internal Server Error", "error": "internal_error"}), 500

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return (jsonify( 
                       {"description":"The token is not fresh",
                        "error":"fresh_token_required",}), 
                401)

    @jwt.token_in_blocklist_loader
    def check_token_in_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]  # Get the token's JTI.
        if redis_client.get(f"revoked_token:{jti}"):
            return True  # The token is in the blocklist, meaning it has been revoked.
        return False  # Token is not revoked, so it is valid.


    # Add Claims to JWT
    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        user = UserModel.query.filter_by(id=identity).first()
        if user and user.id == 1:  # Assuming user ID 1 is admin
            return {"is_admin": True}
        return {"is_admin": False}

    # Expired Token Callback
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        app.logger.error(f"Token expired: {jwt_payload}")
        return jsonify({"message": "The token has expired.", "error": "token_expired"}), 401

    # Invalid Token Callback
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"message": "Signature verification failed", "error": "invalid_token"}), 401

    # Unauthorized Token Callback
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"message": "Request doesn't contain an access token", "error": "authorization_required"}), 401

    # Initialize SQLAlchemy
    db.init_app(app)

    # Initialize database tables at startup
    with app.app_context():
        db.create_all()

    # Register blueprints
    api = Api(app)
    api.register_blueprint(UserBlueprint)
    api.register_blueprint(ItemBlueprint)
    api.register_blueprint(StoreBlueprint)
    api.register_blueprint(TagBlueprint)

    return app
