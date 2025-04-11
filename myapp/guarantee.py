from datetime import datetime, timezone, timedelta
from jsonschema import validate, ValidationError

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
        "expirationTime": i.expiration_time,
        "status": i.status,
    }

@guarantee.route("/request", methods=["POST"])
@login_required
@validate_json(required_fields=["userInfo", "guarantorInfo"])
def add_guarantee():
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

        def is_expired(create_time: str, expiration_time: str) -> bool:
            # 定义时间格式
            time_format = "%Y-%m-%d %H:%M:%S.%f"  # 包含微秒的时间格式

            # 解析时间字符串为 datetime 对象
            create_datetime = datetime.strptime(create_time, time_format)
            expiration_datetime = datetime.strptime(expiration_time, time_format)

            # 计算时间差
            time_difference = expiration_datetime - create_datetime

            # 判断时间差是否超过 1 小时（1小时 = 3600秒）
            return time_difference.total_seconds() > 3600

        _guarantee: Guarantee | None = Guarantee.query.get(id)
        if _guarantee and not is_expired(str(_guarantee.create_time), str(_guarantee.expiration_time)):
            if action == "reject":
                _guarantee.status = 2
                db.session.commit()
                return jsonify({"code": 0, "desc": "担保已拒绝！"})

            elif action == "accept":
                wl = Whitelist.query.filter_by(player_uuid=_guarantee.player_uuid).first()
                if wl is not None:
                    return jsonify({"code": 1, "desc": "此玩家存在已有白名单! "})

                db.session.add(Whitelist(_guarantee.applicant_id, _guarantee.player_name, _guarantee.player_uuid))
                _guarantee.status = 1
                db.session.commit()
                return jsonify({"code": 0, "desc": "担保成功！白名单已添加"})

            else:
                return jsonify({"code": 1, "desc": "未知操作"})
        else:
            return jsonify({"code": 1, "desc": "担保不存在或过期"})

    except ValidationError:
        return jsonify({"code": 1, "desc": "数据有误"})

