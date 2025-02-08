from datetime import datetime, timedelta

from flask_login import UserMixin
from myapp import db, bcrypt

question_type_map = {
    1: 'singleChoice',
    2: 'multipleChoice',
    3: 'fillInTheBlanks',
    4: 'subjective'
}
guarantee_stats_map = {
    1: 'waiting',
    2: 'refuse',
    3: 'agreement'
}

DEFAULT_AVATAR = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAA/UlEQVQYVzWPvy8DYQCGn+/u+l2RlskZBDMSJGxyS4MmBgMzQ4cOIjaLMBmERSwWf0GlMejA0oTRJJEYKupHRBiaSy6qLr7vPnKNd3mW532TV4wNZYyKwREWkVYopbEsi5RjYwyIkYHMH9pJS4duKdDYND4jVKzbwv7qCm5K0pHO0mqGYFsE72/snp4jSltF0+lKvqII23YJwoBBr5fnp1qyKio7a2Z+85BFf4+CX0dmuziqeJSvNjjZLiKOC7PG6+vHcXs4q1aT1lJ+mteXe+ofDcTBcs5IoSldXjM3PJ4IF3c3LPiThM0fxPrMqIljw+3D4/+ZhLmpCVrRN7+WjFb8RvjH7AAAAABJRU5ErkJggg=='


# 问卷表模型
class Survey(db.Model):
    __tablename__ = 'surveys'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，问卷唯一标识，自增
    name = db.Column(db.String(200), nullable=False)  # 问卷名称，不允许为空
    description = db.Column(db.Text)  # 问卷描述，可为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 问卷创建时间，默认为当前时间
    status = db.Column(db.Integer, nullable=False)  # 问卷状态，不允许为空，如0-未发布，1-已发布，2-已结束等
    questions = db.relationship('Question', backref='survey', lazy=True, cascade='all, delete')  # 与问题表建立一对多关系，级联删除

    def __init__(self, name: str, description: str, status: int = 0):
        self.name = name
        self.description = description
        self.status = status


# 问题表模型
class Question(db.Model):
    __tablename__ = 'questions'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，问题唯一标识，自增
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete='CASCADE'),
                          nullable=False)  # 所属问卷id，外键，关联问卷表，级联删除
    question_text = db.Column(db.String(500), nullable=False)  # 问题内容，不允许为空
    question_type = db.Column(db.Integer, nullable=False)  # 问题类型，不允许为空，如1-单选，2-多选，3-填空，4-简答等
    score = db.Column(db.Integer, nullable=False)  # 问题分值，不允许为空
    sequence = db.Column(db.Integer)  # 问题排序，值越大排越前面，可为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 问题创建时间，默认为当前时间
    options = db.relationship('Option', backref='question', lazy=True, cascade='all, delete')  # 与选项表建立一对多关系，级联删除

    def __init__(self, survey_id: int, question_text: str, score: int, question_type: int = 1):
        self.survey_id = survey_id
        self.question_text = question_text
        self.question_type = question_type
        self.score = score


# 选项表模型
class Option(db.Model):
    __tablename__ = 'options'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，选项唯一标识，自增
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'),
                            nullable=False)  # 所属问题id，外键，关联问题表，级联删除
    option_text = db.Column(db.String(200), nullable=False)  # 选项内容，不允许为空
    is_correct = db.Column(db.Boolean)  # 是否为正确选项，对于有标准答案的题目，可为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 选项创建时间，默认为当前时间

    def __init__(self, question_id: int, option_text: str, is_correct: bool = False):
        self.question_id = question_id
        self.option_text = option_text
        self.is_correct = is_correct


# 用户表模型
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，用户唯一标识，自增
    username = db.Column(db.String(100), nullable=False)  # 用户名，不允许为空
    user_qq = db.Column(db.String(25), nullable=False)
    password = db.Column(db.String(100), nullable=False)  # 密码，不允许为空
    role = db.Column(db.String(100))  # 用户角色，如普通用户、管理员等，可为空
    addtime = db.Column(db.DateTime, default=datetime.utcnow)  # 用户新增时间，默认为当前时间
    avatar = db.Column(db.String(500), default=DEFAULT_AVATAR)
    status = db.Column(db.Integer, nullable=False, default=0)  # 0 未激活 1 正常 2 临时封禁 3 永久封禁
    # is_active = db.Column(db.Boolean, default=True)  # 默认为 True
    tokens = db.relationship('Token', backref='user', lazy=True)
    guarantees = db.relationship('Guarantee', foreign_keys='Guarantee.guarantee_id', backref='guarantor', lazy=True)
    applicant = db.relationship('Guarantee', foreign_keys='Guarantee.applicant_id', backref='applicant', lazy=True)
    responses = db.relationship('Response', backref='user', lazy=True, cascade='all, delete')  # 与答卷表建立一对多关系，级联删除

    def __init__(self, username: str, user_qq: str = '1', role: str = 'user'):
        self.username = username
        self.user_qq = user_qq
        self.role = role

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        return self

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


# 答卷表模型
class Response(db.Model):
    __tablename__ = 'responses'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，答卷唯一标识，自增
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                        nullable=False)  # 答题用户id，外键，关联用户表，级联删除
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete='CASCADE'),
                          nullable=False)  # 所答问卷id，外键，关联问卷表，级联删除
    response_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答卷时间，默认为当前时间
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答卷记录创建时间，默认为当前时间
    response_details = db.relationship('ResponseDetail', backref='response', lazy=True,
                                       cascade='all, delete')  # 与答题详情表建立一对多关系，级联删除


# 答题详情表模型
class ResponseDetail(db.Model):
    __tablename__ = 'response_details'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，答题详情唯一标识，自增
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id', ondelete='CASCADE'),
                            nullable=False)  # 所属答卷id，外键，关联答卷表，级联删除
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'),
                            nullable=False)  # 所答问题id，外键，关联问题表，级联删除
    answer = db.Column(db.String(500), nullable=False)  # 用户答案，对于选择题存储选项id，对于简答题存储答案文本，不允许为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答题详情创建时间，默认为当前时间


class Guarantee(db.Model):
    __tablename__ = 'guarantees'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，担保唯一标识，自增
    guarantee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 担保人id，不允许为空
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 申请人id，不允许为空
    player_name = db.Column(db.String(25), nullable=False)  # 被担保人ID，不允许为空
    player_uuid = db.Column(db.String(36), nullable=False)  # 被担保人UUID，不允许为空
    status = db.Column(db.Integer, nullable=False)  # 担保状态
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 担保记录创建时间，默认为当前时间

    def __init__(self, guarantee_id: int, applicant_id: int, player_name: str, player_uuid: str, status: int = 0):
        self.guarantee_id = guarantee_id
        self.applicant_id = applicant_id
        self.player_name = player_name
        self.player_uuid = player_uuid
        self.status = status


class Whitelist(db.Model):
    __tablename__ = 'whitelist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player_name = db.Column(db.String(25), nullable=False)
    player_uuid = db.Column(db.String(36), nullable=False)

    def __init__(self, user_id, player_name: str, player_uuid: str):
        self.user_id = user_id
        self.player_name = player_name
        self.player_uuid = player_uuid


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(256), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False)

    def __init__(self, user_id, token, expires_in=3600):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
