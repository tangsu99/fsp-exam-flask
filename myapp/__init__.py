import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, Request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

login_manager: LoginManager = LoginManager()
db: SQLAlchemy = SQLAlchemy()
bcrypt: Bcrypt = Bcrypt()

cors = CORS()


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")  # 测试数据库
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")  # 用于安全签名session
    app.config["SESSION_PROTECTION"] = None  # 禁用会话保护
    app.config["API_TOKEN"] = os.getenv("API_TOKEN")

    cors.init_app(
        app=app,
        resources={
            "*": {"origins": "*"},
        },
    )

    app.template_folder = "../templates"
    app.static_folder = "../static"

    login_manager.init_app(app)
    db.init_app(app)
    bcrypt.init_app(app)

    from myapp.db_model import Token

    with app.app_context():
        db.create_all()

    # 导入蓝图
    from myapp.admin import admin
    from myapp.query import query
    from myapp.api import api
    from myapp.auth import auth
    from myapp.survey import survey
    from myapp.guarantee import guarantee
    from myapp.user import user

    # 注册蓝图
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(user, url_prefix="/user")
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(query, url_prefix="/query")
    app.register_blueprint(survey, url_prefix="/survey")
    app.register_blueprint(guarantee, url_prefix="/guarantee")

    @app.route("/")
    def hello():
        return "Hello world!\nHello Flask!"

    # 未授权的用户重定向到登录页面
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"code": 1, "desc": "用户未登录"})  # 重定向

    # 管理登录状态的，这个函数是在每次请求时被调用的，它需要从用户 ID 重新创建一个 User 对象
    # 这是因为 User 对象并不会在请求之间保持，所以我们需要在每次请求开始时重新创建它
    # 使用 request_loader 自定义加载逻辑
    @login_manager.request_loader
    def load_user_from_request(request: Request):
        # 尝试从查询参数中获取 token
        token: str | None = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.replace("Bearer ", "", 1)  # 假设使用 Bearer 认证
            token_record: Token | None = Token.query.filter_by(token=token).first()
            if (
                token_record
                and not token_record.is_revoked
                and token_record.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
            ):
                return token_record.user
        # 如果两种方式都未找到用户，返回 None
        return None

    return app
