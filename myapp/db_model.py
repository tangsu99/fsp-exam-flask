from datetime import datetime, timedelta, timezone
from enum import Enum, unique
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myapp import bcrypt, db

# steve avatar, auth.py import this
DEFAULT_AVATAR = "8667ba71-b85a-4004-af54-457a9734eed7"


@unique
class QuestionCategory(Enum):
    SINGLE_CHOICE = 1
    MULTIPLE_CHOICE = 2
    FILL_IN_THE_BLANKS = 3
    SUBJECTIVE = 4


@unique
class GuaranteeStatus(Enum):
    WAITING = 1
    REFUSE = 2
    AGREEMENT = 3


# 问卷表模型
class Survey(db.Model):
    __tablename__ = "surveys"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，问卷唯一标识，自增
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # 问卷名称，不允许为空
    description: Mapped[Optional[str]] = mapped_column(Text)  # 问卷描述，可为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 问卷创建时间，默认为当前时间
    status: Mapped[int] = mapped_column(Integer, nullable=False)  # 问卷状态，不允许为空，0：未挂载，1：已挂载
    questions: Mapped[list["Question"]] = relationship(
        "Question", backref="survey", lazy="select", cascade="all, delete"
    )  # 与问题表建立一对多关系，级联删除
    response: Mapped[list["Response"]] = relationship(
        "Response", backref="survey_res", lazy="select", cascade="all, delete"
    )  # 与答卷表建立一对多关系，级联删除

    def __init__(self, name: str, description: str, status: int = 0):
        self.name = name
        self.description = description
        self.status = status


# 问题表模型
class Question(db.Model):
    __tablename__ = "questions"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，问题唯一标识，自增
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )  # 所属问卷id，外键，关联问卷表，级联删除
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)  # 问题内容，不允许为空
    question_type: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 问题类型，不允许为空，如1-单选，2-多选，3-填空，4-简答等
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 问题分值，不允许为空
    sequence: Mapped[Optional[int]] = mapped_column(Integer)  # 问题排序，值越大排越前面，可为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 问题创建时间，默认为当前时间
    img_list: Mapped[list["QuestionImgURL"]] = relationship(
        "QuestionImgURL", backref="question_images_backref", lazy="select", cascade="all ,delete"
    )  # 与图片表建立一对多关系，级联删除
    options: Mapped[list["Option"]] = relationship(
        "Option", backref="question", lazy="select", cascade="all, delete"
    )  # 与选项表建立一对多关系，级联删除
    response_details: Mapped[list["ResponseDetail"]] = relationship(
        "ResponseDetail", backref="question_r_d", lazy="select", cascade="all, delete"
    )

    def __init__(
        self,
        survey_id: int,
        question_text: str,
        question_type: int,
        score: int,
    ):
        self.survey_id = survey_id
        self.question_text = question_text
        self.question_type = question_type
        self.score = score


# 问题图片表模型
class QuestionImgURL(db.Model):
    __tablename__ = "question_images"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，选项唯一标识，自增
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所属问题id，外键，关联问题表，级联删除
    img_alt: Mapped[str] = mapped_column(String(200))  # 图片alt，允许为空
    img_data: Mapped[str] = mapped_column(Text, nullable=False)  # 图片数据，URL 或者 Base64 编码的图片，不允许为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 选项创建时间，默认为当前时间

    def __init__(self, question_id: int, img_alt: str, img_data: str):
        self.question_id = question_id
        self.img_alt = img_alt
        self.img_data = img_data


# 选项表模型
class Option(db.Model):
    __tablename__ = "options"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，选项唯一标识，自增
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所属问题id，外键，关联问题表，级联删除
    option_text: Mapped[str] = mapped_column(String(200), nullable=False)  # 选项内容，不允许为空
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)  # 是否为正确选项，对于有标准答案的题目，可为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 选项创建时间，默认为当前时间

    def __init__(self, question_id: int, option_text: str, is_correct: bool = False):
        self.question_id = question_id
        self.option_text = option_text
        self.is_correct = is_correct


# 用户表模型
class User(UserMixin, db.Model):
    __tablename__ = "users"  # 指定表名

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，用户唯一标识，自增
    username: Mapped[str] = mapped_column(String(100), nullable=False)  # 用户名，不允许为空
    user_qq: Mapped[str] = mapped_column(String(25), nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)  # 密码，不允许为空
    role: Mapped[str] = mapped_column(String(100))  # 用户角色，如普通用户、管理员等，可为空
    addtime: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 用户新增时间，默认为当前时间
    avatar: Mapped[str] = mapped_column(String(500), default=DEFAULT_AVATAR)
    status: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0 未激活 1 正常 2 临时封禁 3 永久封禁 4 删除
    tokens: Mapped[list["Token"]] = relationship("Token", backref="user", lazy="select")
    whitelist: Mapped[list["Whitelist"]] = relationship("Whitelist", backref="wl_user", lazy="select")
    guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee",
        foreign_keys="Guarantee.guarantee_id",
        backref="guarantor",
        lazy="select",
    )
    applicant: Mapped[list["Guarantee"]] = relationship(
        "Guarantee",
        foreign_keys="Guarantee.applicant_id",
        backref="applicant",
        lazy="select",
    )
    responses: Mapped[list["Response"]] = relationship(
        "Response", backref="user", lazy="select", cascade="all, delete"
    )  # 与答卷表建立一对多关系，级联删除

    reset_password_token: Mapped[list["ResetPasswordToken"]] = relationship(
        "ResetPasswordToken", backref="user_r_p_t", lazy="select", cascade="all, delete"
    )

    def __init__(self, username: str, user_qq: str = "1", role: str = "user"):
        self.username = username
        self.user_qq = user_qq
        self.role = role

    def set_password(self, password) -> "User":
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")
        return self

    def check_password(self, password) -> bool:
        return bcrypt.check_password_hash(self.password, password)


# 答卷表模型
class Response(db.Model):
    __tablename__ = "responses"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，答卷唯一标识，自增
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)  # 完成状态，默认为False（未完成）
    is_reviewed: Mapped[int] = mapped_column(Integer, default=0)  # 阅卷状态，默认为False（未阅卷）
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )  # 答题用户id，外键，关联用户表，级联删除
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )  # 所答问卷id，外键，关联问卷表，级联删除
    response_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 答卷时间，默认为当前时间
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 答卷记录创建时间，默认为当前时间
    response_details: Mapped[list["ResponseDetail"]] = relationship(
        "ResponseDetail", backref="response_d", lazy="select", cascade="all, delete"
    )  # 与答题详情表建立一对多关系，级联删除
    response_score: Mapped[list["ResponseScore"]] = relationship(
        "ResponseScore", backref="response_s", lazy="select", cascade="all, delete"
    )

    def __init__(self, user_id: int, survey_id: int, player_name: str, player_uuid: str):
        self.user_id = user_id
        self.survey_id = survey_id
        self.player_name = player_name
        self.player_uuid = player_uuid


class ResponseScore(db.Model):
    __tablename__ = "response_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[float] = mapped_column()
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    response_id: Mapped[int] = mapped_column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False)

    def __init__(self, score: float, question_id: int, response_id: int):
        self.score = score
        self.question_id = question_id
        self.response_id = response_id


# 答题详情表模型
class ResponseDetail(db.Model):
    __tablename__ = "response_details"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，答题详情唯一标识，自增
    response_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False
    )  # 所属答卷id，外键，关联答卷表，级联删除
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所答问题id，外键，关联问题表，级联删除
    answer: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # 用户答案，对于选择题存储选项id，对于简答题存储答案文本，不允许为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 答题详情创建时间，默认为当前时间

    def __init__(self, response_id: int, question_id: int, answer: str):
        self.response_id = response_id
        self.question_id = question_id
        self.answer = answer


class Guarantee(db.Model):
    __tablename__ = "guarantees"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，担保唯一标识，自增
    guarantee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)  # 担保人id，不允许为空
    applicant_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)  # 申请人id，不允许为空
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)  # 被担保人ID，不允许为空
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)  # 被担保人UUID，不允许为空
    status: Mapped[int] = mapped_column(Integer, nullable=False)  # 担保状态
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )  # 担保记录创建时间，默认为当前时间

    def __init__(
        self,
        guarantee_id: int,
        applicant_id: int,
        player_name: str,
        player_uuid: str,
        status: int = 0,
    ):
        self.guarantee_id = guarantee_id
        self.applicant_id = applicant_id
        self.player_name = player_name
        self.player_uuid = player_uuid
        self.status = status


class Whitelist(db.Model):
    __tablename__ = "whitelist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)

    def __init__(self, user_id: int, player_name: str, player_uuid: str):
        self.user_id = user_id
        self.player_name = player_name
        self.player_uuid = player_uuid


class Token(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, user_id, token, expires_in=3600):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)


class SurveySlot(db.Model):
    __tablename__ = "survey_slot"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slot_name: Mapped[str] = mapped_column(String(25), nullable=False)
    mounted_survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id"), nullable=False)

    def __init__(self, slot_name: str, survey_id: int):
        self.slot_name = slot_name
        self.mounted_survey_id = survey_id


class RegistrationLimit(db.Model):
    __tablename__ = "registration_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)  # 支持IPv6的最大长度
    register_time = db.Column(db.DateTime, default=datetime.now(timezone.utc))


class ResetPasswordToken(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, user_id, token, expires_in=3600):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
