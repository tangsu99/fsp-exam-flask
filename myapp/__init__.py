import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from flask import Flask, Request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase):
    pass


login_manager: LoginManager = LoginManager()
db = SQLAlchemy(model_class=Base)
migrate = Migrate()
bcrypt: Bcrypt = Bcrypt()
mail: Mail = Mail()
cors = CORS()

APP: Flask


def create_app():
    load_dotenv()
    app = Flask(__name__)
    global APP
    APP = app  # type: ignore[reportConstantRedefinition]
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")  # 测试数据库
    app.config["SESSION_PROTECTION"] = None  # 禁用会话保护
    app.template_folder = "../templates"
    app.static_folder = "../static"

    login_manager.init_app(app)  # type: ignore[reportUnknownMemberType]
    db.init_app(app)

    from myapp.db_model import Token

    with app.app_context():
        db.create_all()

    from .config import Config

    Config(app, db)

    cors.init_app(
        app=app,
        resources={
            r"/*": {
                "origins": app.config["ALLOWED_ORIGINS"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )
    migrate.init_app(app, db)
    bcrypt.init_app(app)  # type: ignore[reportUnknownMemberType]
    mail.init_app(app)

    # 导入蓝图
    from myapp.admin import admin
    from myapp.api import api
    from myapp.auth import auth
    from myapp.guarantee import guarantee
    from myapp.query import query
    from myapp.schematic import schematic
    from myapp.survey import survey
    from myapp.user import user

    # 注册蓝图
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(user, url_prefix="/user")
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(query, url_prefix="/query")
    app.register_blueprint(schematic, url_prefix="/schematic")
    app.register_blueprint(survey, url_prefix="/survey")
    app.register_blueprint(guarantee, url_prefix="/guarantee")

    # @app.route("/")
    # def hello():
    #     return "Hello world!\nHello Flask!"

    # 未授权的用户重定向到登录页面
    @login_manager.unauthorized_handler  # type: ignore[reportUnknownMemberType]
    def unauthorized():  # type: ignore[reportUnusedFunction]
        return jsonify({"code": 1, "desc": "用户未登录"})  # 重定向

    # 管理登录状态的，这个函数是在每次请求时被调用的，它需要从用户 ID 重新创建一个 User 对象
    # 这是因为 User 对象并不会在请求之间保持，所以我们需要在每次请求开始时重新创建它
    # 使用 request_loader 自定义加载逻辑
    @login_manager.request_loader  # type: ignore[reportUnknownMemberType]
    def load_user_from_request(request: Request):  # type: ignore[reportUnusedFunction]
        token: str | None = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "", 1)
            stmt = select(Token).where(Token.token == token)
            token_record = db.session.scalar(stmt)
            if (
                token_record
                and not token_record.is_revoked
                and token_record.expires_at.replace(tzinfo=UTC) > datetime.now(UTC)
            ):
                return token_record.token_user

        return None

    return app
