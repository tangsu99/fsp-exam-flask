from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from myapp import db
from myapp.db_model import (
    Option,
    Question,
    Response,
    Survey,
    User,
    Whitelist,
    question_type_map,
)
from myapp.utils import required_role

admin = Blueprint("admin", __name__)


@admin.route("/")
@login_required
@required_role("admin")
def admin_index():
    return jsonify({"desc": "admin"})


@admin.route("/AllQuestion")
@login_required
@required_role("admin")
def all_question():
    result = Question.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    data = []
    for i in result:
        options = []
        for option in i.options:
            options.append({"text": option.option_text, "answer": option.is_correct})
        data.append(
            {
                "id": i.id,
                "title": i.question_text,
                "type": question_type_map[i.question_type],
                "score": i.score,
                "options": options,
            }
        )
        response_data.list = data
    return jsonify(response_data)


@admin.route("/addSurvey", methods=["POST"])
@login_required
@required_role("admin")
def add_survey():
    survey: Survey = Survey(request.json["name"], request.json["description"])
    db.session.add(survey)
    db.session.commit()
    print(survey.id)
    return jsonify({"code": 0, "desc": "成功"})


@admin.route("/addQuestion", methods=["POST"])
@login_required
@required_role("admin")
def add_question():
    req_data = request.json
    question: Question = Question(
        req_data["survey"],
        req_data["title"],
        req_data["type"],
        req_data["score"],
    )

    db.session.add(question)
    db.session.commit()
    options = req_data["options"]
    for i in options:
        option: Option = Option(question.id, i["option"], i["isAnswer"])
        db.session.add(option)
    db.session.commit()
    return jsonify({"code": 0, "desc": "成功"})


@admin.route("/whitelist", methods=["GET"])
@login_required
@required_role("admin")
def whitelist():
    result = Whitelist.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    for i in result:
        response_data["list"].append(
            {"id": i.id, "uid": i.user_id, "name": i.player_name, "uuid": i.player_uuid}
        )
    return jsonify(response_data)


@admin.route("/users", methods=["GET"])
@login_required
@required_role("admin")
def users():
    result = User.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    for i in result:
        response_data["list"].append(
            {
                "id": i.id,
                "username": i.username,
                "userQQ": i.user_qq,
                "role": i.role,
                "addtime": i.addtime,
                "avatar": i.avatar,
                "status": i.status,
            }
        )
    return jsonify(response_data)


@admin.route("/surveys", methods=["GET"])
@login_required
@required_role("admin")
def get_surveys():
    result = Survey.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    for i in result:
        response_data["list"].append(
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "createTime": i.create_time,
                "status": i.status,
            }
        )
    return jsonify(response_data)


@admin.route("/responses", methods=["GET"])
@login_required
@required_role("admin")
def get_responses():
    result = Response.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    for i in result:
        response_data["list"].append(
            {
                "id": i.id,
                "isCompleted": i.is_completed,
                "isReviewed": i.is_reviewed,
                "username": i.user.username,
                "survey": i.survey.name,
                "responseTime": i.response_time,
                "createTime": i.create_time,
            }
        )
    return jsonify(response_data)


@admin.route("/survey/<int:sid>", methods=["get"])
@login_required
@required_role("admin")
def get_survey(sid: int):
    # 查询指定问卷
    survey = Survey.query.get(sid)
    if not survey:
        return jsonify({"code": 1, "desc": "未找到问卷"}), 404
    # 构建问卷数据结构
    survey_data = {
        "id": survey.id,
        "name": survey.name,
        "description": survey.description,
        "create_time": survey.create_time,
        "status": survey.status,
        "questions": [],
    }
    # 查询问卷中的所有题目
    for question in survey.questions:
        question_data = {
            "id": question.id,
            "title": question.question_text,
            "type": question_type_map[question.question_type],
            "score": question.score,
            "options": [],
        }
        # 查询题目中的所有选项
        for option in question.options:
            question_data["options"].append(
                {"id": option.id, "text": option.option_text}
            )

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)
