from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db' # 测试数据库
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    from myapp.db_model import Survey, Question, Option, Response, ResponseDetail
    with app.app_context():
        db.create_all()

    # 导入蓝图
    from myapp.default import default

    # 注册蓝图
    app.register_blueprint(default, url_prefix='/default')

    @app.route("/")
    def hello():
        return '<h1>Hello World!</h1>'

    return app