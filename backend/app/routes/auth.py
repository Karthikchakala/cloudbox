from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.user import User
from app.services.security import (
    validate_email,
    validate_username,
    validate_password,
    generate_jwt_token,
    jwt_required,
)
from app.services.audit_logger import log_security_event

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "error": "Request body must be valid JSON.",
            "code": "INVALID_JSON"
        }), 400

    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    # Input validations
    if not validate_username(username):
        return jsonify({
            "error": "Username must be 3-50 characters long and contain only letters, numbers, hyphens, and underscores.",
            "code": "INVALID_USERNAME"
        }), 400

    if not validate_email(email):
        return jsonify({
            "error": "A valid email address is required.",
            "code": "INVALID_EMAIL"
        }), 400

    is_valid_pass, pass_err = validate_password(password)
    if not is_valid_pass:
        return jsonify({
            "error": pass_err,
            "code": "INVALID_PASSWORD"
        }), 400

    # Duplicate checks
    existing_user_email = User.query.filter(User.email.ilike(email)).first()
    if existing_user_email:
        return jsonify({
            "error": "An account with this email address already exists.",
            "code": "EMAIL_ALREADY_EXISTS"
        }), 409

    existing_user_name = User.query.filter(User.username.ilike(username)).first()
    if existing_user_name:
        return jsonify({
            "error": "Username is already taken.",
            "code": "USERNAME_ALREADY_EXISTS"
        }), 409

    try:
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Issue JWT access token on registration
        token = generate_jwt_token(str(user.id), user.email, user.username)

        log_security_event(
            event_type="AUTH",
            action="USER_REGISTER",
            status="SUCCESS",
            user_id=str(user.id),
            target_resource_id=str(user.id),
            details={"email": email, "username": username}
        )

        return jsonify({
            "message": "User registered successfully.",
            "user": user.to_dict(),
            "access_token": token,
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to register user due to an internal server error.",
            "code": "REGISTRATION_ERROR"
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user credentials and return a signed JWT access token."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "error": "Request body must be valid JSON.",
            "code": "INVALID_JSON"
        }), 400

    identifier = str(data.get("email") or data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not identifier or not password:
        return jsonify({
            "error": "Email and password are required.",
            "code": "MISSING_CREDENTIALS"
        }), 400

    user = User.query.filter(
        (User.email.ilike(identifier)) | (User.username.ilike(identifier))
    ).first()
    if not user or not user.check_password(password):
        log_security_event(
            event_type="AUTH",
            action="USER_LOGIN",
            status="FAILED",
            user_id=str(user.id) if user else "unregistered",
            details={"attempted_identifier": identifier}
        )
        # Prevent username enumeration through generic response
        return jsonify({
            "error": "Invalid email or password.",
            "code": "INVALID_CREDENTIALS"
        }), 401

    token = generate_jwt_token(str(user.id), user.email, user.username)

    log_security_event(
        event_type="AUTH",
        action="USER_LOGIN",
        status="SUCCESS",
        user_id=str(user.id),
        details={"email": user.email, "username": user.username}
    )

    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict(),
        "access_token": token,
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_current_user():
    """Retrieve profile details for the authenticated user."""
    return jsonify({
        "user": g.current_user.to_dict()
    }), 200
