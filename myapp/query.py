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
        answer_sheet: list = ResponseScore.query.filter_by(response_id=res.id).all()
        total_score = sum(question.score for question in answer_sheet)  # 计算总分

        questionnaire: list = Question.query.filter_by(survey_id=res.survey_id).all()
        full_score = sum(question.score for question in questionnaire)

        # 确保 survey_res 和 type 数据加载正确
        survey_res: Survey = res.survey_res  # type: ignore
        if survey_res and survey_res.type:
            survey_type = survey_res.type[0].type_name if survey_res.type[0] else "Unknown"
        else:
            survey_type = "Unknown"

        # 构造返回数据
        response_data.append(
            {
                "id": res.id,
                "type": survey_type,
                "responseTime": res.response_time,
                "state": res.is_reviewed,
                "get_score": total_score,
                "full_score": full_score,
            }
        )

    return jsonify({"code": 0, "desc": "成功! ", "list": response_data})
