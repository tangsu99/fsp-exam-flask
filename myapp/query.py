from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from typing import cast
from myapp import db
from myapp.db_model import (
    Option,
    Question,
    Response,
    Survey,
    User,
    Whitelist,
    ResponseDetail,
    ResponseScore,
    QuestionType,
)

query = Blueprint("query", __name__)


@query.route("/", methods=["GET"])
@login_required
def index():
    return "is query api"


@query.route("/response", methods=["GET"])
@login_required
def response():
    user: User = cast(User, current_user)

    top_10_responses = (
        db.session.query(Response)
        .filter_by(user_id=user.id)
        .order_by(desc(Response.id))  # 按 id 降序排序
        .limit(10)  # 取前 10 条答卷
        .all()
    )

    response_data = []
    for res in top_10_responses:
        scores = ResponseScore.query.filter_by(response_id=res.id).all()
        total_score = sum(score.score for score in scores)  # 计算总分

        # 构造返回数据
        response_data.append(
            {
                "id": res.id,
                "type": res.survey_res.type[0].type_name,
                "responseTime": res.response_time,
                "isReviewed": res.is_reviewed,
                "score": total_score,
            }
        )

    return jsonify({"code": 0, "desc": "成功! ", "list": response_data})
