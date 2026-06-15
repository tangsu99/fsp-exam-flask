from typing import cast

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import select

from myapp import db
from myapp.db_model import User, UserStatus, Whitelist, WhitelistType
from myapp.utils import token_check

api = Blueprint("api", __name__)


@api.route("/whitelist", methods=["POST"])
@token_check()
def whitelist():
    data = request.get_json()
    stmt = select(Whitelist).where(Whitelist.player_uuid == data.get("uuid"))
    result: Whitelist | None = db.session.execute(stmt).scalar()
    if result is None:
        return jsonify({"code": 1, "desc": "not fond"})

    if result.user and result.user.status != UserStatus.ACTIVE:
        return jsonify({"code": 3, "desc": "账户状态异常！"})

    if result.player_name != data.get("name"):
        result.player_name = data.get("name")
        db.session.commit()

    return jsonify({"code": 0, "desc": "在白名单中", "uuid": result.player_uuid, "name": result.player_name})


@api.route("/whitelistAdd", methods=["POST"])
@token_check()
def add_whitelist():
    user: User = cast(User, current_user)
    data = request.get_json()
    db.session.add(
        Whitelist(
            user_id=user.id,
            player_name=data["name"],
            player_uuid=data["uuid"],
            source=WhitelistType.OTHER,
            auditor_uid=user.id,
        )
    )
    db.session.commit()
    return jsonify({"code": 0, "desc": "成功"})
