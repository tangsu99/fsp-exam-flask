from io import BytesIO
from typing import Any, Literal

from flask import Blueprint, jsonify, request, send_file
from flask_login import (
    current_user,
    login_required,  # type: ignore[reportUnknownVariableType]
)
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from myapp import db
from myapp.db_model import Schematic, SchematicFile, SchematicType
from myapp.utils import build_pagination_dict, get_file_size, is_white_list_url

schematic = Blueprint("schematic", __name__)


MAX_FILE_SIZE_KB: int = 500


def to_brief_dict(self: Schematic):
    return {
        "id": self.id,
        "name": self.name,
        "type": self.schematic_type,
        "uploader": self.uploader.username,
        "originalAuthor": self.original_author,
        "tags": self.tag.split(" "),
        "isPublic": self.is_public,
        "gameVersion": self.game_version,
        "downloadCount": self.download_count,
        "uploadDate": self.upload_date.isoformat(),
        "updateDate": self.update_date.isoformat(),
    }


def get_schematic(schematic_id: int) -> Schematic | None:
    return db.session.get(Schematic, schematic_id)


PermissionAction = Literal["detail", "download", "edit", "delete"]


def check_user_permission(user: Any, action: PermissionAction, schematic_item: Schematic):
    """
    通用的权限校验函数
    :param user: 当前用户对象
    :param action: 操作类型，如 'detail', 'download', 'edit', 'share'...
    :param schematic_item: 资源
    """
    if action == "detail" or action == "download":
        return True if schematic_item.uploader_id == user.id or schematic_item.is_public else False

    elif action == "edit" or action == "delete":
        return True if schematic_item.uploader_id == user.id else False


@schematic.route("/", methods=["GET"])
@login_required
def index():
    return "is schematic api"


@schematic.route("/upload", methods=["POST"])
@login_required
def upload_schematic():
    """
    投影上传API
    """
    try:
        name: str = request.form.get("name", "").strip()

        original_author_input = request.form.get("originalAuthor", "").strip()
        # 如果前端没传原作者，默认使用当前登录用户的用户名
        original_author: str = current_user.username if not original_author_input else original_author_input

        desc: str = request.form.get("desc", "").strip()

        type_: str = request.form.get("type", "").strip()
        type_enum: SchematicType | None = Schematic.type_to_enum(int(type_))
        if type_enum is None:
            return jsonify({"code": 1, "desc": "无效的投影类型"})

        tags_raw: str = request.form.get("tags", "").strip()
        tag_list: list[str] = [t for t in tags_raw.split(" ") if t]
        is_public_str = request.form.get("isPublic", "false")
        is_public: bool = is_public_str.lower() == "true"
        game_version: str = request.form.get("gameVersion", "").strip()
        backup_link: str = request.form.get("backupLink", "").strip()

        if not is_white_list_url(backup_link):
            return jsonify({"code": 1, "desc": "该网盘不在白名单内不允许上传！"})

        # 获取并处理上传的文件
        file_storage = request.files.get("uploadFile")
        if not file_storage or file_storage.filename == "":
            return jsonify({"code": 1, "desc": "未找到上传的文件"})

        file_size_kb = get_file_size(file_storage, "KB")

        if file_size_kb > MAX_FILE_SIZE_KB:
            return jsonify({"code": 1, "desc": f"投影文件大小不能超过{MAX_FILE_SIZE_KB}KB！"})

        new_schematic = Schematic(
            name=name,
            uploader_id=current_user.id,
            original_author=original_author,
            schematic_type=type_enum,
            game_version=game_version,
            tag=" ".join(tag_list),  # 将列表转回字符串存入数据库
            description=desc,
            is_public=is_public,
            download_count=0,
            file_size_KB=file_size_kb,
            backup_link=backup_link,
        )

        # 先添加到 session，这样在 commit 之前就能拿到自动生成的主表 id
        db.session.add(new_schematic)
        db.session.flush()

        # 创建分表记录，存入二进制文件
        new_file = SchematicFile(schematic_id=new_schematic.id, file_blob=file_storage.read())
        db.session.add(new_file)
        db.session.commit()

        return jsonify({"code": 0, "desc": "投影上传成功! "})

    except Exception as e:
        # 发生错误时回滚事务，防止脏数据
        db.session.rollback()
        print(f"上传出错: {e}")
        return jsonify({"code": 1, "desc": f"服务器内部错误: {str(e)}"})


@schematic.route("/update", methods=["POST"])
@login_required
def update_schematic():
    """
    投影编辑API
    """
    try:
        schematic_id = request.form.get("id", 0, type=int)
        schematic_item = get_schematic(schematic_id)
        if schematic_item is None:
            return jsonify({"code": 1, "desc": "投影不存在"})

        if not check_user_permission(current_user, "edit", schematic_item):
            return jsonify({"code": 1, "desc": "无权修改该投影"})

        name: str = request.form.get("name", "").strip()
        original_author = request.form.get("originalAuthor", "").strip()

        type_: str = request.form.get("type", "").strip()
        type_enum: SchematicType | None = Schematic.type_to_enum(int(type_))
        if type_enum is None:
            return jsonify({"code": 1, "desc": "无效的投影类型"})

        game_version: str = request.form.get("gameVersion", "").strip()
        tags_raw: str = request.form.get("tags", "").strip()
        tags: list[str] = [t for t in tags_raw.split(" ") if t]
        desc: str = request.form.get("desc", "").strip()
        is_public_str = request.form.get("isPublic", "false")
        is_public: bool = is_public_str.lower() == "true"

        backup_link: str = request.form.get("backupLink", "").strip()
        if not is_white_list_url(backup_link):
            return jsonify({"code": 1, "desc": "该网盘不在白名单内不允许上传！"})

        file_storage = request.files.get("uploadFile")
        new_file_size_kb: int = 0

        if file_storage:
            new_file_size_kb = get_file_size(file_storage, "KB")

            if new_file_size_kb > MAX_FILE_SIZE_KB:
                return jsonify({"code": 1, "desc": f"投影文件大小不能超过{MAX_FILE_SIZE_KB}KB！"})

        schematic_item.name = name
        schematic_item.original_author = original_author
        schematic_item.schematic_type = type_enum
        schematic_item.game_version = game_version
        schematic_item.tag = " ".join(tags)
        schematic_item.description = desc
        schematic_item.is_public = is_public
        schematic_item.backup_link = backup_link

        if file_storage and new_file_size_kb != 0:
            schematic_item.file_size_KB = new_file_size_kb
            schematic_item.file_data.file_blob = file_storage.read()

        db.session.commit()
        return jsonify({"code": 0, "desc": "投影更新成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "desc": f"服务器内部错误: {str(e)}"})


@schematic.route("/query_by_type", methods=["GET"])
@login_required
def query_by_type():
    """
    投影查询API，按照投影类型查询，带分页功能，返回一定数量的投影缩略信息
    """

    type_: int = request.args.get("type", 0, type=int)
    type_enum: SchematicType | None = Schematic.type_to_enum(type_)
    if type_enum is None:
        return jsonify({"code": 1, "desc": "无效的投影类型"})

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)  # 最大每页100条, 默认10条

    stmt = (
        select(Schematic)
        .options(joinedload(Schematic.uploader))
        .where(
            Schematic.schematic_type == type_enum, or_(Schematic.is_public, Schematic.uploader_id == current_user.id)
        )
    )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "code": 0,
            "desc": "投影查询成功",
            "data": build_pagination_dict(pagination, [to_brief_dict(item) for item in pagination.items]),
        }
    )


@schematic.route("/query_detail", methods=["GET"])
@login_required
def query_detail():
    """
    通过投影ID，在此API获取单个投影的详细信息
    """
    schematic_id = request.args.get("id", 0, type=int)
    schematic_item = get_schematic(schematic_id)
    if schematic_item is None:
        return jsonify({"code": 1, "desc": "投影不存在"})

    if not check_user_permission(current_user, "detail", schematic_item):
        return jsonify({"code": 1, "desc": "无权查看！"})

    return jsonify(
        {
            "code": 0,
            "desc": "投影查询成功",
            "data": {
                "id": schematic_item.id,
                "name": schematic_item.name,
                "type": schematic_item.schematic_type,
                "uploader": schematic_item.uploader.username,
                "originalAuthor": schematic_item.original_author,
                "tags": schematic_item.tag.split(" "),
                "gameVersion": schematic_item.game_version,
                "downloadCount": schematic_item.download_count,
                "uploadDate": schematic_item.upload_date.isoformat(),
                "updateDate": schematic_item.update_date.isoformat(),
                "description": schematic_item.description,
                "isPublic": schematic_item.is_public,
                "fileSizeKB": schematic_item.file_size_KB,
                "backupLink": schematic_item.backup_link,
            },
        }
    )


@schematic.route("/search", methods=["GET"])
@login_required
def search_schematics():
    """
    搜索投影，根据搜索文字和类型筛选
    """
    search_text = request.args.get("text", "", type=str).strip()

    type_: int = request.args.get("type", 0, type=int)
    type_enum: SchematicType | None = Schematic.type_to_enum(type_)
    if type_enum is None:
        return jsonify({"code": 1, "desc": "无效的投影类型"})

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    if search_text == "":
        return jsonify({"code": 1, "desc": "请输入要搜索的内容"})

    stmt = (
        select(Schematic)
        .options(joinedload(Schematic.uploader))
        .where(
            or_(Schematic.is_public, Schematic.uploader_id == current_user.id),
            Schematic.schematic_type == type_enum,
            Schematic.name.ilike(f"%{search_text}%"),
        )
        .order_by(Schematic.update_date.desc())  # 降序，新的在前面
    )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "code": 0,
            "desc": "投影查询成功",
            "data": {
                "items": [to_brief_dict(item) for item in pagination.items],
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@schematic.route("/download", methods=["GET"])
@login_required
def download_schematic():
    """
    下载投影
    """
    schematic_id = request.args.get("id", 0, type=int)
    schematic_item = db.session.get(Schematic, schematic_id)

    if not schematic_item:
        return jsonify({"code": 1, "desc": "投影不存在"})

    if not check_user_permission(current_user, "download", schematic_item):
        return jsonify({"code": 1, "desc": "无权下载该私有投影"})

    file_record = schematic_item.file_data

    if not file_record or not file_record.file_blob:
        return jsonify({"code": 1, "desc": "投影文件数据缺失"})

    schematic_item.download_count += 1
    db.session.commit()

    safe_name = f"{schematic_item.name}.litematic"

    buffer = BytesIO(file_record.file_blob)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/octet-stream",
        as_attachment=True,  # 强制浏览器将响应作为附件下载，而不是在浏览器中直接打开或预览
        download_name=safe_name,  # Flask 2.x+ (RFC 5987 自动处理为安全的文件名)
    )


@schematic.route("/delete", methods=["GET"])
@login_required
def delete_schematic():
    """
    删除投影
    """
    schematic_id = request.args.get("id", 0, type=int)
    schematic_item = get_schematic(schematic_id)
    if schematic_item is None:
        return jsonify({"code": 1, "desc": "投影不存在"})

    if not check_user_permission(current_user, "delete", schematic_item):
        return jsonify({"code": 1, "desc": "无权删除该投影"})

    try:
        db.session.delete(schematic_item)
        db.session.commit()

        return jsonify({"code": 0, "desc": "投影删除成功"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 1, "desc": f"服务器内部错误: {str(e)}"})
