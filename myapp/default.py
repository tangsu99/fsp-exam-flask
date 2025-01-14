from flask import Blueprint, jsonify, request
from myapp.db_model import Survey, Question, Option, question_type_map
from myapp import db

default = Blueprint('default', __name__)

@default.route("/addSurvey", methods=['POST'])
def add_survey():
    survey: Survey = Survey(request.json['name'], request.json['description'])
    db.session.add(survey)
    db.session.commit()
    print(survey.id)
    return jsonify({'code': 0, 'desc': '成功'})

@default.route("/survey/<int:id>", methods=['get'])
def get_survey(id: int):
# 查询指定问卷
    survey = Survey.query.get(id)
    if not survey:
        return jsonify({'code': 1, 'desc': '未找到问卷'}), 404
    # 构建问卷数据结构
    survey_data = {
        'id': survey.id,
        'name': survey.name,
        'description': survey.description,
        'create_time': survey.create_time,
        'status': survey.status,
        'questions': []
    }
    # 查询问卷中的所有题目
    for question in survey.questions:
        question_data = {
            'id': question.id,
            'title': question.question_text,
            'type': question_type_map[question.question_type],
            'score': question.score,
            'options': []
        }
        # 查询题目中的所有选项
        for option in question.options:
            question_data['options'].append(option.option_text)

        survey_data['questions'].append(question_data)

    return jsonify(survey_data)

@default.route("/addQuestion", methods=['POST'])
def add_question():
    req_data = request.json
    question: Question = Question(req_data['survey'], req_data['title'], req_data['score'], req_data['type'])
    db.session.add(question)
    db.session.commit()
    options = req_data['options']
    for i in options:
        option: Option = Option(question.id, i, i == req_data['answer'])
        db.session.add(option)
    db.session.commit()
    return jsonify({'code': 0, 'desc': '成功'})
