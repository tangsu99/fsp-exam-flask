import re
from datetime import timedelta, timezone, datetime
from functools import wraps
from typing import cast
from flask import abort, current_app, request, jsonify
from flask_login import current_user

from myapp import db
from myapp.db_model import User, Response

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_])[A-Za-z\d\W_]{8,16}$")


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



def status_check():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user: User = cast(User, current_user)
            if user.status == 0:
                return jsonify({"code": 3, "desc": "您的账户未激活请前往个人中心激活！"})
            if user.status != 1:
                return jsonify({"code": 3, "desc": "您的账户状态异常！"})
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


def check_password_format(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password))


def is_survey_response_expired(survey_response: Response) -> bool:
    val = current_app.config["RESPONSE_VALIDITY_PERIOD"]
    validity_period = timedelta(hours=val) # 有效期为 24h

    # 只判断未完成的问卷，已完成的问卷不存在“过期”的说法
    if not survey_response.is_completed:
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

def validate_json_required_fields(required_fields:dict, data: dict) -> dict:
    """
    接受数据格式模板（字典）和数据(字典）
    数据格式模板例如：
    required_fields = {
        "survey": (int, True, "question_survey_id"),
        "type": (int, True, "question_type"),
        "score": (float, True, "question_score"),
        "title": (str, True, "question_title"),
        "options": (list, True, "question_options"),
        "display_order": (int, True, "question_display_order")
    }
    """
    return_data = {"success": True, "data": {}}
    for field, (expected_type, is_required, new_field) in required_fields.items():
        value = data.get(field)

        if value is None and is_required:
            return {"success": False}

        # 分数是浮点的，如果前端传来例如5分，会被识别成int类型，如果不处理会出问题
        if not isinstance(value, expected_type) and expected_type is float and not isinstance(value, int):
            return {"success": False}

        return_data["data"][new_field] = value

    return return_data


# 定义白名单规则列表
# 字符串代表严格匹配前缀，字典中的 'regex' 代表正则表达式匹配
WHITE_LIST_RULES = [
    "https://pan.baidu.com",  # 百度网盘固定前缀
    "https://pan.quark.cn",  # 夸克网盘固定前缀
    {"regex": r'^https://(www\.|wws\.)?lanzou[a-z]?\.com'}  # 蓝奏云正则规则
]

def is_white_list_url(url: str) -> bool:
    """检测单个链接是否符合白名单列表中的规则"""

    strip_url = url.strip()

    for rule in WHITE_LIST_RULES:
        if isinstance(rule, str) and strip_url.startswith(rule):
            return True

        if isinstance(rule, dict) and 'regex' in rule:
            if re.match(rule['regex'], strip_url):
                return True
    return False
