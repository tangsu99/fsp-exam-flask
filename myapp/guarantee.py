from datetime import datetime, timezone, timedelta
from jsonschema import validate, ValidationError

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import Guarantee, User, Whitelist

guarantee = Blueprint("guarantee", __name__)


def checkGuarantor(info: dict) -> dict:
    wl_result = Whitelist.query.filter_by(player_uuid=info["player_uuid"]).first()

    if wl_result is None:
        return {"code": 1, "desc": "担保人不属于白名单成员，无法担保！"}

    user_result: User | None = User.query.get(wl_result.user_id)
    if user_result is None:
        return {"code": 1, "desc": "担保人账户不存在"}

    if user_result.status != 1:
        return {"code": 1, "desc": "担保人账户状态异常，无法担保！"}

    return {"code": 0, "guarantor_id": user_result.id}


def checkApplicant(info: dict) -> dict:
    wl_result = Whitelist.query.filter_by(player_uuid=info["player_uuid"]).first()

    if wl_result:
        return {"code": 1, "desc": "你已经是白名单成员"}

    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    g_result = Guarantee.query.filter(
        Guarantee.player_uuid == info["player_uuid"],
        Guarantee.create_time >= ten_minutes_ago,
        Guarantee.status == 0,
    ).all()

    if len(g_result) != 0:
        return {"code": 1, "desc": "存在未过期的担保！"}

    return {"code": 0}


def returnData(i: Guarantee):
    return {
        "uid": i.applicant.id, # type: ignore
        "id": i.id,
        "username": i.applicant.username, # type: ignore
        "userQQ": i.applicant.user_qq, # type: ignore
        "avatar": i.applicant.avatar, # type: ignore
        "playerName": i.player_name,
        "playerUUID": i.player_uuid,
        "createTime": i.create_time,
        "expirationTime": i.expiration_time,
        "status": i.status,
    }

@guarantee.route("/request", methods=["POST"])
@login_required
def add_guarantee():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少信息！"})

    applicant_info = {
        "player_name": req_data.get("userInfo").get("playerName"),
        "player_uuid": req_data.get("userInfo").get("playerUUID"),
    }

    guarantor_info = {
        "player_name": req_data.get("guarantorInfo").get("playerName"),
        "player_uuid": req_data.get("guarantorInfo").get("playerUUID"),
    }

    checkGuarantorRes = checkGuarantor(guarantor_info)

    if checkGuarantorRes["code"] == 1:
        return jsonify(checkGuarantorRes)

    guarantor_id = checkGuarantorRes["guarantor_id"]

    checkApplicantRes = checkApplicant(applicant_info)

    if checkApplicantRes["code"] == 1:
        return jsonify(checkApplicantRes)

    _guarantee = Guarantee(
        guarantor_id,
        current_user.get_id(),
        applicant_info["player_name"],
        applicant_info["player_uuid"],
        datetime.now(timezone.utc),
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(_guarantee)
    db.session.commit()
    return jsonify({"code": 0, "desc": "担保请求提交成功，担保有效期1小时，过期后失效"})


@guarantee.route("/query_all", methods=["GET"])
@login_required
def query_all():
    response_data = {
        "code": 0,
        "desc": "yes",
        "data": {"guarantee": [], "applicant": []},
    }
    g_result = current_user.guarantees
    if len(g_result) != 0:
        for i in g_result:
            response_data["data"]["guarantee"].append(returnData(i))
    a_result = current_user.applicant
    if len(a_result) != 0:
        for i in a_result:
            response_data["data"]["applicant"].append(returnData(i))
    return jsonify(response_data)


@guarantee.route("/action", methods=["POST"])
@login_required
def guarantee_user_action():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "number"},
            "action": {"type": "string"},
        },
        "required": ["id", "action"]
    }
    try:
        validate(instance=request.json, schema=schema)
        # 处理合法数据的逻辑
        id: int = request.json["id"] # pyright: ignore
        action: str = request.json["action"] # pyright: ignore

        def is_expired(expiration_time: datetime) -> bool:
            expiration_time = expiration_time.replace(tzinfo=timezone.utc)
            current_datetime = datetime.now(timezone.utc)
            return current_datetime > expiration_time

        _guarantee: Guarantee | None = Guarantee.query.get(id)
        if _guarantee and not is_expired(_guarantee.expiration_time):
            if action == "reject":
                _guarantee.status = 2
                db.session.commit()
                return jsonify({"code": 0, "desc": "担保已拒绝！"})

            elif action == "accept":
                wl = Whitelist.query.filter_by(player_uuid=_guarantee.player_uuid).first()
                if wl is not None:
                    return jsonify({"code": 1, "desc": "此玩家存在已有白名单! "})

                db.session.add(Whitelist(
                        user_id=_guarantee.applicant_id,
                        player_name=_guarantee.player_name,
                        player_uuid=_guarantee.player_uuid,
                        source=1,
                        auditor_uid=current_user.id
                ))

                _guarantee.status = 1
                db.session.commit()
                return jsonify({"code": 0, "desc": "担保成功！白名单已添加"})

            else:
                return jsonify({"code": 1, "desc": "未知操作"})
        else:
            return jsonify({"code": 1, "desc": "担保不存在或过期"})

    except ValidationError:
        return jsonify({"code": 1, "desc": "数据有误"})

