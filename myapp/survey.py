from datetime import datetime, timezone
from typing import cast

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import (
    Option,
    Question,
    QuestionCategory,
    QuestionType,
    Response,
    ResponseDetail,
    ResponseScore,
    Survey,
    User,
    Whitelist,
)

survey = Blueprint("survey", __name__)


@survey.route("/survey/<int:sid>", methods=["GET"])
@login_required
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
        "type": survey.type[0].type_name,
    }
    # 查询问卷中的所有题目
    for question in survey.questions:
        question_data = {
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "score": question.score,
            "img_list": [],
            "options": [],
        }

        for img in question.img_list:
            question_data["img_list"].append({"alt": img.img_alt, "data": img.img_data})

        # 查询题目中的所有选项
        for option in question.options:
            if question.question_type == 3 or question.question_type == 4:
                question_data["options"].append({"id": option.id, "text": "此处作答"})
                continue
            question_data["options"].append({"id": option.id, "text": option.option_text})

        survey_data["questions"].append(question_data)
    return jsonify(survey_data)


def awa(response):
    for i in response:
        if i.is_completed is False:
            return i
    return None


@survey.route("/check_survey", methods=["POST"])
@login_required
def check_survey():
    user: User = cast(User, current_user)
    # 检查用户是否有未完成的答卷
    existing_response = user.responses
    res: Response | None = awa(existing_response)

    if res is None:
        return jsonify({"code": 0, "desc": "暂无问卷! "})

    return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})


@survey.route("/start_survey", methods=["POST"])
@login_required
def start_survey():
    user: User = cast(User, current_user)
    # 检查用户是否有未完成的答卷
    existing_response = user.responses
    res: Response | None = awa(existing_response)
    if res is not None:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})

    data = request.get_json()
    type_ = data["playerType"]
    question_type = QuestionType.query.filter_by(type_name=type_).first()
    if question_type is None:
        return jsonify({"code": 4, "desc": "未找到指定的问卷类型！"}), 400

    mc_name = data.get("playerName")  # Minecraft 名称
    mc_uuid = data.get("playerUUID")  # Minecraft UUID

    wl = Whitelist.query.filter_by(player_uuid=mc_uuid).first()
    if wl is not None:
        return jsonify({"code": 2, "desc": "此玩家存在已有白名单! "})

    survey = question_type.survey_q

    if not all([survey, mc_name, mc_uuid]):
        return jsonify({"code": 1, "desc": "字段无效！"}), 400

    # 创建新的答卷
    new_response = Response(
        user_id=user.id,
        survey_id=survey.id,
        player_name=mc_name,
        player_uuid=mc_uuid,
    )
    db.session.add(new_response)
    db.session.commit()

    return (
        jsonify(
            {
                "code": 0,
                "desc": "问卷开始！",
                "response": new_response.survey_id,
            }
        ),
        201,
    )


def objective_question_scoring(user_response: list, question: Question) -> float:
    # 获取问题的正确选项,列表元素的值为正确选项的ID
    correct_options = [option.id for option in question.options if option.is_correct]

    if question.question_type == QuestionCategory.SINGLE_CHOICE.value:
        if user_response[0] in correct_options:
            return question.score

    elif question.question_type == QuestionCategory.MULTIPLE_CHOICE.value:
        if set(user_response) == set(correct_options):
            return question.score

    elif question.question_type == QuestionCategory.FILL_IN_THE_BLANKS.value:
        new_user_response: str = user_response[0]
        correct_answer_id: int = correct_options[0]
        option: Option | None = Option.query.get(correct_answer_id)
        if option is not None:
            correct_answer: str = option.option_text
            if new_user_response == correct_answer:
                return question.score

    # elif question.question_type == QuestionCategory.SUBJECTIVE.value:

    return 0


def make_answer_details(
    user_response: list[str], question: Question, response_id: int, question_id: int
) -> list[ResponseDetail]:
    if question.question_type == QuestionCategory.MULTIPLE_CHOICE.value:
        return [
            ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=answer,
            )
            for answer in user_response
        ]
    else:
        return [
            ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=user_response[0],
            )
        ]


@survey.route("/complete_survey", methods=["POST"])
@login_required
def complete_survey():
    data = request.get_json()
    user: User = cast(User, current_user)
    res: Response | None = awa(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "问卷未找到！"}), 400
    response_id: int = res.id  # 答卷ID

    # 客观题分数
    count_score: float = 0

    for i in data:
        question_id: int = i.get("id")  # 问题ID
        answer: list | None = i.get("answer")  # 用户答案

        # 允许空题
        if answer is None:
            continue

        question: Question | None = Question.query.get(question_id)

        if question is None:
            return jsonify({"code": 1, "desc": "题目未找到！"}), 400

        # 累加分数
        score_ = objective_question_scoring(answer, question)
        count_score += score_
        if score_ != 0:
            db.session.add(ResponseScore(question.score, question.id, response_id))
        else:
            db.session.add(ResponseScore(0, question.id, response_id))
        # 创建答题详情
        for detail in make_answer_details(answer, question, response_id, question_id):
            db.session.add(detail)

    # 标记答卷为已完成
    res.is_completed = True
    res.response_time = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"code": 0, "desc": "提交成功！", "score": count_score}), 200
