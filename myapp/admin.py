from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import joinedload

from myapp import APP, db
from myapp.config import Config
from myapp.db_model import (
    ConfigModel,
    Guarantee,
    Option,
    Question,
    QuestionCategory,
    QuestionImgURL,
    Response,
    ResponseDetail,
    ResponseScore,
    ResponseStatus,
    Survey,
    SurveySlot,
    User,
    UserStatus,
    Whitelist,
    WhitelistType,
)
from myapp.mail import send_mail, survey_result_mail
from myapp.survey_utils import DCQuestion, build_dc_questions, is_survey_mounted, is_survey_response_expired
from myapp.utils import (
    build_pagination_dict,
    check_password_format,
    parse_dt_to_iso_utc,
    parse_frontend_time_to_utc,
    required_role,
)

admin = Blueprint("admin", __name__)

my_config = Config(APP, db)


@admin.route("/config/get", methods=["GET"])
@login_required
@required_role("admin")
def get_config():
    key = request.args.get("key", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)

    stmt = select(ConfigModel)
    if key:
        stmt = stmt.where(ConfigModel.key.contains(key))  # 模糊查询

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    pagination_items: list = [
        {"key": item.key, "type": item.type, "value": item.value, "desc": item.description if item.description else ""}
        for item in pagination.items
    ]

    return jsonify({"code": 0, "desc": "success", "data": build_pagination_dict(pagination, pagination_items, True)})


@admin.route("/config/set", methods=["POST"])
@login_required
@required_role("admin")
def set_config():
    data = request.get_json()
    key = str(data.get("key") or "").strip()
    value = str(data.get("value") or "").strip()
    type_ = str(data.get("type") or "").strip()
    description = str(data.get("description") or "").strip()

    if not key:
        return jsonify({"code": 1, "desc": "need key!"})

    res = my_config.set_item(key, value, type_, description)
    if res:
        return jsonify({"code": 0, "desc": "success"})

    return jsonify({"code": 1, "desc": "fail"})


@admin.route("/config/delete", methods=["POST"])
@login_required
@required_role("admin")
def del_config():
    data = request.get_json()
    key = str(data.get("key") or "").strip()
    res = my_config.delete_item(key)
    if res:
        return jsonify({"code": 0, "desc": "success"})
    return jsonify({"code": 1, "desc": "fail"})


@admin.route("/survey/add", methods=["POST"])
@login_required
@required_role("admin")
def add_survey():
    data = request.get_json()
    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip()

    if not name:
        return jsonify({"code": 1, "desc": "必须填写名称!"})

    survey: Survey = Survey(name=name, description=description)
    db.session.add(survey)
    db.session.commit()
    return jsonify({"code": 0, "desc": "问卷创建成功", "data": {"surveyId": survey.id}})


@admin.route("/survey/delete", methods=["POST"])
@login_required
@required_role("admin")
def del_survey():
    data = request.get_json()
    id_ = int(data.get("id") or 0)

    if id_ == 0:
        return jsonify({"code": 1, "desc": "need id!"})

    try:
        survey: Survey | None = db.session.get(Survey, id_)

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


@admin.route("/survey/update", methods=["POST"])
@login_required
@required_role("admin")
def mod_survey():
    data = request.get_json()
    id_ = int(data.get("id") or 0)
    name = str(data.get("name") or "")
    desc = str(data.get("desc") or "")

    if id_ == 0 or not name:
        return jsonify({"code": 1, "desc": "必须填写名称!"})

    survey: Survey | None = db.session.get(Survey, id_)
    if survey is None:
        return jsonify({"code": 1, "desc": "问卷不存在"})

    survey.name = name
    survey.description = desc
    db.session.commit()
    return jsonify({"code": 0, "desc": "success"})


@admin.route("/question/add", methods=["POST"])
@login_required
@required_role("admin")
def add_question():
    """
    添加题目 API
    前端提供一个题目列表，每个列表元素包含：问卷ID、题目标题、类型、分数、选项和排序 ID 六个参数
    排序 ID 为 0 代表题目加入到末尾，其他值则为插入
    """
    data = request.get_json()
    question_list = data.get("questions", [])
    survey_id = data.get("surveyId", None)

    is_valid, error_info_or_list = build_dc_questions(question_list, survey_id)
    if not is_valid:
        return jsonify({"code": 1, "desc": error_info_or_list})

    try:
        question: DCQuestion
        for question in error_info_or_list:
            new_question: Question = Question.create(
                survey_id=question.survey_id,
                question_text=question.title,
                question_type=question.type,
                score=question.score,
                target_display_order=question.display_order,
            )

            option_objs = [
                Option(question_id=new_question.id, option_text=opt.text, is_correct=opt.is_correct)
                for opt in question.options
            ]

            image_objs = [
                QuestionImgURL(question_id=new_question.id, img_alt=img.alt, img_data=img.data)
                for img in question.images
            ]

            db.session.add(new_question)
            db.session.add_all(option_objs)
            db.session.add_all(image_objs)

        db.session.commit()
        return jsonify({"code": 0, "desc": "添加题目成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "desc": f"保存失败: {str(e)}"})


@admin.route("/question/migration", methods=["POST"])
@login_required
@required_role("admin")
def migration_question():
    """
    迁移题目 API，将源问卷的题目移动到目标问卷的末尾
    前端提供目标问卷ID (target_sid) 和题目ID (qid)
    """
    req_data = request.get_json()

    if not req_data:
        return jsonify({"code": 1, "desc": "请求数据为空或格式错误"})

    target_survey_id = req_data.get("target_sid")
    question_id = req_data.get("qid")

    if target_survey_id is None or question_id is None:
        return jsonify({"code": 1, "desc": "缺少必要参数: target_sid 或 qid"})

    current_question = db.session.get(Question, question_id)
    if current_question is None:
        return jsonify({"code": 1, "desc": "题目不存在"})

    if current_question.survey_id == target_survey_id:
        return jsonify({"code": 0, "desc": "题目已在目标问卷中，无需迁移"})

    try:
        stmt = (select(func.max(Question.display_order))
                .where(Question.survey_id == target_survey_id, Question.logical_deletion.is_(False)))
        max_order = db.session.scalar(stmt)

        current_question.survey_id = target_survey_id
        current_question.display_order = 1 if max_order is None else max_order + 1

        db.session.commit()
        return jsonify({"code": 0, "desc": "迁移题目成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "desc": f"迁移失败: {str(e)}"})


@admin.route("/question/edit", methods=["POST"])
@login_required
@required_role("admin")
def edit_question():
    """
    只接受一个题目一个题目修改
    """
    data = request.get_json()
    question_data = data.get("question", None)

    if question_data is None:
        return jsonify({"code": 1, "desc": "fail"})

    is_valid, error_info_or_list = build_dc_questions([question_data], question_data.get("surveyId", None))
    if not is_valid:
        return jsonify({"code": 1, "desc": error_info_or_list})

    try:
        question: DCQuestion = error_info_or_list[0]

        new_question = db.session.get(Question, question.id)

        if new_question is None or new_question.logical_deletion:
            return jsonify({"code": 1, "desc": "题目不存在或已被删除"})

        new_question.question_type = question.type
        new_question.question_text = question.title
        new_question.score = question.score
        new_question.display_order = question.display_order

        db.session.execute(delete(Option).where(Option.question_id == question.id))
        db.session.execute(delete(QuestionImgURL).where(QuestionImgURL.question_id == question.id))

        option_objs = [
            Option(question_id=question.id, option_text=opt.text, is_correct=opt.is_correct) for opt in question.options
        ]

        image_objs = [
            QuestionImgURL(question_id=question.id, img_alt=img.alt, img_data=img.data) for img in question.images
        ]

        db.session.add_all(option_objs)
        db.session.add_all(image_objs)

        db.session.commit()
        return jsonify({"code": 0, "desc": "编辑题目成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "desc": f"编辑题目失败: {str(e)}"})


@admin.route("/question/delete", methods=["POST"])
@login_required
@required_role("admin")
def del_question():
    req_data = request.get_json()
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少数据"})

    try:
        question = db.session.get(Question, req_data.get("id", None))

        if question is None:
            return jsonify({"code": 0, "desc": "题目不存在"})

        question.logical_deletion = True
        question.display_order = 0  # 保险起见，把排序设置为0

        db.session.commit()
        return jsonify({"code": 0, "desc": "删除题目成功"})

    except Exception as e:
        db.session.rollback()
        print(f"An error occurred while deleting the question: {e}")
        return jsonify({"code": 1, "desc": "出现错误"})


@admin.route("/question/sort", methods=["POST"])
@login_required
@required_role("admin")
def sort_survey_question():
    """
    编辑问卷排序模式提交排序API
    前端提供一个order_map 列表，列表元素数据格式：{ id: question_id, display_order: display_order}
    """
    order_list: None | list[dict[str, int]] = request.json
    if order_list is None or type(order_list) is not list:
        return jsonify({"code": 1, "desc": "缺少数据或数据错误"})

    origin_order_set = set()
    new_order_set = set()

    for i in order_list:
        question: None | Question = Question.query.get(i["id"])
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
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("size", 10, type=int)

    stmt = select(Whitelist).options(
        joinedload(Whitelist.user),
        joinedload(Whitelist.auditor),
    )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    items: list[Whitelist] = pagination.items
    pagination_items: list = [
        {
            "id": item.id,
            "username": item.user.username,
            "playerName": item.player_name,
            "playerUUID": item.player_uuid,
            "source": item.source,
            "auditorName": item.auditor.username if item.auditor else None,
            "authorizationDate": item.created_at,
        }
        for item in items
    ]

    return jsonify({"code": 0, "desc": "success", "data": build_pagination_dict(pagination, pagination_items, True)})


@admin.route("/users", methods=["GET"])
@login_required
@required_role("admin")
def users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("size", 10, type=int)

    stmt = select(User).where(User.status != UserStatus.DELETED)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    pagination_items = [
        {
            "id": user.id,
            "username": user.username,
            "userQQ": user.user_qq,
            "role": user.role,
            "status": user.status,
            "registeredAt": parse_dt_to_iso_utc(user.registered_at),
            "avatar": user.avatar
        } for user in pagination.items
    ]

    return jsonify({"code": 0, "desc": "success", "data": build_pagination_dict(pagination, pagination_items, True)})


@admin.route("/user", methods=["GET"])
@login_required
@required_role("admin")
def get_user():
    id_ = request.args.get("id", 0, type=int)
    user: User | None = db.session.get(User, id_)
    if user is None:
        return jsonify({"code": 1, "desc": "未找到用户！"})

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
                "registeredAt": parse_dt_to_iso_utc(user.registered_at),
                "avatar": user.avatar,
                "whitelist": user.whitelist
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
        if db.session.query(User).filter_by(username=username).first():
            return jsonify({"code": 2, "desc": "用户名已存在！"}), 400

        # 创建用户
        new_user = User(username=username, user_qq=user_qq, role=role)
        new_user.password = password
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
        registered_at_iso_str = req_data.get("addtime")
        role = req_data.get("role")
        status = req_data.get("status")

        # 校验必填字段
        if not user_id:
            return jsonify({"code": 1, "desc": "缺少用户ID！"}), 400

        # 查询用户
        user: User | None = db.session.get(User, user_id)
        if not user:
            return jsonify({"code": 2, "desc": "用户不存在！"}), 404

        # 更新用户信息
        if username:
            user.username = username

        if password is not None and check_password_format(password):
            user.password = password

        if user_qq:
            user.user_qq = user_qq

        if registered_at_iso_str:
            user.registered_at = parse_frontend_time_to_utc(registered_at_iso_str)

        if role:
            user.role = role

        if status is not None:
            user.status = status

            # 如果用户被封禁、临时封禁、删除，则删除名下白名单，如果之后被解封，需要重新考取白名单资格，系统不会自动恢复
            if status in (2, 3, 4):
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
            if expired:
                i.is_completed = True
                i.is_reviewed = 2
                db.session.commit()

        not_reviewed_count = Response.query.filter(Response.survey_id == _survey.id, Response.is_reviewed == 0).count()

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
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("size", 10, type=int)

    pagination = db.session.query(Response).paginate(page=page, per_page=per_page, error_out=False)
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
        if is_survey_response_expired(i):
            i.is_completed = True
            i.is_reviewed = 2
            db.session.commit()

        total_score: float = 0

        # 如果是被批改完的卷子，就直接调取总分，否则计算一遍
        if i.archive_score is None:
            scores = ResponseScore.query.filter_by(response_id=i.id).all()
            total_score = sum(score.score for score in scores)  # 计算总分

        else:
            total_score = i.archive_score

        if i.reviewer_uid is None:
            reviewer_name = "未审核"
        else:
            reviewer: None | User = db.session.get(User, i.reviewer_uid)
            if reviewer is None:
                reviewer_name = "该用户不存在"
            else:
                reviewer_name = reviewer.username

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
                "createTime": i.create_time,
                "responseTime": i.submit_time,
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
        "questions": [],
    }

    # 查询问卷中的所有题目
    for question in survey.questions:
        # 不返回被逻辑删除的题目
        if question.logical_deletion:
            continue

        question_data = {
            "display_order": question.display_order,
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
        status: ResponseStatus = req_data.get("status")

        resp: Response | None = Response.query.get(rid)

        if resp is None:
            return jsonify({"code": 1, "desc": "未找到! "})

        if resp.is_reviewed:
            return jsonify({"code": 1, "desc": "已被审核! "})

        resp.is_reviewed = status
        resp.reviewer_uid = current_user.id
        resp.is_completed = True

        # 已审核的问卷不可再批分，向归档分数字段添加分数，优化查询答卷列表时的速度
        stmt = select(func.sum(ResponseScore.score)).where(ResponseScore.response_id == rid)
        total_score: float = db.session.execute(stmt).scalar() or 0.0
        resp.archive_score = total_score

        # 为通过的用户添加白名单
        if status == ResponseStatus.APPROVED:
            stmt = select(exists().where(Whitelist.player_uuid == resp.player_uuid))

            if db.session.execute(stmt).scalar():
                db.session.commit()
                return jsonify({"code": 0, "desc": "此玩家存在已有白名单! "})

            db.session.add(
                Whitelist(
                    user_id=resp.user_id,
                    player_name=resp.player_name,
                    player_uuid=resp.player_uuid,
                    source=WhitelistType.EXAM,
                    auditor_uid=current_user.id,
                )
            )

        send_mail(APP, survey_result_mail([f"{resp.user.user_qq}@qq.com"], str(total_score)))

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
        "isReviewed": res.is_reviewed,
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
            "score": question.score,
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

        stmt = (select(ResponseScore)
                .where(ResponseScore.question_id == question_id, ResponseScore.response_id == response_id)
                )
        res = db.session.scalar(stmt)
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
def add_slot():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少信息！"})

    slot_name: str = req_data.get("slotName")
    mounted_survey_id: int = req_data.get("mountedSID")

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
            if Survey.query.get(new_survey_id) is None:
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
def del_slot():
    req_data = request.json
    if req_data is None:
        return jsonify({"code": 1, "desc": "缺少信息！"})

    slot_id: str | None = req_data.get("id")

    try:
        slot = SurveySlot.query.get(slot_id)
        if slot is None:
            return jsonify({"code": 0, "desc": "要删除的插槽不存在"})

        db.session.delete(slot)
        db.session.commit()
        return jsonify({"code": 0, "desc": "删除插槽成功"})

    except Exception as e:
        db.session.rollback()
        print(f"An error occurred while deleting the question: {e}")
        return jsonify({"code": 1, "desc": "出现错误"})


@admin.route("/guarantee/get", methods=["GET"])
@login_required
@required_role("admin")
def get_guarantee():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("size", 10, type=int)

    stmt = select(Guarantee)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    pagination_items = []

    for item in pagination.items:
        pagination_items.append(
            {
                "id": item.id,
                "guarantor_username": item.guarantor.username,
                "applicant_username": item.applicant_user.username,
                "player_name": item.player_name,
                "status": item.status,
                "create_time": parse_dt_to_iso_utc(item.create_time),
                "expiration_time": parse_dt_to_iso_utc(item.expiration_time)
            }
        )

    return jsonify({"code": 0, "desc": "success", "data": build_pagination_dict(pagination, pagination_items, True)})
