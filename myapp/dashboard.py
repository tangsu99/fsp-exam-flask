from datetime import UTC, datetime

from flask import Blueprint, jsonify
from flask_login import (
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import func, select

from myapp import db
from myapp.api import get_mc_users_info
from myapp.db_model import (
    Guarantee,
    GuaranteeStatus,
    Question,
    Response,
    ResponseStatus,
    Schematic,
    Survey,
    User,
    UserStatus,
    Whitelist,
)

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/usersInfo", methods=["GET"])
@login_required
def users_info():
    mc_data = get_mc_users_info()
    mc_data["user_count"] = db.session.scalar(select(func.count()).select_from(User))
    mc_data["user_w_list_count"] = db.session.scalar(select(func.count()).select_from(Whitelist))
    return jsonify({"data": mc_data})


@dashboard.route("/sysInfo", methods=["GET"])
@login_required
def sys_info():
    now = datetime.now(UTC)
    ban_count = db.session.scalar(
        select(func.count()).select_from(User).where(User.status.in_([UserStatus.TEMP_BANNED, UserStatus.PERM_BANNED]))
    )

    ban_whitelist_count = db.session.scalar(
        select(func.count())
        .select_from(Whitelist)
        .join(User, Whitelist.user_id == User.id)
        .where(User.status.in_([UserStatus.TEMP_BANNED, UserStatus.PERM_BANNED]))
    )

    response_not_reviewed_count = db.session.scalar(
        select(func.count())
        .select_from(Response)
        .where(Response.is_reviewed == ResponseStatus.PENDING, Response.is_completed.is_(False))
    )

    guarantee_not_passed_count = db.session.scalar(
        select(func.count())
        .select_from(Guarantee)
        .where(Guarantee.status == GuaranteeStatus.WAITING, Guarantee.expiration_time > now)
    )

    question_count = db.session.scalar(
        select(func.count()).select_from(Question).where(Question.logical_deletion.is_(False))
    )

    survey_count = db.session.scalar(select(func.count()).select_from(Survey))
    schematic_count = db.session.scalar(select(func.count()).select_from(Schematic))

    return jsonify(
        {
            "data": {
                "ban_wl_count": ban_whitelist_count or 0,
                "ban_count": ban_count or 0,
                "whitelist_block_count": 0,
                "response_not_reviewed_count": response_not_reviewed_count or 0,
                "guarantee_not_passed_count": guarantee_not_passed_count or 0,
                "question_count": question_count or 0,
                "survey_count": survey_count or 0,
                "schematic_count": schematic_count or 0,
            }
        }
    )
