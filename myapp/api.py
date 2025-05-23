from flask import Blueprint, jsonify, request
from flask_login import current_user
from typing import cast, Optional
from myapp import db
from myapp.db_model import User, Whitelist
from myapp.utils import token_check

api = Blueprint("api", __name__)


@api.route("/whitelist", methods=["POST"])
@token_check()
def whitelist():
    data = request.get_json()
    result: Whitelist | None = Whitelist.query.filter_by(player_uuid=data.get("uuid")).first()
    if result is not None:
        if result.player_name != data.get("name"):
            result.player_name = data.get("name")
            db.session.commit()

        if result.wl_user.status != 1:
            jsonify({"code": 3, "desc": "账户状态异常！"})

        res = {"code": 0, "desc": "在白名单中", "uuid": result.player_uuid, "name": result.player_name}
        print(type(result.user_id))
        if result.user_id is None:
            res["code"] = 2
            res["desc"] = "未绑定账户"
        return jsonify(res)
    return jsonify({"code": 1, "desc": "not fond"})


@api.route("/whitelistAdd", methods=["POST"])
@token_check()
def add_whitelist():
    user: User = cast(User, current_user)
    data = request.get_json()
    db.session.add(Whitelist(
        user_id=user.id,
        player_name=data["name"],
        player_uuid=data["uuid"],
        source=2,
        auditor_uid=user.id
    ))
    db.session.commit()
    return jsonify({"code": 0, "desc": "成功"})


@api.route("/register", methods=["POST"])
@token_check()
def register():
    req_data: Optional[dict[str, str]] = request.json
    if req_data:
        username: str = req_data["username"]
        password: str = req_data["password"]
        if username or password:
            u = User.query.filter_by(username=username).first()
            if u:
                return jsonify({"code": 2, "desc": "用户存在!"})
            user: User = User(username).set_password(password)
            db.session.add(user)
            db.session.commit()
            return jsonify({"code": 0, "desc": "注册成功!"})
        return jsonify({"code": 1, "desc": "错误"})
    return jsonify({"code": 1, "desc": "错误"})
