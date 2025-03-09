from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import User, Survey, question_type_map, Response, Whitelist, ResponseDetail, QuestionType, Question, \
    Option

default = Blueprint("default", __name__)


@default.route("/survey/<int:sid>", methods=["GET"])
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
            question_data["options"].append({"id": option.id, "text": option.option_text})

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)


def awa(response):
    for i in response:
        if i.is_completed is False:
            return i
    return None


@default.route('/start_survey', methods=['POST'])
@login_required
def start_survey():
    data = request.get_json()
    type_ = data["playerType"]
    user: User = current_user
    survey = QuestionType.query.filter_by(type_name=type_).first().survey_q

    mc_name = data.get("playerName")  # Minecraft 名称
    mc_uuid = data.get("playerUUID")  # Minecraft UUID

    if not all([survey, mc_name, mc_uuid]):
        return jsonify({"code": 2, "desc": "字段无效！"}), 400

    # 检查用户是否有未完成的答卷
    existing_response = user.responses
    res: Response = awa(existing_response)
    if res is not None:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.id}), 400

    # 创建新的答卷
    new_response = Response(
        user_id=user.id,
        survey_id=survey.id,
        player_name=mc_name,
        player_uuid=mc_uuid,
    )
    db.session.add(new_response)
    db.session.commit()

    print(new_response)

    return jsonify({
        "code": 0,
        "desc": "Survey started successfully",
        "response": new_response.id,
    }), 201


@default.route('/submit_response_detail', methods=['POST'])
@login_required
def submit_response_detail():
    data = request.get_json()
    user: User = current_user
    res: Response = awa(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "问卷未找到！"}), 400
    response_id = res.id  # 答卷ID
    question_id = data.get('questionId')  # 问题ID
    answer = data.get("answer")  # 用户答案

    if not all([response_id, question_id, answer]):
        return jsonify({"code": 2, "desc": "字段无效！"}), 400

    # 创建答题详情
    question: Question = Question.query.get(question_id)
    if question.question_type == 2: # 处理多选
        for i in answer:
            new_response_detail = ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=i,
            )
            db.session.add(new_response_detail)
    else:
        new_response_detail = ResponseDetail(
            response_id=response_id,
            question_id=question_id,
            answer=answer,
        )
        db.session.add(new_response_detail)
    db.session.commit()

    return jsonify({"desc": "成功！"}), 201


def count_s(li: list[ResponseDetail]):
    count = 0
    for item in li:
        option: Option = Option.query.get(int(item.answer))
        if option.is_correct:
            count += item.question_r_d.score
    return count

#
def count_m(li: list[int]):
    count = 0
    for item in li:
        question = Question.query.get(item)
        # todo 实现多选计分，错一个无分， 少选无分
    return count


@default.route('/complete_survey', methods=['POST'])
@login_required
def complete_survey():
    user: User = current_user
    res: Response = awa(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "问卷未找到！"}), 400

    # 标记答卷为已完成
    res.is_completed = True
    db.session.commit()

    # 计算选择与判断分数
    count_score = 0

    # 获取单选和多选
    ques_s = []
    ques_m = {}
    for item in res.response_details:
        if item.question_r_d.question_type == 1:
            ques_s.append(item)
        elif item.question_r_d.question_type == 2:
            ques_m[item.question_r_d.id] = item.question_r_d.id

    count_score += count_s(ques_s)
    # count_score += count_m(ques_m.)
    print(ques_s)
    print(ques_m)
    print(count_score)


    return jsonify({"code": 0, "desc": "提交成功！", "score": count_score}), 200
