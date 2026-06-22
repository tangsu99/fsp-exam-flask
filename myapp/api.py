from typing import cast

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import select

from myapp import db
from myapp.db_model import User, UserStatus, Whitelist, WhitelistType
from myapp.utils import token_check

api = Blueprint("api", __name__)

mc_users_info: dict[str, object] = {
    "user_count": 0,
    "user_w_list_count": 0,
    "online_players": [],
}


def get_mc_users_info() -> dict[str, object]:
    return mc_users_info


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


@api.route("/usersInfo", methods=["POST"])
@token_check()
def report_users_info():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"code": 1, "desc": "请求数据格式错误"}), 400

    user_count = data.get("user_count")
    user_w_list_count = data.get("user_w_list_count")
    online_players = data.get("online_players")

    if not isinstance(user_count, int) or not isinstance(user_w_list_count, int) or not isinstance(online_players, list):
        return jsonify({"code": 1, "desc": "字段类型错误"}), 400

    mc_users_info["user_count"] = user_count
    mc_users_info["user_w_list_count"] = user_w_list_count
    mc_users_info["online_players"] = []

    for player in online_players:
        if not isinstance(player, dict):
            continue
        mc_users_info["online_players"].append(
            {
                "playerName": player.get("playerName", ""),
                "playerUuid": player.get("playerUuid", ""),
                "currentServer": player.get("currentServer", ""),
            }
        )

    return jsonify({"code": 0, "desc": "上报成功"})
