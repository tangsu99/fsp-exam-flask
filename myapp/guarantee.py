from datetime import UTC, datetime, timedelta
from typing import Any, cast

from flask import Blueprint, jsonify, request
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import select

from myapp import APP, db
from myapp.db_model import Guarantee, GuaranteeStatus, User, Whitelist, WhitelistType
from myapp.mail import guarantee_result_mail, send_mail
from myapp.utils import parse_dt_to_iso_utc, status_check

guarantee = Blueprint("guarantee", __name__)


def is_expired(expiration_time: datetime) -> bool:
    expiration_time = expiration_time.replace(tzinfo=UTC)
    current_datetime = datetime.now(UTC)
    return current_datetime > expiration_time


def is_player_in_whitelist(player_uuid: str) -> Whitelist | None:
    return db.session.scalar(select(Whitelist).where(Whitelist.player_uuid == player_uuid))


def check_guarantor(info: dict[str, Any]) -> dict[str, Any]:
    player_uuid: str = info.get("player_uuid", "")
    player = is_player_in_whitelist(player_uuid)
    if not player:
        return {"code": 1, "desc": "担保人不属于白名单成员，无法担保！"}

    user_result: User | None = db.session.get(User, player.user_id)

    if user_result is None:
        return {"code": 1, "desc": "担保人账户不存在"}

    if user_result.status != 1:
        return {"code": 1, "desc": "担保人账户状态异常，无法担保！"}

    return {"code": 0, "guarantor_id": user_result.id}


def check_applicant(info: dict[str, Any]) -> dict[str, Any]:
    player_uuid = info.get("player_uuid", "")

    if is_player_in_whitelist(player_uuid):
        return {"code": 1, "desc": "你已经是白名单成员"}

    g_result = db.session.scalars(
        select(Guarantee).where(
            Guarantee.player_uuid == info.get("player_uuid"),
            Guarantee.status == GuaranteeStatus.WAITING,
        )
    )

    for i in g_result:
        # 如果有未过期的
        if datetime.now(UTC) < i.expiration_time.replace(tzinfo=UTC):
            return {"code": 1, "desc": "存在未过期的担保！个人中心担保查询里查看进度"}

    return {"code": 0}


def build_trust_chain(player_uuid: str, max_depth: int = 10) -> list[dict[str, Any]]:
    """
    Build a trust chain list.
    Returns: [{"guarantor": {...}, "applicant": {...}}, ...]
             Ordered from direct guarantor -> top-level guarantor.
    """
    chain: list[dict[str, Any]] = []
    visited_user_ids: set[int] = set()

    whitelist_entry = db.session.scalar(select(Whitelist).where(Whitelist.player_uuid == player_uuid))
    if not whitelist_entry or not whitelist_entry.user_id:
        return chain

    current_applicant_id = whitelist_entry.user_id
    visited_user_ids.add(current_applicant_id)

    depth = 0
    while depth < max_depth:
        guarantee = db.session.scalar(select(Guarantee).where(Guarantee.applicant_id == current_applicant_id))
        if not guarantee:
            break

        guarantor = guarantee.guarantor
        applicant = guarantee.applicant_user

        if guarantor.id in visited_user_ids:
            chain.append(
                {
                    "guarantor": {
                        "id": guarantor.id,
                        "username": guarantor.username,
                        "user_qq": guarantor.user_qq,
                        "avatar": guarantor.avatar,
                        "warning": "Circular guarantee detected",
                    },
                    "applicant": {
                        "id": applicant.id,
                        "username": applicant.username,
                        "user_qq": applicant.user_qq,
                        "avatar": applicant.avatar,
                    },
                }
            )
            break

        chain.append(
            {
                "guarantor": {
                    "id": guarantor.id,
                    "username": guarantor.username,
                    "user_qq": guarantor.user_qq,
                    "avatar": guarantor.avatar,
                },
                "applicant": {
                    "id": applicant.id,
                    "username": applicant.username,
                    "user_qq": applicant.user_qq,
                    "avatar": applicant.avatar,
                },
            }
        )

        visited_user_ids.add(guarantor.id)
        current_applicant_id = guarantor.id
        depth += 1

    return chain


def return_data(i: Guarantee):
    return {
        "uid": i.applicant_user.id,
        "id": i.id,
        "username": i.applicant_user.username,
        "userQQ": i.applicant_user.user_qq,
        "avatar": i.applicant_user.avatar,
        "playerName": i.player_name,
        "playerUUID": i.player_uuid,
        "createTime": parse_dt_to_iso_utc(i.create_time),
        "expirationTime": parse_dt_to_iso_utc(i.expiration_time),
        "status": i.status,
    }


@guarantee.route("/request", methods=["POST"])
@login_required
@status_check()
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

    check_guarantor_res = check_guarantor(guarantor_info)

    if check_guarantor_res["code"] == 1:
        return jsonify(check_guarantor_res)

    guarantor_id = check_guarantor_res["guarantor_id"]

    check_applicant_res = check_applicant(applicant_info)

    if check_applicant_res["code"] == 1:
        return jsonify(check_applicant_res)

    expiration: int = cast(int, APP.config["GUARANTEE_EXPIRATION"])

    _guarantee = Guarantee(
        guarantee_id=guarantor_id,
        applicant_id=current_user.id,
        player_name=applicant_info["player_name"],
        player_uuid=applicant_info["player_uuid"],
        expiration_time=datetime.now(UTC) + timedelta(hours=expiration),
    )

    db.session.add(_guarantee)
    db.session.commit()
    return jsonify(
        {
            "code": 0,
            "desc": (
                f"有效期{expiration}小时，超时失效，"
                f"{expiration}小时内不可再申请新的担保请求，"
                "除非对方手动拒绝或同意，担保结果会发往您的qq邮箱。"
            ),
        }
    )


@guarantee.route("/query_all", methods=["GET"])
@login_required
def query_all():
    response_data: dict[str, Any] = {
        "code": 0,
        "desc": "yes",
        "data": {"guarantee": [], "applicant": []},
    }
    g_result = current_user.guarantees
    if len(g_result) != 0:
        for i in g_result:
            response_data["data"]["guarantee"].append(return_data(i))
    a_result = current_user.applicant_guarantees
    if len(a_result) != 0:
        for i in a_result:
            response_data["data"]["applicant"].append(return_data(i))
    return jsonify(response_data)


@guarantee.route("/action", methods=["POST"])
@login_required
def guarantee_user_action():
    """
    操作用户担保
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"code": 1, "desc": "缺少数据！"})

    _id = data.get("id")
    action = data.get("action")

    if _id is None or action is None:
        return jsonify({"code": 1, "desc": "缺少数据！"})

    if not isinstance(_id, int) or not isinstance(action, str):
        return jsonify({"code": 1, "desc": "参数类型错误！"})

    _guarantee: Guarantee | None = db.session.get(Guarantee, _id)
    if _guarantee and not is_expired(_guarantee.expiration_time):
        if action == "reject":
            _guarantee.status = GuaranteeStatus.REFUSE
            db.session.commit()

            mail_msg = guarantee_result_mail(
                [_guarantee.applicant_user.user_qq + "@qq.com"], _guarantee.guarantor.username, False
            )
            send_mail(APP, mail_msg)

            return jsonify({"code": 0, "desc": "担保已拒绝！"})

        elif action == "accept":
            if is_player_in_whitelist(_guarantee.player_uuid):
                return jsonify({"code": 1, "desc": "此玩家存在已有白名单! "})

            db.session.add(
                Whitelist(
                    user_id=_guarantee.applicant_id,
                    player_name=_guarantee.player_name,
                    player_uuid=_guarantee.player_uuid,
                    source=WhitelistType.GUARANTEE,
                    auditor_uid=current_user.id,
                )
            )

            _guarantee.status = GuaranteeStatus.AGREEMENT
            db.session.commit()

            mail_msg = guarantee_result_mail(
                [_guarantee.applicant_user.user_qq + "@qq.com"], _guarantee.guarantor.username, True
            )
            send_mail(APP, mail_msg)

            return jsonify({"code": 0, "desc": "担保成功！白名单已添加"})

        else:
            return jsonify({"code": 1, "desc": "未知操作"})
    else:
        return jsonify({"code": 1, "desc": "担保不存在或过期"})
