from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import User, Token, Whitelist

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
                "addtime": current_user.addtime,
                "avatar": current_user.avatar,
                "status": current_user.status,
                "play_permission": current_user.has_play_permission,
            },
        }
    )


@user.route("/getWhitelist")
@login_required
def get_whitelist():
    return jsonify({
        "code": 0,
        "list": [
            {"id": i.id, "name": i.player_name, "uuid": i.player_uuid}
            for i in current_user.whitelist
        ],
    })


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


def update_password(uid: int, token: str, new_password: str):

    user_: User | None = db.session.get(User, uid)
    if not user_:
        return "用户不存在"

    if not user_.check_password(new_password):
        return "新旧密码不能相同"

    token_record: Token | None = db.session.query(Token).filter_by(
        token=token, user_id=uid
    ).first()

    if token_record is None:
        return "?"

    user.password = new_password

    db.session.delete(token_record)
    db.session.commit()
    return "修改成功"


@user.route("/getChainOfTrust", methods=["GET"])
@login_required
def get_chain_of_trust():
    query_player_uuid = request.args.get("uuid", '', type=str)

    query = db.session.query(Whitelist).filter_by(player_uuid=query_player_uuid).filter()
    # if q
    # uuid已经在白名单里

    # temp = current_user.whitelist
    # play_permission: bool = True if len(temp) > 0 else False
    #
