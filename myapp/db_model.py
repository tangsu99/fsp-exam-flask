from datetime import datetime, timedelta, timezone
from enum import Enum, unique
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import LONGTEXT
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
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
    )  # 问卷创建时间，默认为当前时间
    status: Mapped[int] = mapped_column(Integer, nullable=False)  # 问卷状态，！！！已废弃字段！！！
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
    logical_deletion: Mapped[bool] = mapped_column(Boolean ,default=False, nullable=True)  # 逻辑删除
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
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
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)

    def __init__(
        self,
        survey_id: int,
        question_text: str,
        question_type: int,
        score: float,
        display_order: int | None = None,
    ):
        self.survey_id = survey_id
        self.question_text = question_text
        self.question_type = question_type
        self.score = score

        if display_order is None:
            max_display_order = (
                    db.session.query(func.max(Question.display_order))
                    .filter_by(survey_id=survey_id, logical_deletion=False)
                    .scalar()
            )
            self.display_order = (max_display_order or 0) + 1
        else:
            self.display_order = display_order

    @classmethod
    def append_question(cls, survey_id: int, question_text: str, question_type: int, score: float):
        """
        在末尾插入题目
        """
        new_question = cls(
            survey_id=survey_id,
            question_text=question_text,
            question_type=question_type,
            score=score,
        )
        db.session.add(new_question)
        db.session.commit()

        # 返回新建的实例
        return new_question


    @classmethod
    def insert_question(cls, survey_id: int, question_text: str, question_type: int, score: float, target_display_order: int):
        """
        在指定位置插入一个问题，并调整后续问题的顺序。

        :param survey_id: 所属问卷 ID
        :param question_text: 问题内容
        :param question_type: 问题类型
        :param score: 问题分值
        :param target_display_order: 目标插入位置
        :return: 新建的 Question 实例
        """
        # 获取目标位置及之后的所有问题
        questions_to_shift = (
            db.session.query(Question)
            .filter(
                Question.survey_id == survey_id,
                Question.display_order >= target_display_order,
                Question.logical_deletion == False
            )
            .order_by(Question.display_order.desc()) # 从后往前更新，避免冲突
            .all()
        )

        for question in questions_to_shift:
            question.display_order +=1

        new_question = cls(
            survey_id=survey_id,
            question_text=question_text,
            question_type=question_type,
            score=score,
            display_order=target_display_order,
        )
        db.session.add(new_question)
        db.session.commit()

        # 返回新建的实例
        return new_question


# 问题图片表模型
class QuestionImgURL(db.Model):
    __tablename__ = "question_images"  # 指定表名
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # 主键，选项唯一标识，自增
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所属问题id，外键，关联问题表，级联删除
    img_alt: Mapped[str] = mapped_column(String(200))  # 图片alt，允许为空
    img_data: Mapped[str] = mapped_column(LONGTEXT, nullable=False)  # 图片数据，URL 或者 Base64 编码的图片，不允许为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
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
    option_text: Mapped[str] = mapped_column(Text, nullable=False)  # 选项内容，不允许为空
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)  # 是否为正确选项，对于有标准答案的题目，可为空
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
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
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
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
    is_reviewed: Mapped[int] = mapped_column(Integer, default=0)  # 阅卷状态，0 待审核 1 已通过 2 已拒绝
    reviewer_uid: Mapped[int] = mapped_column(Integer, nullable=True)
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )  # 答题用户id，外键，关联用户表，级联删除
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )  # 所答问卷id，外键，关联问卷表，级联删除
    survey_name: Mapped[str] = mapped_column(String(200), nullable=True)  # 问卷当时的名称
    response_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )  # 答卷时间，默认为当前时间
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
    )  # 答卷记录创建时间，默认为当前时间
    response_details: Mapped[list["ResponseDetail"]] = relationship(
        "ResponseDetail", backref="response_d", lazy="select", cascade="all, delete"
    )  # 与答题详情表建立一对多关系，级联删除
    response_score: Mapped[list["ResponseScore"]] = relationship(
        "ResponseScore", backref="response_s", lazy="select", cascade="all, delete"
    )
    archive_score: Mapped[float] = mapped_column(Float, nullable=True)

    def __init__(self, user_id: int, survey_id: int, survey_name: str, player_name: str, player_uuid: str):
        self.user_id = user_id
        self.survey_id = survey_id
        self.survey_name = survey_name
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
        DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp()
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
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 担保状态, 0 待同意，1 已同意，2 已拒绝
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expiration_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    def __init__(
        self,
        guarantee_id: int,
        applicant_id: int,
        player_name: str,
        player_uuid: str,
        create_time: datetime,
        expiration_time: datetime
    ):
        self.guarantee_id = guarantee_id
        self.applicant_id = applicant_id
        self.player_name = player_name
        self.player_uuid = player_uuid
        self.create_time = create_time
        self.expiration_time = expiration_time


class Whitelist(db.Model):
    __tablename__ = "whitelist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    auditor_uid: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[int] = mapped_column(Integer, nullable=False) # 0 代表考试，1代表担保，2代表其他
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.utc_timestamp(),
        server_default=func.utc_timestamp()
    )

    def __init__(self, user_id: int, player_name: str, player_uuid: str, source: int, auditor_uid: int):
        self.user_id = user_id
        self.player_name = player_name
        self.player_uuid = player_uuid
        self.source = source
        self.auditor_uid = auditor_uid


class Token(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp())
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
    register_time = db.Column(db.DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp())
    def __init__(self, ip):
        self.ip = ip


class ResetPasswordToken(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.utc_timestamp(), server_default=func.utc_timestamp())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(self, user_id, token, expires_in=3600):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)


# 配置表模型
class ConfigModel(db.Model):
    __tablename__ = "config"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.utc_timestamp(),
        server_default=func.utc_timestamp()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.utc_timestamp(),
        onupdate=func.utc_timestamp(),
        server_default=func.utc_timestamp(),
        server_onupdate=func.utc_timestamp()
    )

    def __init__(self, key: str, value: str, type_: str):
        self.key = key
        self.value = value
        self.type = type_
