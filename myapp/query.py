from typing import Any, cast

from flask import Blueprint, jsonify
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import desc, select

from myapp import db
from myapp.db_model import (
    Response,
    User,
)
from myapp.survey_utils import get_response_total_score, get_survey_total_score
from myapp.utils import parse_dt_to_iso_utc

query = Blueprint("query", __name__)


@query.route("/", methods=["GET"])
@login_required
def index():
    return "is query api"


@query.route("/response", methods=["GET"])
@login_required
def response():
    """
    用户考试查询API
    """
    user: User = cast(User, current_user)

    stmt = select(Response).where(Response.user_id == user.id).order_by(desc(Response.id)).limit(10)
    top_10_responses = db.session.scalars(stmt)

    response_data: list[dict[str, Any]] = []
    for res in top_10_responses:
        get_score: float | None = res.archive_score

        if res.archive_score is None:
            get_score = get_response_total_score(res.id)

        full_score = get_survey_total_score(res.survey_id)

        # 构造返回数据
        response_data.append(
            {
                "id": res.id,
                "survey_name": res.survey_name,
                "responseTime": parse_dt_to_iso_utc(res.submit_time),
                "state": res.is_reviewed,
                "get_score": get_score,
                "full_score": full_score,
            }
        )

    return jsonify({"code": 0, "desc": "成功! ", "list": response_data})
