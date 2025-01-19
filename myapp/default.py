from flask import Blueprint, jsonify
from myapp.db_model import Survey, question_type_map

default = Blueprint('default', __name__)


@default.route("/survey/<int:sid>", methods=['get'])
def get_survey(sid: int):
    # 查询指定问卷
    survey = Survey.query.get(sid)
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
            question_data['options'].append({
                'id': option.id,
                'text': option.option_text
            })

        survey_data['questions'].append(question_data)

    return jsonify(survey_data)
