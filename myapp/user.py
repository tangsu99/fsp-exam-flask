import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import Whitelist

user = Blueprint("user", __name__)


@user.route("/getInfo")
@login_required
def getUserInfo():
    return jsonify(
        {
            "code": 0,
            "data": {
                "id": current_user.id,
                "username": current_user.username,
                "user_qq": current_user.user_qq,
                "role": current_user.role,
                "addtime": current_user.addtime,
                "avatar": current_user.avatar,
                "status": current_user.status,
            },
        }
    )


@user.route("/getWhitelist")
@login_required
def get_whitelist():
    temp = current_user.whitelist
    res = {
        "code": 0,
        "list": [],
    }
    for item in temp:
        res["list"].append(
            {
                "id": item.id,
                "name": item.player_name,
                "uuid": item.player_uuid,
            }
        )
    return jsonify(res)


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


# @user.route("/setAvatar", methods=["GET"])
# @login_required
# def set_avatar():
#     player_uuid = request.args.get("uuid")
#     if not player_uuid:
#         return jsonify({"code": 1, "desc": "UUID为空！"}), 400
#
#     wl = current_user.whitelist
#
#     if len(wl) == 0:
#         return jsonify({"code": 2, "desc": "用户不存在白名单！"}), 404
#     wl_item: Whitelist = uuidInWl(wl, player_uuid)
#     if wl_item is None:
#         return jsonify({"code": 3, "desc": "此UUID不属于用户！"}), 403
#
#     name = wl_item.player_name
#     uuid = wl_item.player_uuid
#
#     cache_path = os.path.join(AVATAR_DIR, f"{name}:{uuid}.png")
#     # 检查缓存中是否已有该玩家的头像
#     # if os.path.exists(cache_path):
#     #     return jsonify({"avatar_url": f"/cache/{uuid}.png"})
#
#     # 获取并缓存头像
#     try:
#         avatar_binary = get_profile_pic(uuid)
#         with open(cache_path, "wb") as f:
#             f.write(avatar_binary)
#
#         # 修改用户头像
#         try:
#             current_user.avatar = f"/static/avatar/{name}:{uuid}.png"
#             db.session.commit()
#             return jsonify(
#                 {
#                     "code": 0,
#                     "avatar_url": f"/static/avatar/{name}:{uuid}.png",
#                     "desc": "更改成功",
#                 }
#             )
#         except Exception as e:
#             db.session.rollback()
#             return jsonify({"code": 5, "desc": f"头像修改失败：{str(e)}"}), 500
#     except Exception as e:
#         return jsonify({"code": 5, "desc": str(e)}), 500
#
#
# def uuidInWl(wl, uuid):
#     for item in wl:
#         if item["uuid"] == uuid:
#             return item
#     return None
