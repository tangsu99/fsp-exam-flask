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
        "type": survey.type[0].type_name,
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
            if question.question_type == 3 or question.question_type == 4:
                question_data["options"].append({"id": option.id, "text": '此处作答'})
                continue
            question_data["options"].append({"id": option.id, "text": option.option_text})

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)


def awa(response):
    for i in response:
        if i.is_completed is False:
            return i
    return None


@default.route('/check_survey', methods=['POST'])
@login_required
def check_survey():
    user: User = current_user
    # 检查用户是否有未完成的答卷
    existing_response = user.responses
    res: Response = awa(existing_response)
    if res is not None:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})

    return jsonify({'code': 0, 'desc': '暂无问卷! '})


@default.route('/start_survey', methods=['POST'])
@login_required
def start_survey():
    user: User = current_user
    # 检查用户是否有未完成的答卷
    existing_response = user.responses
    res: Response = awa(existing_response)
    if res is not None:
        return jsonify({"code": 1, "desc": "您有未完成问卷！", "response": res.survey_id})

    data = request.get_json()
    type_ = data["playerType"]
    survey = QuestionType.query.filter_by(type_name=type_).first().survey_q

    mc_name = data.get("playerName")  # Minecraft 名称
    mc_uuid = data.get("playerUUID")  # Minecraft UUID

    if not all([survey, mc_name, mc_uuid]):
        return jsonify({"code": 2, "desc": "字段无效！"}), 400

    # 创建新的答卷
    new_response = Response(
        user_id=user.id,
        survey_id=survey.id,
        player_name=mc_name,
        player_uuid=mc_uuid,
    )
    db.session.add(new_response)
    db.session.commit()

    return jsonify({
        "code": 0,
        "desc": "问卷开始！",
        "response": new_response.id,
    }), 201


@default.route('/complete_survey', methods=['POST'])
@login_required
def complete_survey():
    data = request.get_json()
    user: User = current_user
    res: Response = awa(user.responses)
    if res is None:
        return jsonify({"code": 1, "desc": "问卷未找到！"}), 400
    response_id = res.id  # 答卷ID

    # 计算选择与判断分数
    count_score = 0

    for i in data:
        question_id = i.get('id')  # 问题ID
        answer = i.get("answer")  # 用户答案
        if answer is None:
            continue
        question: Question = Question.query.get(question_id)

        # 获取问题的正确选项
        correct_options = [option.id for option in question.options if option.is_correct]

        # 处理单选题
        if question.question_type == 1:  # 单选题
            if len(answer) == 1 and answer[0] in correct_options:
                count_score += question.score  # 答案正确，累加分数

        # 处理多选题
        elif question.question_type == 2:  # 多选题
            if set(answer) == set(correct_options):  # 用户答案与正确选项完全匹配
                count_score += question.score  # 答案正确，累加分数

        # 创建答题详情
        if question.question_type == 2:  # 处理多选
            for j in answer:
                new_response_detail = ResponseDetail(
                    response_id=response_id,
                    question_id=question_id,
                    answer=j,
                )
                db.session.add(new_response_detail)
        else:
            new_response_detail = ResponseDetail(
                response_id=response_id,
                question_id=question_id,
                answer=answer[0],
            )
            db.session.add(new_response_detail)

    # 标记答卷为已完成
    res.is_completed = True
    db.session.commit()

    return jsonify({"code": 0, "desc": "提交成功！", "score": count_score}), 200
