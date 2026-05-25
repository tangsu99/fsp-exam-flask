from dataclasses import dataclass, field
from typing import cast

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from myapp.db_model import (
    User,
)


@dataclass
class Schematic:
    name: str
    author: int
    original_author: str
    desc: str
    game_version: str
    file: bytes
    type: str
    tags: list[str] = field(default_factory=list)
    is_public: bool = False


schematic = Blueprint("schematic", __name__)


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
    user: User = cast(User, current_user)
    is_public = False

    if request.form.get("isPublic") == "true":
        is_public = True

    original_author = user.username if request.form.get("originalAuthor") == "" else request.form.get("originalAuthor")

    schematic_item = Schematic(
        name=request.form.get("fileName"),
        author=user.id,
        original_author=original_author,
        desc=request.form.get("desc"),
        type=request.form.get("type"),
        tags=request.form.get("tags").split(" "),
        is_public=is_public,
        game_version=request.form.get("gameVersion"),
        file=request.files.get("uploadFile"),
    )

    print(schematic_item)

    return jsonify({"code": 0, "desc": "投影上传成功! "})
