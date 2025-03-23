from flask import Blueprint, jsonify, request
from flask_login import login_required

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
    return 'is query api'


@query.route("/response", methods=["GET"])
@login_required
def response():
    # 查询所有答卷记录
    responses = Response.query.all()

    response_data = []
    for res in responses:
        scores = ResponseScore.query.filter_by(response_id=res.id).all()
        total_score = sum(score.score for score in scores)  # 计算总分

        # 构造返回数据
        response_data.append({
            "id": res.id,
            "type": res.survey_res.type[0].type_name,
            "responseTime": res.response_time,
            "isReviewed": res.is_reviewed,
            "score": total_score
        })

    return jsonify({
        "code": 0,
        "desc": "成功! ",
        "list": response_data
    })
