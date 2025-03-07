from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import User, Whitelist
from myapp.utils import token_check

api = Blueprint("api", __name__)


@api.route("/whitelist/<player>", methods=["GET"])
def whitelist(player: str):
    response_data = {"code": 1, "desc": "not fond"}
    result = None
    if len(player) > 16:
        result = Whitelist.query.filter_by(player_uuid=player).first()
    else:
        result = Whitelist.query.filter_by(player_name=player).first()
    if result is not None:
        response_data["code"] = 0
        response_data["desc"] = "在白名单中"
        response_data["uuid"] = result.player_uuid
        response_data["name"] = result.player_name
    return jsonify(response_data)


@api.route("/whitelistAdd", methods=["POST"])
@login_required
def add_whitelist():
    data = request.get_json()
    user: User = current_user
    db.session.add(Whitelist(user.id, data["name"], data["uuid"]))
    db.session.commit()
    return jsonify({"code": 0, "desc": "成功"})


@api.route("/register", methods=["POST"])
@token_check()
def register():
    req_data = request.json
    username = req_data["username"]
    password = req_data["password"]
    if username or password:
        u = User.query.filter_by(username=username).first()
        if u:
            return jsonify({"code": 2, "desc": "用户存在!"})
        user: User = User(username).set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"code": 0, "desc": "注册成功!"})
    return jsonify({"code": 1, "desc": "错误"})
