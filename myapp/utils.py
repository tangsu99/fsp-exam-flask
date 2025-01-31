from functools import wraps
from flask import current_app, request, abort


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