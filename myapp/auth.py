from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from flask import Blueprint, current_app, jsonify, request
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
    login_user,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from myapp import APP, db
from myapp.db_model import ActivationToken, RegistrationLimit, ResetPasswordToken, Token, User, UserStatus
from myapp.mail import activation_mail, reset_password_mail, send_mail
from myapp.utils import check_password_format, validate_username

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    req_data: dict[str, str] | None = request.json
    if req_data:
        username = req_data["username"]
        password = req_data["password"]
        stmt = select(User).where(User.username == username)
        user = db.session.scalar(stmt)
        if user and user.check_password(password):
            login_user(user)
            token = create_token(user)

            temp = current_user.whitelist
            play_permission: bool = True if len(temp) > 0 else False

            return jsonify(
                {
                    "code": 0,
                    "token": token,
                    "username": user.username,
                    "avatar": user.avatar,
                    "isAdmin": user.role == "admin",
                    "play_permission": play_permission,
                }
            )
        else:
            return jsonify({"code": 1, "desc": "用户名或密码错误!"})
    return jsonify({"code": 1, "desc": "字段错误！"})


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    if current_user.is_authenticated:
        # 用户已登录
        token: str | None = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "", 1)

        stmt = select(Token).where(Token.token == token)
        tk = db.session.scalar(stmt)
        if tk is None:
            return jsonify({"code": 4, "desc": "Token not found"})
        db.session.delete(tk)
        db.session.commit()
        return jsonify({"code": 0, "desc": "退出成功"})
    return jsonify({"code": 1, "desc": "error"})


@auth.route("/register", methods=["POST"])
def register():
    req_data = request.json
    if not req_data:
        return jsonify({"code": 1, "desc": "请求数据错误"})

    # 获取客户端IP
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if client_ip is None:
        return jsonify({"code": 1, "desc": "无法获取用户IP"})

    client_ip_split = client_ip.split(",")[0]

    # 检查IP注册限制
    if check_ip_registration_limit(client_ip_split):
        return jsonify({"code": 5, "desc": "该IP注册次数过多，请稍后再试!"})

    raw_username = req_data.get("username", "")
    user_qq = req_data.get("userQQ", "").strip()
    password = req_data.get("password", "").strip()
    re_password = req_data.get("passwordAgain", "").strip()

    # 验证必填字段
    if not all([raw_username, password, re_password]):
        return jsonify({"code": 1, "desc": "表单错误!"})

    # 验证用户名
    username_result = validate_username(raw_username)
    if username_result["code"] != 0:
        return jsonify(username_result)
    username = username_result["username"]

    # 验证密码一致性
    if password != re_password:
        return jsonify({"code": 2, "desc": "密码与重复密码不一致!"})

    # 验证密码是否合法
    if not check_password_format(password):
        return jsonify({"code": 2, "desc": "密码不合法!"})

    # 验证 QQ 号格式（QQ 号不能带邮箱后缀）
    if "@qq.com" in user_qq.lower():
        return jsonify({"code": 2, "desc": "请填写纯QQ号，不要带 @qq.com 后缀!"})

    # 验证 QQ 号
    stmt = select(User).where(User.user_qq == user_qq)
    existing_user = db.session.scalar(stmt)

    if existing_user:
        return jsonify({"code": 3, "desc": "QQ号已存在!"})

    # 创建用户
    try:
        new_user = User(
            username=username,
            user_qq=user_qq,
        )

        new_user.password = password

        db.session.add(new_user)

        # 记录IP注册信息
        record_ip_registration(client_ip)

        db.session.commit()

        token = create_token(new_user)
        return jsonify(
            {
                "code": 0,
                "desc": "注册成功",
                "token": token,
                "username": new_user.username,
                "avatar": new_user.avatar,
                "isAdmin": new_user.role == "admin",
            }
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({"code": 5, "desc": "注册失败，请稍后再试"})


@auth.route("/check", methods=["GET"])
def check_login():
    if current_user.is_authenticated:
        # 用户已登录，返回用户信息

        temp = current_user.whitelist
        play_permission: bool = True if len(temp) > 0 else False

        return jsonify(
            {
                "code": 0,
                "username": current_user.username,
                "avatar": current_user.avatar,
                "isAdmin": current_user.role == "admin",
                "play_permission": play_permission,
            }
        )
    else:
        # 用户未登录，返回未登录提示
        return jsonify(
            {
                "code": 1,
                "desc": "User is not logged in",
                "avatar": "b83565e6-b0d0-4265-bb4f-fdb5e8d00655",
            }
        )


@auth.route("/findPassword", methods=["POST"])
def find_password():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if client_ip is None:
        return jsonify({"code": 1, "desc": "无法获取用户IP"})

    client_ip_split = client_ip.split(",")[0]

    # 检查IP注册限制
    if check_ip_registration_limit(client_ip_split):
        return jsonify({"code": 5, "desc": "该IP注册次数过多，请稍后再试!"})

    request_data = request.get_json(silent=True)

    if request_data is None:
        return jsonify({"code": 5, "desc": "缺少数据"})

    qq: str | None = request_data.get("userQQ")

    user = db.session.scalar(select(User).where(User.user_qq == qq))
    if user is None:
        return jsonify({"code": 4, "desc": "未找到用户!"})

    send_reset_password(user)
    return jsonify({"code": 0, "desc": "发送成功！请查找邮箱!"})


@auth.route("/findPassword", methods=["PUT"])
def find_password_set():
    token_str = request.args.get("token", "")
    stmt = select(ResetPasswordToken).where(ResetPasswordToken.token == token_str)
    token = db.session.scalar(stmt)
    if not token:
        return jsonify({"code": 4, "desc": "无效token!"})

    data = request.json
    if data:
        password = data.get("password")
        if not check_password_format(password):
            return jsonify({"code": 2, "desc": "密码不合法!"})

        user: User | None = token.user_r_p_t
        if not user:
            return jsonify({"code": 4, "desc": "未找到用户!"})

        user.password = password
        db.session.delete(token)
        db.session.commit()

        return jsonify({"code": 0, "desc": "修改成功！"})
    return jsonify({"code": 2, "desc": "缺少数据"})


@auth.route("/reqActivation", methods=["post"])
@login_required
def req_activation():
    user = db.session.scalar(select(User).where(User.username == current_user.username))
    if user is None:
        return jsonify({"code": 4, "desc": "未找到用户!"}), 404

    if user.status == UserStatus.ACTIVE:
        return jsonify({"code": 2, "desc": "账户状态正常！不需要进行激活！"})

    if user.status != UserStatus.INACTIVE:
        return jsonify({"code": 2, "desc": "账户状态异常！无法进行激活！"})

    stmt = select(ActivationToken).where(
        ActivationToken.user_id == user.id,
        ActivationToken.expires_at >= datetime.now(UTC),
        ActivationToken.is_revoked.is_(False),
    )

    token = db.session.scalar(stmt)
    if token:
        return jsonify({"code": 1, "desc": "链接未过期请稍后尝试！"})

    send_activation_mail(user)
    return jsonify({"code": 0, "desc": "发送成功！请查找邮箱!"})


@auth.route("/activation", methods=["PUT"])
def activation():
    token_str: str = request.args.get("token", "")
    stmt = select(ActivationToken).where(ActivationToken.token == token_str)
    token = db.session.scalar(stmt)
    if not token:
        return jsonify({"code": 4, "desc": "无效token!"})

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"code": 2, "desc": "json 解析失败"})

    username: str | None = data.get("username")

    user: User | None = token.user_active
    if not user or user.username != username:
        return jsonify({"code": 4, "desc": "未找到用户!"})

    user.status = UserStatus.ACTIVE
    db.session.delete(token)
    db.session.commit()

    return jsonify({"code": 0, "desc": "激活成功！"})


def send_activation_mail(user: User):
    with APP.app_context():
        token = generate_token(user)
        db.session.add(ActivationToken(user_id=user.id, token=token))
        db.session.commit()
        msg = activation_mail([f"{user.user_qq}@qq.com"], token)
        send_mail(APP, msg)


def send_reset_password(user: User):
    with APP.app_context():
        token = generate_token(user)
        db.session.add(ResetPasswordToken(user.id, token))
        db.session.commit()
        msg = reset_password_mail([f"{user.user_qq}@qq.com"], token)
        send_mail(APP, msg)


def check_ip_registration_limit(ip: str):
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    stmt = select(func.count(RegistrationLimit.id)).where(
        RegistrationLimit.ip == ip, RegistrationLimit.register_time >= one_hour_ago
    )
    registrations = db.session.scalar(stmt) or 0

    return registrations >= 2


def record_ip_registration(ip: str):
    registration = RegistrationLimit(ip=ip)
    db.session.add(registration)


def generate_token(user: User, expires_in: int = 3600) -> str:
    payload: dict[str, Any] = {
        "user_id": user.id,
        "exp": datetime.now(UTC) + timedelta(hours=expires_in * 24),
    }
    secret_key: str = current_app.config["SECRET_KEY"]  # type: ignore[reportUnknownVariableType]
    token: str = jwt.encode(payload, secret_key, algorithm="HS256")  # type: ignore[reportUnknownMemberType]
    return token


def create_token(user: User, expires_in: int = 3600 * 24 * 7):
    # 默认是7天过期
    expires_in_minutes = expires_in / 60  # 秒转分钟
    token = generate_token(user, expires_in)
    new_token = Token(
        user_id=user.id, token=token, expires_at=(datetime.now(UTC) + timedelta(minutes=expires_in_minutes))
    )
    db.session.add(new_token)
    db.session.commit()
    return token


def revoke_token(token: str):
    token_record = db.session.scalar(select(Token).where(Token.token == token))
    if token_record:
        token_record.is_revoked = True
        db.session.commit()


def is_token_revoked(token: str):
    token_record = db.session.scalar(select(Token).where(Token.token == token))
    if token_record and token_record.is_revoked:
        return True
    return False


def verify_token(token: str, secret_key: str) -> int:
    try:
        payload = jwt.decode(token, secret_key, algorithm="HS256")  # type: ignore[reportUnknownMemberType]
        user_id = payload["user_id"]
        return user_id
    except jwt.ExpiredSignatureError:
        return -1  # Token 过期
    except jwt.InvalidTokenError:
        return 0  # 无效 Token
