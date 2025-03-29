from flask import Blueprint, jsonify, request
from flask_login import login_required
from flask_sqlalchemy import pagination
from sqlalchemy.engine import result

from myapp import db
from myapp.db_model import (
    Option,
    Question,
    Response,
    Survey,
    User,
    Whitelist,
    ResponseDetail,
    ResponseScore,
    QuestionType,
)
from myapp.utils import required_role, check_password

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
        response_data["list"] = data
    return jsonify(response_data)


@admin.route("/addSurvey", methods=["POST"])
@login_required
@required_role("admin")
def add_survey():
    if request.json:
        name = request.json["name"]
        description = request.json["description"]
        survey: Survey = Survey(name, description)
        db.session.add(survey)
        db.session.commit()
        return jsonify({"code": 0, "desc": "成功"})
    return jsonify({"code": 1, "desc": "失败"})


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
    page = request.args.get("page", 1, type=int)  # 获取页码，默认为 1
    per_page = request.args.get("size", 10, type=int)  # 获取每页条数，默认为 10

    # 分页查询白名单
    pagination = Whitelist.query.paginate(page=page, per_page=per_page, error_out=False)
    result = pagination.items

    # 构造返回数据
    response_data = {"code": 0, "desc": "success", "list": []}
    for i in result:
        response_data["list"].append(
            {"id": i.id, "uid": i.user_id, "name": i.player_name, "uuid": i.player_uuid}
        )

    # 添加分页信息
    response_data["page"] = pagination.page
    response_data["size"] = pagination.per_page
    response_data["total"] = pagination.total

    return jsonify(response_data)


# @admin.route("/whitelist", methods=["POST"])
# @login_required
# @required_role("admin")
# def add_whitelist():
#     req_data = request.json
#     if req_data is None:
#         return jsonify({"desc": "错误!"})
#     for i in req_data:
#         name = i.get("name")
#         uuid = i.get("uuid")
#         wl = Whitelist(name=name, uuid=uuid)
#         db.session.add(wl)
#     db.session.commit()
#     return jsonify({"desc": "成功!"})


@admin.route("/users", methods=["GET"])
@login_required
@required_role("admin")
def users():
    page = request.args.get("page", 1, type=int)  # 获取页码，默认为 1
    per_page = request.args.get("size", 10, type=int)  # 获取每页条数，默认为 10

    # 分页查询用户
    query = User.query.filter(User.status != 4)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    # 构造返回数据
    user_data = []
    for user in users:
        user_data.append(
            {
                "id": user.id,
                "username": user.username,
                "user_qq": user.user_qq,
                "role": user.role,
                "status": user.status,
                "addtime": user.addtime.isoformat() if user.addtime else None,
                "avatar": user.avatar,
            }
        )

    return jsonify(
        {
            "code": 0,
            "desc": "success",
            "list": user_data,
            "page": pagination.page,
            "size": pagination.per_page,
            "total": pagination.total,
        }
    )


@admin.route("/user", methods=["GET"])
@login_required
@required_role("admin")
def get_user():
    id_ = request.args.get("id", 0, type=int)
    user: User | None = User.query.get(id_)
    if user is None:
        return jsonify({"code": 1, "desc": "未找到用户！"}), 400
    return jsonify(
        {
            "code": 0,
            "desc": "success",
            "data": {
                "id": user.id,
                "username": user.username,
                "user_qq": user.user_qq,
                "role": user.role,
                "status": user.status,
                "addtime": user.addtime.isoformat() if user.addtime else None,
                "avatar": user.avatar,
            },
        }
    )


@admin.route("/user", methods=["POST"])
@login_required
@required_role("admin")
def add_user():
    req_data = request.json

    if req_data:
        username: str | None = req_data.get("username")
        user_qq: str | None = req_data.get("userQQ")
        role: str | None = req_data.get("role")
        password: str | None = req_data.get("password")

        # 校验必填字段
        if not username or not user_qq or not role or not password:
            return jsonify({"code": 1, "desc": "缺少必填字段！"}), 400

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({"code": 2, "desc": "用户名已存在！"}), 400

        # 创建用户
        new_user = User(username=username, user_qq=user_qq, role=role).set_password(
            password
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"code": 0, "desc": "用户创建成功！"})
    return jsonify({"code": 1, "desc": "缺少必填字段！"}), 400


@admin.route("/user", methods=["PUT"])
@login_required
@required_role("admin")
def set_user():
    req_data = request.json
    if req_data:
        user_id = req_data.get("id")
        username = req_data.get("username")
        password = req_data.get("password")
        user_qq = req_data.get("userQQ")
        role = req_data.get("role")
        status = req_data.get("status")

        # 校验必填字段
        if not user_id:
            return jsonify({"code": 1, "desc": "缺少用户ID！"}), 400

        # 查询用户
        user = User.query.get(user_id)
        if not user:
            return jsonify({"code": 2, "desc": "用户不存在！"}), 404

        # 更新用户信息
        if username:
            user.username = username
        if password is not None and check_password(password):
            user.set_password(password)
        if user_qq:
            user.user_qq = user_qq
        if role:
            user.role = role
        if status is not None:
            user.status = status

        db.session.commit()

        return jsonify({"code": 0, "desc": "用户信息更新成功！"})
    return jsonify({"code": 1, "desc": "缺少信息"}), 400


@admin.route("/user", methods=["DELETE"])
@login_required
@required_role("admin")
def del_user():
    req_data = request.json
    if req_data:
        user_id = req_data.get("id")

        # 校验必填字段
        if not user_id:
            return jsonify({"code": 1, "desc": "缺少用户ID！"}), 400

        # 查询用户
        user: User | None = User.query.get(user_id)
        if not user:
            return jsonify({"code": 2, "desc": "用户不存在！"}), 404

        # 删除用户，逻辑删除
        user.status = 4
        # db.session.delete(user)
        db.session.commit()

        return jsonify({"code": 0, "desc": "用户删除成功！"})
    return jsonify({"code": 1, "desc": "缺少信息"})


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
    page = request.args.get("page", 1, type=int)  # 获取页码，默认为 1
    per_page = request.args.get("size", 10, type=int)  # 获取每页条数，默认为 10

    pagination = Response.query.paginate(page=page, per_page=per_page, error_out=False)
    result = pagination.items

    response_data = {
        "code": 0,
        "desc": "yes",
        "list": [],
        "page": pagination.page,
        "size": pagination.per_page,
        "total": pagination.total,
    }
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
    if req_data:
        rid = req_data.get("response")
        resp: Response | None = Response.query.get(rid)
        if resp is None:
            return jsonify({"code": 1, "desc": "未找到! "})
        if resp.is_reviewed:
            return jsonify({"code": 1, "desc": "已被审核! "})
        wl = Whitelist.query.filter_by(player_uuid=resp.player_uuid).first()
        if wl is not None:
            resp.is_reviewed = True
            db.session.commit()
            return jsonify({"code": 2, "desc": "此玩家存在已有白名单! "})

        resp.is_reviewed = True
        db.session.add(Whitelist(resp.user_id, resp.player_name, resp.player_uuid))
        db.session.commit()
        return jsonify({"code": 0, "desc": "通过! "})
    return jsonify({"code": 4, "desc": "错误! "})


@admin.route("/detail/<int:resp_id>", methods=["GET"])
@login_required
@required_role("admin")
def get_detail(resp_id: int):
    res: Response | None = Response.query.get(resp_id)
    # 查询指定问卷
    if res is None:
        return jsonify({"code": 1, "desc": "信息不足"}), 404
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
        response_score: ResponseScore | None = ResponseScore.query.filter_by(
            question_id=question.id, response_id=resp_id
        ).first()
        score = 0
        if response_score is not None:
            score = response_score.score
        question_data = {
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "score": question.score,
            "options": [],
            "answer": [],
            "countScore": score,
        }
        for option in question.options:
            question_data["options"].append(
                {
                    "id": option.id,
                    "text": option.option_text,
                    "isCorrect": option.is_correct,
                }
            )

        # 查询题目中的所有选项详情
        details: list[ResponseDetail] = ResponseDetail.query.filter_by(
            question_id=question.id, response_id=resp_id
        ).all()
        for detail in details:
            question_data["answer"].append({"id": detail.id, "text": detail.answer})

        survey_data["questions"].append(question_data)

    return jsonify(survey_data)


@admin.route("/detail_score", methods=["POST"])
@login_required
@required_role("admin")
def set_score():
    req_data = request.json
    if req_data:
        score = req_data.get("score")
        question_id = req_data.get("questionId")
        response_id = req_data.get("responseId")
        if not all([score, response_id, question_id]):
            return jsonify({"code": 2, "desc": "字段无效！"}), 400
        res = ResponseScore.query.filter_by(
            question_id=question_id, response_id=response_id
        ).first()
        if res is not None:
            res.score = score
        else:
            db.session.add(ResponseScore(score, question_id, response_id))
        db.session.commit()
        return jsonify({"code": 0, "desc": "更改成功！"})
    return jsonify({"code": 1, "desc": "缺少信息！"})


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
        res_data["list"].append(
            {
                "id": i.id,
                "typeName": i.type_name,
                "surveyId": i.survey_id,
            }
        )

    return jsonify(res_data)


@admin.route("/question_type", methods=["PUT"])
@login_required
@required_role("admin")
def set_question_type():
    req_data = request.json
    if req_data:
        id_ = req_data.get("id")
        survey_id = req_data.get("surveyId")
        type_name = req_data.get("typeName")

        if Survey.query.get(id_) is None:
            return jsonify({"code": 1, "desc": "未找到问卷！"})

        res: QuestionType | None = QuestionType.query.filter_by(id=id_).first()
        if res is None:
            return jsonify({"code": 1, "desc": "未找到类型！"})
        res.type_name = type_name
        res.survey_id = survey_id

        db.session.commit()

        res_data = {
            "code": 0,
            "desc": "成功! ",
        }

        return jsonify(res_data)
    return jsonify("wtf")
