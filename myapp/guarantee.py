from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from mj_api import get_player_uuid
from myapp import db
from myapp.db_model import Guarantee, User, Whitelist
from myapp.validate_json import validate_json

guarantee = Blueprint("guarantee", __name__)


def get_ago_time() -> datetime:
    time: datetime = datetime.now(timezone.utc) - timedelta(minutes=10)
    return time


def checkGuarantor(info: dict) -> dict:
    wl_result = Whitelist.query.filter_by(player_uuid=info["player_uuid"]).first()

    if wl_result is None:
        return {"code": 1, "desc": "担保人不属于白名单成员，无法担保！"}

    user_result = User.query.get(wl_result.user_id)
    if user_result.status != 1:
        return {"code": 1, "desc": "担保人账户状态异常，无法担保！"}

    return {"code": 0, "guarantor_id": user_result.id}


def checkApplicant(info: dict) -> dict:
    wl_result = Whitelist.query.filter_by(player_uuid=info["player_uuid"]).first()

    if wl_result:
        return {"code": 1, "desc": "你已经是白名单成员"}

    ten_minutes_ago = get_ago_time()

    g_result = Guarantee.query.filter(
        Guarantee.player_uuid == info["player_uuid"],
        Guarantee.create_time >= ten_minutes_ago,
    ).all()

    if len(g_result) != 0:
        return {"code": 1, "desc": "存在未过期的担保！"}

    # 前端已经验证过了，感觉这段代码不需要
    # _res = get_player_uuid(info["playerName"])
    #
    # if _res is None:
    #     return {"code": 1, "desc": "被担保玩家名不存在"}

    return {"code": 0}


@guarantee.route("/request", methods=["POST"])
@login_required
@validate_json(required_fields=["userInfo", "guarantorInfo"])
def _request():
    applicant_info = {
        "player_name": request.json["userInfo"]["playerName"],
        "player_uuid": request.json["userInfo"]["playerUUID"],
    }

    guarantor_info = {
        "player_name": request.json["guarantorInfo"]["playerName"],
        "player_uuid": request.json["guarantorInfo"]["playerUUID"],
    }

    checkGuarantorRes = checkGuarantor(guarantor_info)

    if checkGuarantorRes["code"] == 1:
        return jsonify(checkGuarantorRes)

    guarantor_id = checkGuarantorRes["guarantor_id"]

    checkApplicantRes = checkApplicant(applicant_info)

    if checkApplicantRes["code"] == 1:
        return jsonify(checkApplicantRes)

    _guarantee = Guarantee(
        guarantor_id, current_user.get_id(), applicant_info["player_name"], applicant_info["player_uuid"]
    )
    db.session.add(_guarantee)
    db.session.commit()
    return jsonify({"code": 0, "desc": "担保请求提交成功，担保有效期1小时，过期后失效"})


@guarantee.route("/query", methods=["GET"])
@login_required
def query():
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


def returnData(i: Guarantee):
    return {
        "uid": i.applicant.id,
        "id": i.id,
        "username": i.applicant.username,
        "userQQ": i.applicant.user_qq,
        "avatar": i.applicant.avatar,
        "playerName": i.player_name,
        "playerUUID": i.player_uuid,
        "createTime": i.create_time,
        "status": i.status,
    }
