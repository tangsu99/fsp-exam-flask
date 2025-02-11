from functools import wraps
from flask import current_app, request, abort
from flask_login import current_user

from myapp.db_model import User


def token_check():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_token = current_app.config['API_TOKEN']
            token = request.headers.get('API-Token')
            if not token or api_token != token:
                abort(401, description='Missing API Token')
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def required_role(role: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user: User = current_user
            if user.role != role:
                abort(401, description='角色不符')
            return f(*args, **kwargs)

        return decorated_function

    return decorator
