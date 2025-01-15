from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # 测试数据库
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'c4329f5e3bc9daf6cd2b82bf9355a5d2'  # 用于安全签名session

    app.template_folder = '../templates'
    app.static_folder = '../static'

    login_manager.init_app(app)
    db.init_app(app)

    from myapp.db_model import Survey, Question, Option, Response, ResponseDetail, User
    with app.app_context():
        db.create_all()

    # 导入蓝图
    from myapp.api import api
    from myapp.auth import auth
    from myapp.admin import admin
    from myapp.default import default
    from myapp.guarantee import guarantee

    # 注册蓝图
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(default, url_prefix='/default')
    app.register_blueprint(guarantee, url_prefix='/guarantee')

    @app.route("/")
    def hello():
        return render_template('index.html')

    # 未授权的用户重定向到登录页面
    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login'))  # 重定向

    # 管理登录状态的，这个函数是在每次请求时被调用的，它需要从用户 ID 重新创建一个 User 对象
    # 这是因为 User 对象并不会在请求之间保持，所以我们需要在每次请求开始时重新创建它
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
