from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import User, Token

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


def update_password(uid: int, token: str, new_password: str, old_password: str) -> bool:
    if new_password != old_password:
        return False

    user: User | None = User.query.get(uid)

    if user:
        token_record: Token | None = Token.query.filter_by(token=token).first()

        user.set_password(new_password)
        db.session.delete(token_record)
        db.session.commit()
        return True

    return False
