import re
from functools import wraps
from typing import cast
from flask import abort, current_app, request
from flask_login import current_user

from myapp.db_model import User

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,16}$")


def token_check():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_token = current_app.config["API_TOKEN"]
            token = request.headers.get("API-Token")
            if not token or api_token != token:
                abort(401, description="Missing API Token")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def required_role(role: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user: User = cast(User, current_user)
            if user.role != role:
                abort(401, description="角色不符")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_password(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password))
