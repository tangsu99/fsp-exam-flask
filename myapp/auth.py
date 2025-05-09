from datetime import datetime, timezone, timedelta
from threading import Thread
from typing import Optional, cast
import jwt
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user

from myapp import APP, db, reset_password_mail, mail
from myapp.db_model import Token, User, Whitelist, RegistrationLimit, ResetPasswordToken, ActivationToken
from myapp.mail import activation_mail
from myapp.utils import check_password

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    req_data: Optional[dict[str, str]] = request.json
    if req_data:
        username = req_data["username"]
        password = req_data["password"]
        user: User | None = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            token = create_token(user)
            return jsonify(
                {
                    "code": 0,
                    "token": token,
                    "username": user.username,
                    "avatar": user.avatar,
                    "isAdmin": user.role == "admin",
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
        tk: Token | None = Token.query.filter_by(token=token).first()
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
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if client_ip is None:
        return jsonify({"code": 1, "desc": "无法获取用户IP"})

    client_ip_split = client_ip.split(',')[0]

    # 检查IP注册限制
    if check_ip_registration_limit(client_ip_split):
        return jsonify({"code": 5, "desc": "该IP注册次数过多，请稍后再试!"})

    username = req_data.get("username")
    user_qq = req_data.get("userQQ")
    password = req_data.get("password")
    re_password = req_data.get("repassword")

    # 验证必填字段
    if not all([username, password, re_password]):
        return jsonify({"code": 1, "desc": "表单错误!"})

    # 验证密码一致性
    if password != re_password:
        return jsonify({"code": 2, "desc": "密码与重复密码不一致!"})

    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({"code": 3, "desc": "用户名已存在!"})

    # 检查白名单
    if Whitelist.query.filter_by(player_name=username).first():
        return jsonify({"code": 3, "desc": "用户名已存在!"})

    # 创建用户
    try:
        user = User(username=username, user_qq=user_qq).set_password(password)
        db.session.add(user)

        # 记录IP注册信息
        record_ip_registration(client_ip)

        db.session.commit()

        token = create_token(user)
        return jsonify({
            "code": 0,
            "desc": "注册成功",
            "token": token,
            "username": user.username,
            "avatar": user.avatar,
            "isAdmin": user.role == "admin",
        })
    except Exception:
        db.session.rollback()
        return jsonify({"code": 5, "desc": "注册失败，请稍后再试"})


@auth.route("/check", methods=["GET"])
def check_login():
    if current_user.is_authenticated:
        # 用户已登录，返回用户信息
        return jsonify(
            {
                "code": 0,
                "username": current_user.username,
                "avatar": current_user.avatar,
                "isAdmin": current_user.role == "admin",
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


@auth.route('/findPassword', methods=["POST"])
def find_password():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    if client_ip is None:
        return jsonify({"code": 1, "desc": "无法获取用户IP"})

    client_ip_split = client_ip.split(',')[0]

    # 检查IP注册限制
    if check_ip_registration_limit(client_ip_split):
        return jsonify({"code": 5, "desc": "该IP注册次数过多，请稍后再试!"})

    if request.json:
        username = request.json.get('username')
        qq = request.json.get('userQQ')
        user = User.query.filter_by(user_qq=qq, username=username).first()
        if not user:
            return jsonify({"code": 4, "desc": "未找到用户!"}), 404
        Thread(target=send_reset_password, args=(user,), ).start()
        return jsonify({"code": 0, "desc": "发送成功！请查找邮箱!"})

    return jsonify({"code": 5, "desc": "缺少数据"})


@auth.route('/findPassword', methods=["PUT"])
def find_password_set():
    token = ResetPasswordToken.query.filter_by(token=request.args.get('token', '')).first()
    if not token:
        return jsonify({"code": 4, "desc": "无效token!"}), 404

    data = request.json
    if data:
        password = data.get('password')
        if not check_password(password):
            return jsonify({"code": 2, "desc": "密码不合法!"})

        user: User | None = token.user_r_p_t
        if not user:
            return jsonify({"code": 4, "desc": "未找到用户!"}), 404

        user.set_password(password)
        db.session.delete(token)
        db.session.commit()

        return jsonify({"code": 0, "desc": "修改成功！"})
    return jsonify({"code": 2, "desc": "缺少数据"})


@auth.route('/reqActivation', methods=["post"])
@login_required
def req_activation():
    user: User = User.query.filter_by(username=current_user.username).first()
    if user.status != 0:
        if user.status == 1:
            return jsonify({"code": 2, "desc": "账户状态正常！不需要进行激活！"})
        return jsonify({"code": 2, "desc": "账户状态异常！无法进行激活！"})
    token = ActivationToken.query.filter(
        ActivationToken.user_id == user.id,
        ActivationToken.expires_at >= datetime.now(timezone.utc),
        ActivationToken.is_revoked != True
    ).first()
    if token:
        return jsonify({"code": 1, "desc": "链接未过期请稍后尝试！"})
    Thread(target=send_activation_mail, args=(user,), ).start()
    return jsonify({"code": 0, "desc": "发送成功！请查找邮箱!"})


@auth.route('/activation', methods=["PUT"])
def activation():
    token = ActivationToken.query.filter_by(token=request.args.get('token', '')).first()
    if not token:
        return jsonify({"code": 4, "desc": "无效token!"}), 404

    data = request.json
    if data:
        username = data.get('username')

        user: User | None = token.user_active
        if not user or user.username != username:
            return jsonify({"code": 4, "desc": "未找到用户!"}), 404

        user.status = 1
        db.session.delete(token)
        db.session.commit()

        return jsonify({"code": 0, "desc": "激活成功！"})
    return jsonify({"code": 2, "desc": "缺少数据"})


def send_activation_mail(user):
    with APP.app_context():
        token = generate_token(user)
        db.session.add(ActivationToken(user.id, token))
        db.session.commit()
        msg = activation_mail([f'{user.user_qq}@qq.com'], token)
        mail.send(msg)


def send_reset_password(user):
    with APP.app_context():
        token = generate_token(user)
        db.session.add(ResetPasswordToken(user.id, token))
        db.session.commit()
        msg = reset_password_mail([f'{user.user_qq}@qq.com'], token)
        mail.send(msg)


def check_ip_registration_limit(ip):
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    registrations = RegistrationLimit.query.filter(
        RegistrationLimit.ip == ip,
        RegistrationLimit.register_time >= one_hour_ago
    ).count()
    return registrations >= 2


def record_ip_registration(ip):
    registration = RegistrationLimit(ip=ip)
    db.session.add(registration)


def generate_token(user, expires_in=3600):
    payload = {
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in * 24),
    }
    secret_key = current_app.config["SECRET_KEY"]
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def create_token(user, expires_in=3600 * 24 * 7):
    token = generate_token(user, expires_in)
    new_token = Token(user_id=user.id, token=token, expires_in=expires_in)
    db.session.add(new_token)
    db.session.commit()
    return token


def revoke_token(token):
    token_record = Token.query.filter_by(token=token).first()
    if token_record:
        token_record.is_revoked = True
        db.session.commit()


def is_token_revoked(token):
    token_record = Token.query.filter_by(token=token).first()
    if token_record and token_record.is_revoked:
        return True
    return False


def verify_token(token, secret_key) -> int:
    try:
        payload = jwt.decode(token, secret_key, algorithm="HS256")
        user_id = payload["user_id"]
        return user_id
    except jwt.ExpiredSignatureError:
        return -1  # Token 过期
    except jwt.InvalidTokenError:
        return 0  # 无效 Token
