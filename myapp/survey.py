from datetime import UTC, datetime, timedelta
from typing import Any, cast

from flask import Blueprint, current_app, jsonify, request
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import exists, select

from myapp import APP, db
from myapp.db_model import (
    Question,
    Response,
    ResponseScore,
    ResponseStatus,
    Survey,
    SurveySlot,
    User,
    Whitelist,
)
from myapp.mail import send_mail, survey_complete_mail
from myapp.survey_utils import get_response_objective_question_score, is_survey_response_expired, make_answer_details
from myapp.utils import parse_dt_to_iso_utc, status_check

survey = Blueprint("survey", __name__)


def incomplete_survey_exist(response_list: list[Response]) -> Response | None:
    for i in response_list:
        if not i.is_completed:
            if not is_survey_response_expired(i):
                return i
            i.is_completed = True
            i.is_reviewed = ResponseStatus.REJECTED
            db.session.flush()

    return None


def build_survey_questions(survey_: Survey) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for question in survey_.questions:
        if question.logical_deletion:
            continue

        options_data = [
            {"id": opt.id, "text": "此处作答" if question.question_type in (3, 4) else opt.option_text}
            for opt in question.options
        ]

        question_data = {
            "display_order": question.display_order,
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "score": question.score,
            "img_list": [{"alt": img.img_alt, "data": img.img_data} for img in question.img_list],
            "options": options_data,
        }

        questions.append(question_data)

    return questions


@survey.route("/get_slots", methods=["GET"])
@login_required
def get_all_exam():
    """获取所有可选择的问卷"""
    stmt = select(SurveySlot)
    slots = db.session.execute(stmt).scalars().all()
    res_data = {
        "code": 0,
        "desc": "成功! ",
        "list": [
            {
                "id": slot.id,
                "slotName": slot.slot_name,
                "mountedSID": slot.mounted_survey_id,
            }
            for slot in slots
        ],
    }

    return jsonify(res_data)


@survey.route("/survey/<int:sid>", methods=["GET"])
@login_required
def get_survey(sid: int):
    """
    获取问卷
    """
    user: User = cast(User, current_user)

    survey_ = db.session.get(Survey, sid)
    if not survey_:
        return jsonify({"code": 1, "desc": "未找到问卷"})

    existing_response_list = user.responses
    for i in existing_response_list:
        if not i.is_completed:
            create_time = i.create_time
            end_time = i.end_time
            break
    else:
        return jsonify({"code": 1, "desc": "没有要填写的问卷"})

    survey_data: dict[str, Any] = {
        "id": survey_.id,
        "name": survey_.name,
        "description": survey_.description,
        "create_time": parse_dt_to_iso_utc(create_time),
        "ddl": parse_dt_to_iso_utc(end_time),
        "questions": build_survey_questions(survey_),
    }

    return jsonify(survey_data)


@survey.route("/check_survey", methods=["POST"])
@login_required
def check_survey():
    user: User = cast(User, current_user)
    # 检查用户是否有未完成的答卷
    existing_response_list = user.responses
    res = incomplete_survey_exist(existing_response_list)

    if res:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})

    return jsonify({"code": 0, "desc": "暂无问卷! "})


@survey.route("/start_survey", methods=["POST"])
@login_required
@status_check()
def start_survey():
    """
    创建答卷
    """
    user: User = cast(User, current_user)

    # 检查用户是否有未完成的答卷
    existing_response_list = user.responses
    res: Response | None = incomplete_survey_exist(existing_response_list)

    if res:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})

    data = request.get_json()

    sid: int = data.get("sid")
    slot_name: str = data.get("slot_name")
    mc_name: str = data.get("playerName")
    mc_uuid: str = data.get("playerUUID")

    if not sid or not slot_name or not mc_name or not mc_uuid:
        return jsonify({"code": 1, "desc": "缺少信息！"})

    is_in_whitelist = db.session.scalar(select(exists().where(Whitelist.player_uuid == mc_uuid)))
    if is_in_whitelist:
        return jsonify({"code": 2, "desc": "此玩家存在已有白名单! "})

    survey_exist = db.session.get(Survey, sid)
    if survey_exist is None:
        return jsonify({"code": 1, "desc": "问卷不存在！"})

    new_response = Response(
        user_id=user.id,
        survey_id=sid,
        survey_name=slot_name,
        player_name=mc_name,
        player_uuid=mc_uuid,
    )

    db.session.add(new_response)
    db.session.flush()

    val = cast(int, current_app.config["RESPONSE_VALIDITY_PERIOD"])
    validity_period = timedelta(hours=val)
    new_response.end_time = new_response.create_time + validity_period

    db.session.commit()

    return jsonify(
        {
            "code": 0,
            "desc": "问卷开始！",
            "response": new_response.survey_id,
        }
    )


@survey.route("/complete_survey", methods=["POST"])
@login_required
def complete_survey():
    """
    交卷
    """
    data = request.get_json()
    user: User = cast(User, current_user)
    res: Response | None = incomplete_survey_exist(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "你没有要提交的问卷！"})

    response_id: int = res.id

    # 客观题分数
    count_score: float = 0

    for i in data:
        question_id: int = i.get("id")
        answer: list[str] | None = i.get("answer")

        # 允许空题
        if answer is None:
            continue

        question = db.session.get(Question, question_id)

        # 如果这道题已经被删除，就算了
        if question is None:
            continue

        # 累加分数
        score_ = get_response_objective_question_score(answer, question)
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
    res.submit_time = datetime.now(UTC)
    db.session.commit()

    send_survey_complete(user.username, res.submit_time.replace(tzinfo=UTC).isoformat(), res.id)

    return jsonify({"code": 0, "desc": "提交成功！", "score": count_score}), 200


def send_survey_complete(username: str, response_time: str, id_: int):
    with APP.app_context():
        stmt = select(User).filter_by(role="admin")
        admins = db.session.scalars(stmt).all()
        if not admins:
            return

        admin_mails = [f"{admin.user_qq}@qq.com" for admin in admins]
        msg = survey_complete_mail(admin_mails, username, response_time, id_)
        send_mail(APP, msg)
