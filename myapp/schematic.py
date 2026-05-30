from typing import cast
from enum import Enum
import re

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp import db
from myapp.db_model import (
    User,
    Schematics,
    SchematicFiles,
)


schematic = Blueprint("schematic", __name__)


class SchematicType(Enum):
    OTHER = 0
    REDSTONE = 1
    ARCHITECTURE = 2


# 定义白名单规则列表
# 字符串代表严格匹配前缀，字典中的 'regex' 代表正则表达式匹配
WHITE_LIST_RULES = [
    "https://pan.baidu.com",  # 百度网盘固定前缀
    "https://pan.quark.cn",  # 夸克网盘固定前缀
    {"regex": r'^https://(www\.|wws\.)?lanzou[a-z]?\.com'}  # 蓝奏云正则规则
]


def is_white_list_url(url):
    """检测单个链接是否符合白名单列表中的规则"""
    if not url:
        return False

    url = url.strip()

    for rule in WHITE_LIST_RULES:
        if isinstance(rule, str) and url.startswith(rule):
            return True

        if isinstance(rule, dict) and 'regex' in rule:
            if re.match(rule['regex'], url):
                return True
    return False

@schematic.route("/", methods=["GET"])
@login_required
def index():
    return "is schematic api"


@schematic.route("/upload", methods=["POST"])
@login_required
def upload():
    """
    投影上传API
    """
    try:
        user: User = cast(User, current_user)

        original_author_input = request.form.get("originalAuthor", "").strip()

        name: str = request.form.get("fileName","").strip()

        # 如果前端没传原作者，默认使用当前登录用户的用户名
        original_author: str = user.username if not original_author_input else original_author_input

        desc: str = request.form.get("desc", "").strip()

        type_str: str = request.form.get("type", "").strip()

        try:
            type_index = SchematicType[type_str.upper()].value

        except KeyError:
            return jsonify({"code": 1, "desc": "无效的投影类型"})

        tags_list: list[str]  = request.form.get("tags", "").split(" ")
        is_public_str = request.form.get("isPublic", "false")
        is_public: bool = is_public_str.lower() == "true"
        game_version: str = request.form.get("gameVersion","").strip()
        backup_link: str = request.form.get("backupLink","").strip()

        if backup_link != "" and not is_white_list_url(backup_link):
            return jsonify({"code": 1, "desc": "该网盘不在白名单内不允许上传！"})

        # 获取并处理上传的文件
        file_storage = request.files.get("uploadFile")
        if not file_storage or file_storage.filename == '':
            return jsonify({"code": 1, "desc": "未找到上传的文件"})

        # 读取文件的二进制内容并计算大小 (KB)
        file_bytes = file_storage.read()
        file_size_kb = len(file_bytes) // 1024

        new_schematic = Schematics(
            name=name,
            uploader_id=user.id,
            original_author=original_author,
            schematic_type=type_index,
            game_version=game_version,
            tag=" ".join(tags_list), # 将列表转回字符串存入数据库
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
        new_file = SchematicFiles(
            schematic_id=new_schematic.id,
            file_blob=file_bytes
        )
        db.session.add(new_file)
        db.session.commit()

        return jsonify({"code": 0, "desc": "投影上传成功! "})

    except Exception as e:
            # 发生错误时回滚事务，防止脏数据
            db.session.rollback()
            print(f"上传出错: {e}")
            return jsonify({"code": 1, "desc": f"服务器内部错误: {str(e)}"})


@schematic.route("/query_by_type", methods=["GET"])
@login_required
def query_by_type():
    """
        投影查询API，按照投影类型查询，带分页功能，返回一定数量的投影缩略信息
    """

    type_str = request.args.get("type", "", type=str)
    try:
        type_index = SchematicType[type_str.upper()].value

    except KeyError:
        return jsonify({"code": 1, "desc": "无效的投影类型"}), 400

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100) # 最大每页100条, 默认10条

    query = (db.session.query(Schematics)
             .filter(Schematics.schematic_type == type_index)
             .paginate(page=page, per_page=per_page, error_out=False))

    schematics_list = [
        {
            "id": item.id,
            "name": item.name,
            "type": item.schematic_type,
            "uploader": item.uploader.username,
            "originalAuthor": item.original_author,
            "tags": item.tag.split(" "),
            "isPublic": item.is_public,
            "gameVersion": item.game_version,
            "downloadCount": item.download_count,
            "uploadDate": item.upload_date.strftime("%Y-%m-%d %H:%M:%S"),
            "updateDate": item.update_date.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for item in query.items
    ]

    return jsonify({
        "code": 0,
        "desc": "投影查询成功",
        "data": {
            "items": schematics_list,
            "total": query.total,
            "page": query.page,
            "pages": query.pages,
            "per_page": query.per_page,
            "has_next": query.has_next,
            "has_prev": query.has_prev
        }
    })


@schematic.route("/query_detail", methods=["GET"])
@login_required
def query_detail():
    """
        通过投影ID，在此API获取单个投影的详细信息
    """

    schematic_id = request.args.get("id", 0, type=int)

    if schematic_id == 0:
        return jsonify({"code": 1, "desc": "无效的投影ID"})

    query: Schematics | None = Schematics.query.get(schematic_id)
    if query is None:
        return jsonify({"code": 1, "desc": "投影不存在"})

    return jsonify({
        "code": 0,
        "desc": "投影查询成功",
        "data": {
            "id": query.id,
            "name" : query.name,
            "type": query.schematic_type,
            "uploader" : query.uploader.username,
            "originalAuthor" : query.original_author,
            "tags": query.tag.split(" "),
            "gameVersion": query.game_version,
            "downloadCount": query.download_count,
            "uploadDate": query.upload_date,
            "updateDate": query.update_date,
            "description": query.description,
            "isPublic": query.is_public,
            "fileSizeKB": query.file_size_KB,
            "backupLink": query.backup_link,
        }
    })
