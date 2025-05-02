import re
from datetime import timedelta, timezone, datetime
from functools import wraps
from typing import cast
from flask import abort, current_app, request
from flask_login import current_user

from myapp import db
from myapp.db_model import User, Response

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


def is_survey_response_expired(survey_response: Response) -> bool:
    val = current_app.config["VALIDITY_PERIOD"]
    validity_period = timedelta(hours=val) # 有效期为 24h

    # 只判断未完成的问卷，已完成的问卷不存在“过期”的说法
    if survey_response.is_completed is False:
        create_time = survey_response.create_time
        create_datetime = create_time.replace(tzinfo=timezone.utc)
        current_datetime = datetime.now(timezone.utc)
        expired_datetime = create_datetime + validity_period
        if expired_datetime < current_datetime:
            survey_response.is_completed = True
            survey_response.is_reviewed = 2
            db.session.commit()
            return True
    return False
