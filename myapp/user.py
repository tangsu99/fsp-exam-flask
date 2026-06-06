from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import User, Token, Whitelist, Guarantee

user = Blueprint("user", __name__)


def build_trust_chain(player_uuid: str, max_depth: int = 10) -> list[dict]:
    """
    构建信任链列表
    Returns: [{"guarantor": {...}, "applicant": {...}}, ...]
             列表顺序为：从直接担保人 -> 最顶层担保人
    """
    chain = []
    visited_user_ids = set()  # 防止环形担保导致无限循环

    # 1. 找到目标玩家的白名单记录及关联用户
    whitelist_entry = db.session.query(Whitelist).filter_by(player_uuid=player_uuid).first()
    if not whitelist_entry or not whitelist_entry.user_id:
        return chain

    current_applicant_id = whitelist_entry.user_id
    visited_user_ids.add(current_applicant_id)

    # 2. 逐层向上追溯担保关系
    depth = 0
    while depth < max_depth:
        # 查找当前用户作为申请人的担保记录
        guarantee = db.session.query(Guarantee).filter(
            Guarantee.applicant_id == current_applicant_id
        ).first()

        if not guarantee:
            break  # 没有更多担保记录，到达信任链顶端

        guarantor = guarantee.guarantor
        applicant = guarantee.applicant_user

        # 安全检查：如果担保人已访问过，说明存在环，立即终止
        if guarantor.id in visited_user_ids:
            chain.append({
                "guarantor": {
                    "id": guarantor.id,
                    "username": guarantor.username,
                    "user_qq": guarantor.user_qq,
                    "avatar": guarantor.avatar,
                    "warning": "检测到环形担保"
                },
                "applicant": {
                    "id": applicant.id,
                    "username": applicant.username,
                    "user_qq": applicant.user_qq,
                    "avatar": applicant.avatar
                }
            })
            break

        chain.append({
            "guarantor": {
                "id": guarantor.id,
                "username": guarantor.username,
                "user_qq": guarantor.user_qq,
                "avatar": guarantor.avatar
            },
            "applicant": {
                "id": applicant.id,
                "username": applicant.username,
                "user_qq": applicant.user_qq,
                "avatar": applicant.avatar
            }
        })

        visited_user_ids.add(guarantor.id)
        current_applicant_id = guarantor.id  # 继续向上追溯
        depth += 1

    return chain


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

    if not query_player_uuid:
        return jsonify({"code": 1, "desc": "缺少 uuid 参数"})

    player = db.session.query(Whitelist).filter_by(player_uuid=query_player_uuid).first()
    if player is None:
        return jsonify({"code": 1, "desc": "该玩家没有白名单！"})

    trust_chain = build_trust_chain(query_player_uuid)

    return jsonify({
        "code": 0,
        "desc": "success",
        "data": {
            "playerUUID": query_player_uuid,
            "playerName": player.player_name,
            "chain": trust_chain,
        }
    })
