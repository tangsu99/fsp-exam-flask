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
from myapp.survey_utils import (
    build_dict_question,
    get_response_objective_question_score,
    is_survey_response_expired,
    make_answer_details,
)
from myapp.utils import parse_dt_to_iso_utc, status_check

survey = Blueprint("survey", __name__)


def incomplete_survey_exist(response_list: list[Response]) -> Response | None:
    for i in response_list:
        if not i.is_completed:
            if not is_survey_response_expired(i):
                return i
            i.is_completed = True
            i.is_reviewed = ResponseStatus.TIMEOUT
            db.session.flush()

    return None


def build_answer_survey(target_survey: Survey, create_time: datetime, end_time: datetime) -> dict[str, Any]:
    return {
        "id": target_survey.id,
        "name": target_survey.name,
        "description": target_survey.description,
        "startAnswerTime": parse_dt_to_iso_utc(create_time),
        "ddl": parse_dt_to_iso_utc(end_time),
        "questions": [
            build_dict_question("answer", question)
            for question in target_survey.questions
            if not question.logical_deletion
        ],
    }


@survey.route("/get_slots", methods=["GET"])
@login_required
def get_all_exam():
    """获取所有可选择的问卷"""
    stmt = select(SurveySlot)
    slots = db.session.execute(stmt).scalars().all()
    res_data = {
        "code": 0,
        "desc": "success",
        "data": [
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
    获取待作答问卷
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
            if i.survey_id != sid:
                return jsonify({"code": 1, "desc": "你选择的问卷不是这张！"})
            if end_time is None:
                return jsonify({"code": 5, "desc": "内部错误"}), 500
            break
    else:
        return jsonify({"code": 1, "desc": "没有要填写的问卷"})

    return jsonify({"code": 0, "desc": "ok", "data": build_answer_survey(survey_, create_time, end_time)})


@survey.route("/check_survey", methods=["POST"])
@login_required
def check_survey():
    user: User = cast(User, current_user)
    # 检查用户是否有未完成的答卷
    existing_response_list = user.responses
    res = incomplete_survey_exist(existing_response_list)

    if res:
        return jsonify({"code": 0, "desc": "您有未完成问卷！", "data": res.survey_id})

    return jsonify({"code": 1, "desc": "暂无未完成的问卷! "})


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
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "data": res.survey_id})

    data: dict[str, Any] | None = request.get_json(silent=True)

    if data is None:
        return jsonify({"code": 2, "desc": "缺少信息！"}), 400

    sid: int | None = data.get("sid", None)
    slot_name: str | None = data.get("slotName")
    mc_name: str | None = data.get("playerName")
    mc_uuid: str | None = data.get("playerUUID")

    if not sid or not slot_name or not mc_name or not mc_uuid:
        return jsonify({"code": 2, "desc": "缺少信息！"}), 400

    is_in_whitelist = db.session.scalar(select(exists().where(Whitelist.player_uuid == mc_uuid)))
    if is_in_whitelist:
        return jsonify({"code": 2, "desc": "此玩家存在已有白名单! "})

    survey_exist = db.session.get(Survey, sid)
    if survey_exist is None:
        return jsonify({"code": 2, "desc": "问卷不存在！"})

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
            "desc": "开始作答！",
            "data": new_response.survey_id,
        }
    )


@survey.route("/complete_survey", methods=["POST"])
@login_required
def complete_survey():
    """
    用户交卷接口
    """
    req_data: dict[str, Any] | None = request.get_json(silent=True)

    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少数据！"}), 400

    user: User = cast(User, current_user)
    res: Response | None = incomplete_survey_exist(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "你没有要提交的问卷！"})

    survey_id: int | None = req_data.get("surveyId", None)
    answers: list[Any] | None = req_data.get("answers", None)

    if not survey_id or not answers:
        return jsonify({"code": 1, "desc": "缺少数据！"}), 400

    if survey_id != res.survey_id:
        return jsonify({"code": 1, "desc": "提交的问卷ID与系统记录不符！"})

    # 客观题分数
    count_score: float = 0
    response_id: int = res.id

    for i in answers:
        question_id: int | None = i.get("id", None)
        answer: list[str] | None = i.get("answer", None)

        # 允许空题
        if answer is None or question_id is None:
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
    now: datetime = datetime.now(UTC)
    res.is_completed = True
    res.submit_time = now
    db.session.commit()

    send_survey_complete(user.username, now.isoformat(), response_id)

    return jsonify({"code": 0, "desc": "提交成功！", "data": count_score})


def send_survey_complete(username: str, response_time: str, id_: int):
    with APP.app_context():
        stmt = select(User).filter_by(role="admin")
        admins = db.session.scalars(stmt).all()
        if not admins:
            return

        admin_mails = [f"{admin.user_qq}@qq.com" for admin in admins]
        msg = survey_complete_mail(admin_mails, username, response_time, id_)
        send_mail(APP, msg)
