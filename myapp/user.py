from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import select

from myapp import db
from myapp.db_model import Profile, Token, User, Whitelist
from myapp.guarantee import build_trust_chain
from myapp.utils import check_data_size, parse_dt_to_iso_utc

user = Blueprint("user", __name__)


@user.route("/getInfo")
@login_required
def get_user_info():
    return jsonify(
        {
            "code": 0,
            "data": {
                "id": current_user.id,
                "username": current_user.username,
                "user_qq": current_user.user_qq,
                "role": current_user.role,
                "addtime": parse_dt_to_iso_utc(current_user.registered_at),
                "avatar": current_user.avatar,
                "status": current_user.status,
                "play_permission": current_user.has_play_permission,
            },
        }
    )


@user.route("/getWhitelist")
@login_required
def get_whitelist():
    return jsonify(
        {
            "code": 0,
            "list": [{"id": i.id, "name": i.player_name, "uuid": i.player_uuid} for i in current_user.whitelist],
        }
    )


@user.route("/setAvatar", methods=["POST"])
@login_required
def set_avatar():
    # 获取请求数据
    req_data = request.json

    # 检查是否提供了 uuid
    if not req_data or "uuid" not in req_data:
        return jsonify({"code": 1, "desc": "缺少头像 uuid 参数！"}), 400

    avatar_uuid = req_data["uuid"]

    # 修改用户头像
    try:
        current_user.avatar = avatar_uuid
        db.session.commit()
        return jsonify({"code": 0, "desc": "头像修改成功！"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 3, "desc": f"头像修改失败：{str(e)}"}), 500


@user.route("/profile/setBackground", methods=["POST"])
@login_required
def set_background():
    """设置用户个人主页背景图"""
    req_data: dict[str, Any] | None = request.get_json(silent=True)
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少信息！"})

    if not req_data or "bg_url" not in req_data:
        return jsonify({"code": 1, "desc": "缺少 bg_url 参数！"}), 400

    bg_url = req_data["bg_url"]
    if not check_data_size(bg_url, "MB", 5):
        return jsonify({"code": 2, "desc": "背景图数据不能超过 5MB！"})

    try:
        profile = current_user.profile
        if profile is None:
            profile = Profile(user_id=current_user.id)
            db.session.add(profile)
        profile.background_url = req_data["bg_url"]
        db.session.commit()
        return jsonify({"code": 0, "desc": "背景图设置成功！"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 3, "desc": f"背景图设置失败：{str(e)}"}), 500


def update_password(uid: int, token: str, new_password: str):

    user_: User | None = db.session.get(User, uid)
    if not user_:
        return "用户不存在"

    if not user_.check_password(new_password):
        return "新旧密码不能相同"

    token_record = db.session.scalar(select(Token).where(Token.token == token, Token.user_id == uid))
    if token_record is None:
        return "token未找到"

    user_.password = new_password

    db.session.delete(token_record)
    db.session.commit()
    return "修改成功"


@user.route("/getChainOfTrust", methods=["GET"])
@login_required
def get_chain_of_trust():
    query_player_uuid = request.args.get("uuid", "", type=str)

    if not query_player_uuid:
        return jsonify({"code": 1, "desc": "缺少 uuid 参数"})

    player = db.session.scalar(select(Whitelist).where(Whitelist.player_uuid == query_player_uuid))
    if player is None:
        return jsonify({"code": 1, "desc": "该玩家没有白名单！"})

    trust_chain = build_trust_chain(query_player_uuid)

    return jsonify(
        {
            "code": 0,
            "desc": "success",
            "data": {
                "playerUUID": query_player_uuid,
                "playerName": player.player_name,
                "chain": trust_chain,
            },
        }
    )
