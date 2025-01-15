from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from myapp.db_model import Question, Survey, Option, question_type_map
from myapp import db

admin = Blueprint('admin', __name__)


@admin.route('/')
@login_required
def admin_index():
    return render_template('admin.html')


@admin.route('/AllQuestion')
@login_required
def all_question():
    result = Question.query.all()
    data = []
    for i in result:
        options = []
        for option in i.options:
            options.append({
                'text': option.option_text,
                'answer': option.is_correct
            })
        data.append({
            'id': i.id,
            'title': i.question_text,
            'type': question_type_map[i.question_type],
            'score': i.score,
            'options': options
        })
    return jsonify(data)


@admin.route("/addSurvey", methods=['POST'])
def add_survey():
    survey: Survey = Survey(request.json['name'], request.json['description'])
    db.session.add(survey)
    db.session.commit()
    print(survey.id)
    return jsonify({'code': 0, 'desc': '成功'})


@admin.route("/addQuestion", methods=['POST'])
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
