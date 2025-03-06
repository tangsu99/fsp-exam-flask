from datetime import datetime, timedelta

import jwt
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required, login_user

from myapp import db
from myapp.db_model import DEFAULT_AVATAR, Token, User, Whitelist

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    req_data = request.json
    username = req_data["username"]
    password = req_data["password"]
    user: User = User.query.filter_by(username=username).first()
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
        return jsonify({"code": 1, "desc": "User not found"})


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    if current_user.is_authenticated:
        # 用户已登录
        token: str = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "", 1)
        Token.query.filter_by(token=token).delete()
        db.session.commit()
        return jsonify({"code": 0, "desc": "退出成功"})


@auth.route("/register", methods=["POST"])
def register():
    req_data = request.json
    username = req_data["username"]
    user_qq = req_data["userQQ"]
    password = req_data["password"]
    re_password = req_data["repassword"]
    if username or password or re_password:
        if password == re_password:
            u = User.query.filter_by(username=username).first()
            w = Whitelist.query.filter_by(player_name=username).first()
            if u or w:
                return jsonify({"code": 3, "desc": "用户存在!"})
            user: User = User(username, user_qq=user_qq).set_password(password)
            db.session.add(user)
            db.session.commit()
            token = create_token(user)
            return jsonify(
                {
                    "code": 0,
                    "desc": "成功",
                    "token": token,
                    "username": user.username,
                    "avatar": user.avatar,
                    "isAdmin": user.role == "admin",
                }
            )
        return jsonify({"code": 2, "desc": "密码与重复密码不一致"})
    return jsonify({"code": 1, "desc": "表单错误"})


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
        return jsonify({"code": 1, "desc": "User is not logged in", "avatar": "b83565e6-b0d0-4265-bb4f-fdb5e8d00655"})


def generate_token(user, expires_in=3600):
    payload = {"user_id": user.id, "exp": datetime.utcnow() + timedelta(hours=expires_in * 24)}
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
