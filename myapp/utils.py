import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any, Literal, cast

from flask import abort, current_app, jsonify, request
from flask_login import current_user
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import select
from werkzeug.datastructures import FileStorage

from myapp import db
from myapp.db_model import User

# 密码复杂性校验：长度 8~16 位，至少包含一个字母和一个数字
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*[0-9])[\s\S]{8,16}$")


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


def is_password_complexity_valid(password: str) -> bool:
    """密码强度校验"""
    return bool(PASSWORD_PATTERN.match(password))


def check_data_size(data: str, unit: Literal["KB", "MB", "GB"], value: int) -> bool:
    """
    检查字符串数据（如 base64 URL）的大小是否不超过指定限制。

    :param data: 要检查的字符串
    :param unit: 单位，支持 'KB', 'MB', 'GB'
    :param value: 最大允许的数值（如 5MB 则 unit="MB", value=5）
    :return: 不超过限制返回 True，否则返回 False
    """
    unit_factors = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
    factor = unit_factors.get(unit.upper(), 1024)
    size_bytes = len(data.encode("utf-8"))
    return size_bytes <= value * factor


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


def parse_dt_to_iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""

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


def validate_username(username: str, exclude_user_id: int | None = None) -> dict[str, Any]:
    """
    验证用户名是否合法。

    检查规则：
    - 不能为空
    - 长度不能超过 100 个字符
    - 不能与其他用户重复

    :param username: 待校验的用户名
    :param exclude_user_id: 排除的用户 ID（修改用户名时使用，跳过该用户自身的检查）
    :return: {"code": 0} 表示合法，否则返回 {"code": ..., "desc": "..."}
    """
    username = username.strip()
    if not username:
        return {"code": 1, "desc": "用户名不能为空！"}

    if len(username) > 100:
        return {"code": 2, "desc": "用户名长度不能超过 100 个字符！"}

    stmt = select(User).where(User.username == username)
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    existing = db.session.scalar(stmt)
    if existing is not None:
        return {"code": 3, "desc": "该用户名已被使用！"}

    return {"code": 0, "username": username}
