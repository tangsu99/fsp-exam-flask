from flask import Blueprint, jsonify, request
from flask_login import current_user
from typing import cast
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
            return jsonify({"code": 3, "desc": "账户状态异常！"})

        res = {"code": 0, "desc": "在白名单中", "uuid": result.player_uuid, "name": result.player_name}
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

