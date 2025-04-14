from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from typing import cast
from myapp import db
from myapp.db_model import (
    Question,
    Response,
    Survey,
    User,
    ResponseScore,
)

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

    top_10_responses = (
        db.session.query(Response)
        .filter_by(user_id=user.id)
        .order_by(desc(Response.id))  # 按 id 降序排序
        .limit(10)  # 取前 10 条答卷
        .all()
    )

    response_data: list = []
    for res in top_10_responses:
        # 计算得分是多少
        # 如果是被批改完的卷子，就直接调取总分，否则计算一遍
        total_score: float = 0

        if res.archive_score is None:
            scores = ResponseScore.query.filter_by(response_id=res.id).all()
            total_score = sum(score.score for score in scores)  # 计算总分

        else:
            total_score = res.archive_score


        # 计算满分是多少
        questionnaire: list = Question.query.filter_by(survey_id=res.survey_id).all()
        full_score = sum(question.score for question in questionnaire)

        # 构造返回数据
        response_data.append(
            {
                "id": res.id,
                "survey_name": res.survey_name,
                "responseTime": res.response_time,
                "state": res.is_reviewed,
                "get_score": total_score,
                "full_score": full_score,
            }
        )

    return jsonify({"code": 0, "desc": "成功! ", "list": response_data})
