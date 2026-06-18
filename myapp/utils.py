import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any, Literal, cast

from flask import abort, current_app, jsonify, request
from flask_login import current_user
from flask_sqlalchemy.pagination import Pagination
from werkzeug.datastructures import FileStorage

from myapp.db_model import User

# 密码强度校验的正则，要求密码 8~16 位，且必须同时包含大写字母、小写字母、数字、特殊字符四种字符
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_])[A-Za-z\d\W_]{8,16}$")


def token_check() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            api_token = current_app.config.get("API_TOKEN", "")  # type: ignore[reportUnknownMemberType]
            token = request.headers.get("API-Token")
            if not token or api_token != token:
                abort(401, description="Missing API Token")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def status_check() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            user: User = cast(User, current_user)
            if user.status == 0:
                return jsonify({"code": 3, "desc": "您的账户未激活请前往个人中心激活！"})
            if user.status != 1:
                return jsonify({"code": 3, "desc": "您的账户状态异常！"})
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def required_role(role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            user: User = cast(User, current_user)
            if user.role != role:
                abort(401, description="角色不符")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_password_format(password: str) -> bool:
    """密码强度校验"""
    return bool(PASSWORD_PATTERN.match(password))


# 定义白名单规则列表
# 字符串代表严格匹配前缀，字典中的 'regex' 代表正则表达式匹配
WHITE_LIST_RULES = [
    "https://pan.baidu.com",  # 百度网盘固定前缀
    "https://pan.quark.cn",  # 夸克网盘固定前缀
    {"regex": r"^https://.*lanzou[a-z]?\.com"},  # 蓝奏云正则规则
]


def is_white_list_url(url: str) -> bool:
    """检测单个链接是否符合白名单列表中的规则"""

    strip_url = url.strip()
    if strip_url == "":
        return True

    for rule in WHITE_LIST_RULES:
        if isinstance(rule, str) and strip_url.startswith(rule):
            return True

        if isinstance(rule, dict) and "regex" in rule:
            if re.match(rule["regex"], strip_url):
                return True
    return False


def get_file_size(file_storage: FileStorage, unit: Literal["KB", "MB", "GB"] = "KB") -> int:
    """
    获取文件对象的大小，并转换为指定单位。
    如果计算结果向下取整后为0，则强制返回1。

    :param file_storage: 文件对象（如 Flask 的 FileStorage）
    :param unit: 目标单位，支持 'KB', 'MB', 'GB'
    :return: 转换后的大小 (int)
    """

    original_pos = file_storage.tell()
    file_storage.seek(0, os.SEEK_END)
    size_bytes = file_storage.tell()
    file_storage.seek(original_pos)

    unit_factors = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}

    factor = unit_factors.get(unit.upper(), 1024)

    # 向下取整
    calculated_size = size_bytes // factor

    # 如果算出来文件大小为 0 按 1 算
    return calculated_size if calculated_size > 0 else 1


def parse_frontend_time_to_utc(front_end_time: str) -> datetime:
    """
    对于前端用 new Date(time).toISOString() 格式化的时间，此函数可以将其转化为 UTC 时间的 DateTime
    front_end_time 打印出来应该类似这种格式：2026-06-07T10:43:00.000Z
    """
    return datetime.fromisoformat(front_end_time.replace("Z", "+00:00"))


def parse_dt_to_iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def build_pagination_dict(
    pagination: Pagination, pagination_items: list[Any], with_total: bool = False
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "items": pagination_items,
        "page": pagination.page,
        "pages": pagination.pages,
        "perPage": pagination.per_page,
        "hasNext": pagination.has_next,
        "hasPrev": pagination.has_prev,
    }

    if with_total:
        result["total"] = pagination.total

    return result
