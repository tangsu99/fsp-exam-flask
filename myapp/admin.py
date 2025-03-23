from flask import Blueprint, jsonify, request
from flask_login import login_required

from myapp import db
from myapp.db_model import (
    Option,
    Question,
    Response,
    Survey,
    User,
    Whitelist, ResponseDetail, ResponseScore, QuestionType,
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
                "type": i.question_type,
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
    name = request.json["name"]
    description = request.json["description"]
    survey: Survey = Survey(name, description)
    db.session.add(survey)
    db.session.commit()
    print(survey.id)
    return jsonify({"code": 0, "desc": "成功"})


@admin.route("/addQuestion", methods=["POST"])
@login_required
@required_role("admin")
def add_question():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "失败"})

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


@admin.route("/whitelist", methods=["POST"])
@login_required
@required_role("admin")
def add_whitelist():
    req_data = request.json
    if req_data is None:
        return jsonify({"desc": "错误!"})
    for i in req_data:
        wl = Whitelist(i.get('name'), i.get('uuid'))
        db.session.add(wl)
    db.session.commit()
    return jsonify({"desc": "成功!"})



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
        scores = ResponseScore.query.filter_by(response_id=i.id).all()
        total_score = sum(score.score for score in scores)  # 计算总分
        response_data["list"].append(
            {
                "id": i.id,
                "isCompleted": i.is_completed,
                "isReviewed": i.is_reviewed,
                "username": i.user.username,
                "playername": i.player_name,
                "survey": i.survey_res.name,
                "score": total_score,
                "surveyId": i.survey_res.id,
                "responseTime": i.response_time,
                "createTime": i.create_time,
            }
        )
    return jsonify(response_data)


@admin.route("/survey/<int:sid>", methods=["GET"])
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
            "type": question.question_type,
            "score": question.score,
            "options": [],
        }
        # 查询题目中的所有选项
        for option in question.options:
            question_data["options"].append(
                {
                    "id": option.id,
                    "text": option.option_text,
                    "isCorrect": option.is_correct,
                }
            )

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)


@admin.route("/reviewed", methods=["POST"])
@login_required
@required_role("admin")
def reviewed_response():
    req_data = request.json
    rid = req_data.get("response")
    resp: Response = Response.query.get(rid)
    if resp is None:
        return jsonify({"code": 1, "desc": "未找到! "})
    resp.is_reviewed = True
    wl = Whitelist(resp.user_id, resp.player_name, resp.player_uuid)
    db.session.add(wl)
    db.session.commit()
    return jsonify({"code": 0, "desc": "通过! "})


@admin.route("/detail/<int:resp_id>", methods=["GET"])
@login_required
@required_role("admin")
def get_detail(resp_id: int):
    res: Response = Response.query.get(resp_id)
    # 查询指定问卷
    survey = Survey.query.get(res.survey_id)
    if not survey:
        return jsonify({"code": 1, "desc": "未找到问卷"}), 404
    survey_data = {
        "id": res.id,
        "name": survey.name,
        "description": survey.description,
        "create_time": survey.create_time,
        "status": survey.status,
        "questions": [],
        "type": survey.type[0].type_name,
    }
    # 查询问卷中的所有题目
    for question in survey.questions:
        question_data = {
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "score": question.score,
            "options": [],
            "answer": [],
            "countScore": ResponseScore.query.filter_by(question_id=question.id, response_id=resp_id).first().score,
        }
        for option in question.options:
            question_data["options"].append(
                {"id": option.id, "text": option.option_text, "isCorrect": option.is_correct}
            )

        # 查询题目中的所有选项详情
        details: list[ResponseDetail] = ResponseDetail.query.filter_by(question_id=question.id, response_id=resp_id)
        for detail in details:
            question_data["answer"].append(
                {"id": detail.id, "text": detail.answer}
            )

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)


@admin.route("/detail_score", methods=["POST"])
@login_required
@required_role("admin")
def set_score():
    req_data = request.json
    score = req_data.get("score")
    question_id = req_data.get("questionId")
    response_id = req_data.get("responseId")
    if not all([score, response_id, question_id]):
        return jsonify({"code": 2, "desc": "字段无效！"}), 400
    res = ResponseScore.query.filter_by(question_id=question_id, response_id=response_id).first()
    if res is not None:
        res.score = score
    else:
        db.session.add(ResponseScore(score, question_id, response_id))
    db.session.commit()
    return jsonify({"code": 0, "desc": "更改成功！"})


@admin.route("/question_type", methods=["GET"])
@login_required
@required_role("admin")
def get_all_question_type():
    res: list[QuestionType] = QuestionType.query.all()

    res_data = {
        "code": 0,
        "desc": "成功! ",
        "list": [],
    }

    for i in res:
        res_data.get("list").append({
            "id": i.id,
            "typeName": i.type_name,
            "surveyId": i.survey_id,
        })

    return jsonify(res_data)


@admin.route("/question_type", methods=["PUT"])
@login_required
@required_role("admin")
def set_question_type():
    req_data = request.json
    id_ = req_data.get("id")
    survey_id = req_data.get("surveyId")
    type_name = req_data.get("typeName")

    if Survey.query.get(id_) is None:
        return jsonify({
            "code": 1,
            "desc": "未找到问卷！"
        })

    res: QuestionType = QuestionType.query.filter_by(id=id_).first()
    if res is None:
        return jsonify({
            "code": 1,
            "desc": "未找到类型！"
        })
    res.type_name = type_name
    res.survey_id = survey_id

    db.session.commit()

    res_data = {
        "code": 0,
        "desc": "成功! ",
    }

    return jsonify(res_data)
