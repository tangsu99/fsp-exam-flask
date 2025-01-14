from datetime import datetime
from myapp import db

question_type_map = {
    1: 'singleChoice',
    2: 'multipleChoice',
    3: 'fillInTheBlanks',
    4: 'subjective'
}

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
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete='CASCADE'), nullable=False)  # 所属问卷id，外键，关联问卷表，级联删除
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
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)  # 所属问题id，外键，关联问题表，级联删除
    option_text = db.Column(db.String(200), nullable=False)  # 选项内容，不允许为空
    is_correct = db.Column(db.Boolean)  # 是否为正确选项，对于有标准答案的题目，可为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 选项创建时间，默认为当前时间
    def __init__(self, question_id: int, option_text: str, is_correct: bool = None):
        self.question_id = question_id
        self.option_text = option_text
        self.is_correct = is_correct

# 用户表模型
# class User(db.Model):
#     __tablename__ = 'users'  # 指定表名
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，用户唯一标识，自增
#     username = db.Column(db.String(100), nullable=False)  # 用户名，不允许为空
#     password = db.Column(db.String(100), nullable=False)  # 密码，不允许为空
#     role = db.Column(db.String(100))  # 用户角色，如普通用户、管理员等，可为空
#     addtime = db.Column(db.DateTime, default=datetime.utcnow)  # 用户新增时间，默认为当前时间
#     responses = db.relationship('Response', backref='user', lazy=True, cascade='all, delete')  # 与答卷表建立一对多关系，级联删除

# 答卷表模型
class Response(db.Model):
    __tablename__ = 'responses'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，答卷唯一标识，自增
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)  # 答题用户id，外键，关联用户表，级联删除
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id', ondelete='CASCADE'), nullable=False)  # 所答问卷id，外键，关联问卷表，级联删除
    response_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答卷时间，默认为当前时间
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答卷记录创建时间，默认为当前时间
    response_details = db.relationship('ResponseDetail', backref='response', lazy=True, cascade='all, delete')  # 与答题详情表建立一对多关系，级联删除

# 答题详情表模型
class ResponseDetail(db.Model):
    __tablename__ = 'response_details'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，答题详情唯一标识，自增
    response_id = db.Column(db.Integer, db.ForeignKey('responses.id', ondelete='CASCADE'), nullable=False)  # 所属答卷id，外键，关联答卷表，级联删除
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)  # 所答问题id，外键，关联问题表，级联删除
    answer = db.Column(db.String(500), nullable=False)  # 用户答案，对于选择题存储选项id，对于简答题存储答案文本，不允许为空
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 答题详情创建时间，默认为当前时间

class Guarantee(db.Model):
    __tablename__ = 'guarantees'  # 指定表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键，担保唯一标识，自增
    guarantee_qq = db.Column(db.String(25), nullable=False)  # 担保人qq，不允许为空
    player_qq = db.Column(db.String(25), nullable=False)  # 被担保人qq，不允许为空
    status = db.Column(db.Integer, nullable=False)  # 担保状态，如1-等待，2-通过，3-存疑
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 担保记录创建时间，默认为当前时间
    def __init__(self, guarantee_qq: str, player_qq: str, status: int = 0):
        self.guarantee_qq = guarantee_qq
        self.player_qq = player_qq
        self.status = status
