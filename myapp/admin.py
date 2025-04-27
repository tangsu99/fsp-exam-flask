from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from myapp import db, my_config
from myapp.db_model import (
    Guarantee,
    Option,
    Question,
    QuestionCategory,
    QuestionImgURL,
    SurveySlot,
    Response,
    ResponseDetail,
    ResponseScore,
    Survey,
    User,
    Whitelist,
)
from myapp.utils import check_password, required_role
from myapp.validate_json import validate_json

admin = Blueprint("admin", __name__)


@admin.route("/config", methods=["GET"])
@login_required
@required_role("admin")
def get_config():
    key = request.args.get('key')
    if key is None:
        return jsonify({"code": 0, "desc": "tangsu is lazy!", 'list': my_config.get_all()})
    return jsonify({"code": 0, "desc": "tangsu is lazy!", 'value': my_config.get_item(key)})


@admin.route("/config", methods=["POST"])
@login_required
@required_role("admin")
def set_config():
    data = request.get_json()
    if not data or "key" not in data or "value" not in data or "type" not in data:
        return jsonify({"code": 1, "desc": "数据不合法!"})

    my_config.set(data["key"], data["value"], data["type"])
    return jsonify({"code": 0, "desc": "tangsu is lazy!"})


def is_survey_mounted(survey_id: int) -> bool:
    res = SurveySlot.query.filter_by(mounted_survey_id=survey_id).count()
    return True if res else False


@admin.route("/addSurvey", methods=["POST"])
@login_required
@required_role("admin")
def add_survey():
    if request.json and "name" in request.json and "description" in request.json:
        name = request.json["name"]
        description = request.json["description"]
        if name and description:
            survey: Survey = Survey(name, description)
            db.session.add(survey)
            db.session.commit()
            return jsonify({"code": 0, "desc": "问卷创建成功"})
    return jsonify({"code": 1, "desc": "缺少数据"})


@admin.route("/delSurvey", methods=["POST"])
@login_required
@required_role("admin")
def del_survey():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少数据"})

    if type(req_data) is not int:
        return jsonify({"code": 1, "desc": "数据不符"})

    try:
        survey: Survey | None = db.session.get(Survey, req_data)

        if survey is None:
            return jsonify({"code": 1, "desc": "要删除的问卷不存在"})

        if is_survey_mounted(survey.id):
            return jsonify({"code": 1, "desc": "不能删除已发布的问卷！"})

        db.session.delete(survey)
        db.session.commit()
        return jsonify({"code": 0, "desc": "删除问卷成功"})

    except Exception as e:
        db.session.rollback()
        print(f"An error occurred while deleting the question: {e}")
        return jsonify({"code": 1, "desc": "出现错误"})


@admin.route("/modSurvey", methods=["POST"])
@login_required
@required_role("admin")
def mod_survey():
    if request.json and "sid" in request.json:
        sid = request.json["sid"]
        name = request.json["name"]
        description = request.json["description"]
        if sid and name and description:
            survey: Survey | None = Survey.query.get(sid)
            if survey is None:
                return jsonify({"code": 1, "desc": "问卷不存在"})

            survey.name = name
            survey.description = description

            db.session.commit()
            return jsonify({"code": 0, "desc": "成功"})

        return jsonify({"code": 1, "desc": "缺少数据"})
    return jsonify({"code": 1, "desc": "缺少数据"})


def add_question_images(question_id: int, img_list: list) -> None:
    for item in img_list:
        img: QuestionImgURL = QuestionImgURL(question_id=question_id, img_alt=item["alt"], img_data=item["data"])
        db.session.add(img)


def add_question_options(question_id: int, question_type: int, options: list) -> None:
    # 如果是填空题或者主观，设置第一个选项为正确选项
    if question_type in [3, 4]:
        options[0]["isCorrect"] = True

    for i in options:
        option: Option = Option(question_id=question_id, option_text=i["text"], is_correct=i["isCorrect"])
        db.session.add(option)


@admin.route("/addQuestion", methods=["POST"])
@login_required
@required_role("admin")
def add_question():
    """
    添加题目 API
    前端提供问卷ID、题目标题、类型、分数、选项和排序 ID 六个参数
    排序 ID 为 0 代表题目加入到末尾，其他值则为插入
    """
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "数据为空！"})

    options = req_data["options"]
    if (options is None) or (not len(options) > 0):
        return jsonify({"code": 1, "desc": "至少有一个选项！"})

    if req_data["display_order"] == 0:
        question: Question = Question.append_question(
            survey_id=req_data["survey"],
            question_text=req_data["title"],
            question_type=req_data["type"],
            score=req_data["score"],
        )
    else:
        question: Question = Question.insert_question(
            survey_id=req_data["survey"],
            question_text=req_data["title"],
            question_type=req_data["type"],
            score=req_data["score"],
            target_display_order=req_data["display_order"]
        )

    add_question_options(question.id, question.question_type, options)

    # 添加图片
    img_list = req_data.get("img_list", [])
    add_question_images(question.id, img_list)

    db.session.commit()
    return jsonify({"code": 0, "desc": "添加题目成功"})


@admin.route("/editQuestion", methods=["POST"])
@login_required
@required_role("admin")
def edit_question():
    req_data = request.json

    if req_data is None:
        return jsonify({"code": 1, "desc": "请求数据为空"})

    question_id = req_data.get("id")

    if not question_id:
        return jsonify({"code": 1, "desc": "缺少题目 ID"})

    question: Question | None = Question.query.get(question_id)

    if question is None:
        return jsonify({"code": 1, "desc": "题目不存在"})

    # 更新题目基本信息
    question.survey_id = req_data["survey"]
    question.question_text = req_data["title"]
    question.question_type = req_data["type"]
    question.score = req_data["score"]

    # 处理选项数据
    options = req_data.get("options")
    Option.query.filter_by(question_id=question_id).delete()
    add_question_options(question.id, question.question_type, options)

    # 处理图片数据
    img_list = req_data.get("img_list", [])
    QuestionImgURL.query.filter_by(question_id=question_id).delete()
    add_question_images(question_id, img_list)

    db.session.commit()

    return jsonify({"code": 0, "desc": "修改题目成功"})


@admin.route("/delQuestion", methods=["POST"])
@login_required
@required_role("admin")
def del_question():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少数据"})

    try:
        # 直接通过主键获取问题
        question = db.session.get(Question, req_data)

        if question is None:
            return jsonify({"code": 0, "desc": "题目不存在"})

        # 逻辑删除问题
        question.logical_deletion = True

        # 保险起见，把排序设置为0
        question.display_order = 0

        # 提交事务
        db.session.commit()
        return jsonify({"code": 0, "desc": "删除题目成功"})

    except Exception as e:
        # 处理其他异常
        db.session.rollback()
        print(f"An error occurred while deleting the question: {e}")
        return jsonify({"code": 1, "desc": "出现错误"})


@admin.route("/sortSurveyQuestions", methods=["POST"])
@login_required
@required_role("admin")
def sort_survey_question():
    """
    编辑问卷排序模式提交排序API
    前端提供一个order_map 列表，列表元素数据格式：{ id: question_id, display_order: display_order}
    """
    order_list : None | list[dict[str, int]] = request.json
    if order_list is None or type(order_list) is not list:
        return jsonify({"code": 1, "desc": "缺少数据或数据错误"})

    origin_order_set = set()
    new_order_set = set()

    for i in order_list:
        question : None | Question = Question.query.get(i["id"])
        if question is None or question.logical_deletion is True:
                return jsonify({"code": 1, "desc": "不存在ID为{i.id}的题目"})
        origin_order_set.add(question.display_order)
        new_order_set.add(i["display_order"])
        question.display_order = i["display_order"]

    # 保险起见
    if origin_order_set != new_order_set:
        return jsonify({"code": 1, "desc": "数据错误"})

    db.session.commit()
    return jsonify({"code": 0, "desc": "排序成功"})


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

        auditor : None | User = User.query.get(i.auditor_uid)
        if auditor is None:
            auditor_name = "该用户不存在"
        else:
            auditor_name= auditor.username

        response_data["list"].append({
            "id": i.id,
            "username": i.wl_user.username,
            "name": i.player_name,
            "uuid": i.player_uuid,
            "source": i.source,
            "auditor_name": auditor_name,
            "created_at": i.created_at
        })

    # 添加分页信息
    response_data["page"] = pagination.page
    response_data["size"] = pagination.per_page
    response_data["total"] = pagination.total

    return jsonify(response_data)


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
                "userQQ": user.user_qq,
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
        new_user = User(username=username, user_qq=user_qq, role=role).set_password(password)
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

            # 如果用户被封禁或临时封禁，删除名下白名单，如果之后被解封，需要重新考取白名单资格，系统不会自动恢复
            if status in (2, 3):
                wl = user.whitelist
                for item in wl:
                    db.session.delete(item)

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

        # 逻辑删除用户
        user.status = 4
        db.session.commit()

        return jsonify({"code": 0, "desc": "用户删除成功！"})
    return jsonify({"code": 1, "desc": "缺少信息"})


# survey.py 有一个一模一样的函数
def is_survey_response_expired(survey_response: Response) -> bool:
    VALIDITY_PERIOD = timedelta(hours=24) # 有效期为 24h

    # 只判断未完成的问卷，已完成的问卷不存在“过期”的说法
    if survey_response.is_completed is False:
        create_time = survey_response.create_time
        create_datetime = create_time.replace(tzinfo=timezone.utc)
        current_datetime = datetime.now(timezone.utc)
        expired_datetime = create_datetime + VALIDITY_PERIOD
        if expired_datetime < current_datetime:
            survey_response.is_completed = True
            survey_response.is_reviewed = 2
            db.session.commit()
            return True
    return False



@admin.route("/surveys", methods=["GET"])
@login_required
@required_role("admin")
def get_surveys():
    result = Survey.query.all()
    response_data = {"code": 0, "desc": "yes", "list": []}
    for _survey in result:
        not_completed_count: int = 0
        survey_response_list = Response.query.filter_by(id=_survey.id).all()

        for i in survey_response_list:
            expired = is_survey_response_expired(i)
            if expired is False and i.is_completed is False:
                not_completed_count += 1

        not_reviewed_count = Response.query.filter(
            Response.survey_id == _survey.id,
            Response.is_reviewed == 0
        ).count()

        m = is_survey_mounted(_survey.id)
        status = 1 if m else 0

        response_data["list"].append(
            {
                "id": _survey.id,
                "name": _survey.name,
                "description": _survey.description,
                "createTime": _survey.create_time,
                "status": status,
                "notCompletedCount": not_completed_count,
                "notReviewedCount": not_reviewed_count,
            }
        )
    return jsonify(response_data)


@admin.route("/responses", methods=["GET"])
@login_required
@required_role("admin")
def get_responses():
    """
    查询答卷列表
    """
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
        # 刷新一下是否过期
        is_survey_response_expired(i)

        total_score: float = 0

        # 如果是被批改完的卷子，就直接调取总分，否则计算一遍
        if i.archive_score is None:
            scores = ResponseScore.query.filter_by(response_id=i.id).all()
            total_score = sum(score.score for score in scores)  # 计算总分

        else:
            total_score = i.archive_score


        reviewer : None | User = User.query.get(i.reviewer_uid)
        if reviewer is None:
            reviewer_name = "该用户不存在"
        else:
            reviewer_name= reviewer.username

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
                "reviewer_name": reviewer_name,
            }
        )
    return jsonify(response_data)


@admin.route("/survey/<int:sid>", methods=["GET"])
@login_required
@required_role("admin")
def get_survey(sid: int):
    # 查询指定问卷
    survey: Survey | None = Survey.query.get(sid)
    if not survey:
        return jsonify({"code": 1, "desc": "未找到问卷"}), 404

    survey_data = {
        "id": survey.id,
        "name": survey.name,
        "description": survey.description,
        "create_time": survey.create_time,
        # "status": status, 好像没用
        "questions": [],
    }

    # 查询问卷中的所有题目
    for question in survey.questions:
        # 不返回被逻辑删除的题目
        if question.logical_deletion:
            continue

        question_data = {
            "display_order" : question.display_order,
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "score": question.score,
            "img_list": [],
            "options": [],
        }

        for img in question.img_list:
            question_data["img_list"].append({"id": img.id, "alt": img.img_alt, "data": img.img_data})

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
    """
    设置是否通过该答卷
    """
    req_data = request.json
    if req_data:
        rid = req_data.get("response")
        status: int = req_data.get("status")

        resp: Response | None = Response.query.get(rid)

        if resp is None:
            return jsonify({"code": 1, "desc": "未找到! "})

        if resp.is_reviewed:
            return jsonify({"code": 1, "desc": "已被审核! "})

        if status not in [0, 1, 2]:
            return jsonify({"code": 4, "desc": "未知状态！"})

        # 设置审核状态后，强制将问卷设置为已完成的
        resp.is_reviewed = status
        resp.reviewer_uid = current_user.id
        resp.is_completed = True

        # 已审核的问卷不可再批分，向归档分数字段添加分数，优化查询答卷列表时的速度
        scores = ResponseScore.query.filter_by(response_id=rid).all()
        total_score: float = sum(score.score for score in scores)  # 计算总分
        resp.archive_score = total_score

        # 为通过的用户添加白名单
        if status == 1:
            wl = Whitelist.query.filter_by(player_uuid=resp.player_uuid).first()
            if wl is not None:
                db.session.commit()
                return jsonify({"code": 0, "desc": "此玩家存在已有白名单! "})

            db.session.add(Whitelist(
                    user_id=resp.user_id,
                    player_name=resp.player_name,
                    player_uuid=resp.player_uuid,
                    source=0,
                    auditor_uid=current_user.id
            ))

        db.session.commit()
        return jsonify({"code": 0, "desc": "操作成功"})

    return jsonify({"code": 4, "desc": "缺少数据! "})


@admin.route("/detail/<int:resp_id>", methods=["GET"])
@login_required
@required_role("admin")
def get_detail(resp_id: int):
    """
    查询指定问卷
    """
    res: Response | None = Response.query.get(resp_id)
    if res is None:
        return jsonify({"code": 1, "desc": "信息不足"}), 404

    survey: Survey | None = Survey.query.get(res.survey_id)

    if not survey:
        return jsonify({"code": 1, "desc": "未找到问卷"}), 404

    survey_data = {
        "id": res.id,
        "name": survey.name,
        "description": survey.description,
        "create_time": survey.create_time,
        # "status": survey.status, 好像用不到
        "questions": [],
    }

    # 查询问卷中的所有题目
    for question in survey.questions:
        response_score: ResponseScore | None = ResponseScore.query.filter_by(
            question_id=question.id, response_id=resp_id
        ).first()

        # 查询题目中的所有选项详情
        details: list[ResponseDetail] = ResponseDetail.query.filter_by(
            question_id=question.id, response_id=resp_id
        ).all()

        # 如果题目被逻辑删除，并且用户未作答，则不显示
        if question.logical_deletion and len(details) == 0:
            continue

        score = 0
        user_selected_option: list[int] = []

        if response_score is not None:
            score = response_score.score

        question_data = {
            "display_order": question.display_order,
            "id": question.id,
            "title": question.question_text,
            "type": question.question_type,
            "totalScore": question.score,
            "userGetScore": score,
            "options": [],
            "img_list": [],
            "text_answer": "",
        }

        for img in question.img_list:
            question_data["img_list"].append({"alt": img.img_alt, "data": img.img_data})

        # 标注用户选择的选项
        if (
            question.question_type == QuestionCategory.SINGLE_CHOICE.value
            or question.question_type == QuestionCategory.MULTIPLE_CHOICE.value
        ):
            for detail in details:
                user_selected_option.append(int(detail.answer))

        for option in question.options:
            question_data["options"].append(
                {
                    "id": option.id,
                    "text": option.option_text,
                    "isCorrect": option.is_correct,
                    "isSelected": True if option.id in user_selected_option else False,
                    "inputText": details[0].answer if question.question_type in [3, 4] and len(details) != 0 else "",
                }
            )

        survey_data["questions"].append(question_data)
    return jsonify(survey_data)


@admin.route("/detail_score", methods=["POST"])
@login_required
@required_role("admin")
def set_score():
    """
    批改某个题目，前端提供题目ID，答卷ID，和分数
    """
    req_data = request.json
    if req_data:
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
        return jsonify({"code": 0, "desc": "批改成功！"})
    return jsonify({"code": 1, "desc": "缺少信息！"})


@admin.route("/add_slot", methods=["POST"])
@login_required
@required_role("admin")
@validate_json(required_fields=["slotName", "mountedSID"])
def add_slot():
    slot_name: str = request.json["slotName"] # type: ignore
    mounted_survey_id: int = request.json["mountedSID"] # type: ignore

    mounted_survey: Survey | None = Survey.query.get(mounted_survey_id)
    if mounted_survey is None:
        return jsonify({"code": 1, "desc": "挂载的问卷不存在"})

    slot: SurveySlot = SurveySlot(slot_name=slot_name, survey_id=mounted_survey_id)

    db.session.add(slot)
    db.session.commit()
    return jsonify({"code": 0, "desc": "新建插槽成功"})


@admin.route("/set_slot", methods=["POST"])
@login_required
@required_role("admin")
def set_slot():
    req_data = request.json
    if req_data:
        slot_id = req_data.get("id")
        new_survey_id = req_data.get("mountedSID")
        if slot_id and new_survey_id:
            if Survey.query.get(slot_id) is None:
                return jsonify({"code": 1, "desc": "未找到问卷！"})

            slot: SurveySlot | None = SurveySlot.query.get(slot_id)
            if slot is None:
                return jsonify({"code": 1, "desc": "未找到插槽！"})

            new_mounted_survey: Survey | None = Survey.query.get(new_survey_id)

            if new_mounted_survey:
                slot.mounted_survey_id = new_survey_id
                db.session.commit()

                return jsonify({"code": 0, "desc": f"修改{slot.slot_name}插槽成功"})

            return jsonify({"code": 1, "desc": "问卷不存在"})
        return jsonify({"code": 1, "desc": "缺少信息！"})
    return jsonify({"code": 1, "desc": "缺少信息！"})


@admin.route("/del_slot", methods=["POST"])
@login_required
@required_role("admin")
@validate_json(required_fields=["id"])
def del_slot():
    slot_id: str = request.json["id"] # type: ignore
    try:
        # 直接通过主键获取问题
        slot = SurveySlot.query.get(slot_id)
        if slot is None:
            return jsonify({"code": 0, "desc": "要删除的插槽不存在"})

        db.session.delete(slot)
        db.session.commit()
        return jsonify({"code": 0, "desc": "删除插槽成功"})

    except Exception as e:
        # 处理其他异常
        db.session.rollback()
        print(f"An error occurred while deleting the question: {e}")
        return jsonify({"code": 1, "desc": "出现错误"})



@admin.route("/guarantee/get", methods=["GET"])
@login_required
@required_role("admin")
def get_guarantee():
    page = request.args.get("page", 1, type=int)  # 获取页码，默认为 1
    per_page = request.args.get("size", 10, type=int)  # 获取每页条数，默认为 10

    pagination = Guarantee.query.paginate(page=page, per_page=per_page, error_out=False)

    result_list = []

    for item in pagination.items:
        result_list.append({
            "id": item.id,
            "guarantor_username": item.guarantor.username,
            "applicant_username": item.applicant.username,
            "player_name": item.player_name,
            "status": item.status,
            "create_time": item.create_time,
            "expiration_time": item.expiration_time
        })
    response_data = {
        "code": 0,
        "desc": "yes",
        "list": result_list,
        "page": pagination.page,
        "size": pagination.per_page,
        "total": pagination.total,
    }
    return jsonify(response_data)

