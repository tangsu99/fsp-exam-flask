from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum, unique
from typing import Optional, Self

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    exists,
    func,
    select,
    update,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from myapp import Base, bcrypt, db

# steve avatar, auth.py import this
DEFAULT_AVATAR = "8667ba71-b85a-4004-af54-457a9734eed7"


TZ_AWARE_DATETIME = DateTime(timezone=True)


# 不推荐：
# upload_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
# update_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
# 上述代码对应的 DDL 应该如下
# upload_date     datetime default CURRENT_TIMESTAMP not null,
# update_date     datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
# func.now() 翻译出来是 CURRENT_TIMESTAMP，
# SQLite 的 CURRENT_TIMESTAMP 默认返回的就是 UTC 格式字符串；MySQL/PG 返回的是服务器本地时间
# 它们都不带时区，很麻烦，Unix 时间戳又只支持到 2038 年
# func.utc_timestamp() # MySQL 特有，返回 UTC 时间戳，不支持 PGSQL 和 SQLite
# 所以采用 Python 赋值时间比较方便且跨平台
# 这样设置的时间，存在 DB 的都是 UTC 时间的 datetime，前后端都可以直接正确处理


@unique
class QuestionCategory(IntEnum):
    SINGLE_CHOICE = 1
    MULTIPLE_CHOICE = 2
    FILL_IN_THE_BLANKS = 3
    SUBJECTIVE = 4


@unique
class GuaranteeStatus(IntEnum):
    WAITING = 0
    AGREEMENT = 1
    REFUSE = 2


@unique
class SchematicType(IntEnum):
    OTHER = 0
    REDSTONE = 1
    ARCHITECTURE = 2


@unique
class UserStatus(IntEnum):
    INACTIVE = 0
    ACTIVE = 1
    TEMP_BANNED = 2
    PERM_BANNED = 3
    DELETED = 4


@unique
class UserRole(StrEnum):
    USER = "user"
    HELPER = "helper"
    ADMIN = "admin"


@unique
class ResponseStatus(IntEnum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    TIMEOUT = 3


@unique
class WhitelistType(IntEnum):
    EXAM = 0
    GUARANTEE = 1
    OTHER = 2


class User(UserMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_qq: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    _password_hash: Mapped[str] = mapped_column("password", String(100), nullable=False, init=False)
    role: Mapped[UserRole] = mapped_column(String(100), nullable=False, default=UserRole.USER)
    registered_at: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), nullable=False
    )
    avatar: Mapped[str] = mapped_column(String(500), default=DEFAULT_AVATAR)  # 头像的 UUID
    status: Mapped[UserStatus] = mapped_column(Integer, nullable=False, default=0)
    tokens: Mapped[list["Token"]] = relationship(back_populates="token_user", init=False)
    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", init=False
    )

    # 拥有的白名单
    whitelist: Mapped[list["Whitelist"]] = relationship(
        foreign_keys="Whitelist.user_id",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
    )

    # 作为审核人的白名单（审核了哪些白名单）
    audited_whitelist: Mapped[list["Whitelist"]] = relationship(
        foreign_keys="Whitelist.auditor_uid", back_populates="auditor", init=False
    )

    # 担保人身份：我作为担保人的担保记录
    guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee", foreign_keys="Guarantee.guarantee_id", back_populates="guarantor", lazy="select", init=False
    )
    # 申请人身份：我作为申请人的担保记录
    applicant_guarantees: Mapped[list["Guarantee"]] = relationship(
        "Guarantee", foreign_keys="Guarantee.applicant_id", back_populates="applicant_user", lazy="select", init=False
    )

    responses: Mapped[list["Response"]] = relationship(back_populates="user", cascade="all, delete", init=False)
    reset_password_token: Mapped[list["ResetPasswordToken"]] = relationship(
        back_populates="user_r_p_t", cascade="all, delete", init=False
    )
    activation_token: Mapped[list["ActivationToken"]] = relationship(
        back_populates="user_active", cascade="all, delete", init=False
    )

    @property
    def password(self) -> str:
        """禁止直接读取密码哈希"""
        raise AttributeError("密码不可读取！如果需要比较新旧密码是否一致，请使用 check_password() 进行校验")

    @password.setter
    def password(self, raw_password: str) -> None:
        """所有赋值自动哈希，内建安全逻辑"""
        self._password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")  # type: ignore[reportUnknownMemberType]

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self._password_hash, password)  # type: ignore[reportUnknownMemberType]

    @property
    def has_play_permission(self):
        """查看用户是否拥有至少一个白名单"""
        stmt = select(exists().where(Whitelist.user_id == self.id))
        return db.session.execute(stmt).scalar()


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # 1:1 关系
        nullable=False,
    )
    user: Mapped["User"] = relationship(back_populates="profile", init=False)
    bio: Mapped[str | None] = mapped_column(Text, default=None)  # 个人简介
    website: Mapped[str | None] = mapped_column(String(500), default=None)
    background_url: Mapped[str | None] = mapped_column(LONGTEXT, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME,
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Whitelist(Base):
    __tablename__ = "whitelist"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[Optional["User"]] = relationship(foreign_keys=[user_id], back_populates="whitelist", init=False)
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    auditor_uid: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    auditor: Mapped[Optional["User"]] = relationship(
        foreign_keys=[auditor_uid], back_populates="audited_whitelist", init=False
    )
    source: Mapped[WhitelistType] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), nullable=False
    )


# 问卷插槽表
class SurveySlot(Base):
    __tablename__ = "survey_slot"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    slot_name: Mapped[str] = mapped_column(String(25), nullable=False)
    mounted_survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id"), nullable=False)


# 问卷表模型
class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), nullable=False
    )
    questions: Mapped[list["Question"]] = relationship(back_populates="survey", cascade="all, delete", init=False)
    response_list: Mapped[list["Response"]] = relationship(
        back_populates="res_survey", cascade="all, delete", init=False
    )


# 问题表模型
# 题目一般是逻辑删除，但是当题目所属的问卷被删除时，题目会被彻底删除！
class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    survey: Mapped["Survey"] = relationship(back_populates="questions", init=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)
    question_type: Mapped[QuestionCategory] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    logical_deletion: Mapped[bool] = mapped_column(default=False)
    create_time: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), nullable=False
    )
    img_list: Mapped[list["QuestionImgURL"]] = relationship(backref="image_question", cascade="all, delete", init=False)
    options: Mapped[list["Option"]] = relationship(backref="option_question", cascade="all, delete", init=False)
    response_details: Mapped[list["ResponseDetail"]] = relationship(
        backref="question_r_d", cascade="all, delete", init=False
    )

    __table_args__ = (Index("idx_question_id_logical", "id", "logical_deletion"),)

    @classmethod
    def create(
        cls,
        survey_id: int,
        question_text: str,
        question_type: QuestionCategory,
        score: float,
        target_display_order: int | None = None,
    ) -> Self:
        """
        如果 target_display_order 是 None，在末尾插入题目
        如提供了 target_display_order，在指定位置插入一个问题，并调整后续问题的顺序
        """
        if target_display_order is None:
            # 获取当前最大排序值
            stmt = select(func.max(cls.display_order)).where(
                cls.survey_id == survey_id, cls.logical_deletion.is_(False)
            )
            max_order = db.session.scalar(stmt)
            target_display_order = 1 if max_order is None else max_order + 1

        else:
            # 直接将目标位置及之后的所有题目 display_order + 1
            shift_stmt = (
                update(cls)
                .where(
                    cls.survey_id == survey_id,
                    cls.display_order >= target_display_order,
                    cls.logical_deletion.is_(False),
                )
                .values(display_order=cls.display_order + 1)
            )
            db.session.execute(shift_stmt)

        return cls(
            survey_id=survey_id,
            question_text=question_text,
            question_type=question_type,
            score=score,
            display_order=target_display_order,
        )


# 问题图片表模型
class QuestionImgURL(Base):
    __tablename__ = "question_images"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所属问题id，外键，关联问题表，级联删除
    img_data: Mapped[str] = mapped_column(LONGTEXT, nullable=False)  # 图片数据，URL 或者 Base64 编码的图片
    img_alt: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))


# 选项表模型
class Option(Base):
    __tablename__ = "options"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )  # 所属问题id，外键，关联问题表，级联删除
    option_text: Mapped[str] = mapped_column(Text, nullable=False)  # 选项内容，不允许为空
    is_correct: Mapped[bool] = mapped_column(Boolean)  # 是否为正确选项，对于有标准答案的题目，可为空
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))


# 答卷表模型
class Response(Base):
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="responses", init=False)
    survey_id: Mapped[int] = mapped_column(Integer, ForeignKey("surveys.id"), nullable=False)
    survey_name: Mapped[str] = mapped_column(String(200), nullable=True)  # 问卷可能被删除，保留问卷名称
    res_survey: Mapped["Survey"] = relationship(back_populates="response_list", init=False)

    response_details: Mapped[list["ResponseDetail"]] = relationship(
        "ResponseDetail", backref="response_d", cascade="all, delete", init=False
    )  # 与答题详情表建立一对多关系，级联删除
    response_score: Mapped[list["ResponseScore"]] = relationship(
        "ResponseScore", backref="response_s", cascade="all, delete", init=False
    )
    reviewer_uid: Mapped[int | None] = mapped_column(Integer, nullable=True, init=False)
    archive_score: Mapped[float | None] = mapped_column(Float, nullable=True, init=False)
    submit_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, nullable=True, init=False)
    end_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, nullable=True, init=False)
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    is_reviewed: Mapped[ResponseStatus] = mapped_column(Integer, default=ResponseStatus.PENDING)


class ResponseScore(Base):
    __tablename__ = "response_scores"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    score: Mapped[float] = mapped_column()
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    response_id: Mapped[int] = mapped_column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False)


# 答题详情表模型
class ResponseDetail(Base):
    __tablename__ = "response_details"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    response_id: Mapped[int] = mapped_column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    answer: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # 用户答案，对于选择题存储选项id，对于简答题存储答案文本，不允许为空
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))


class Guarantee(Base):
    __tablename__ = "guarantees"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    guarantee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)  # 担保人id
    applicant_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)  # 申请人id
    player_name: Mapped[str] = mapped_column(String(25), nullable=False)  # 被担保玩家昵称
    player_uuid: Mapped[str] = mapped_column(String(36), nullable=False)  # 被担保人UUID
    expiration_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, nullable=False)
    status: Mapped[GuaranteeStatus] = mapped_column(Integer, nullable=False, default=GuaranteeStatus.WAITING)
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))

    guarantor: Mapped["User"] = relationship(
        "User", foreign_keys=[guarantee_id], back_populates="guarantees", init=False
    )

    applicant_user: Mapped["User"] = relationship(
        "User", foreign_keys=[applicant_id], back_populates="applicant_guarantees", init=False
    )

    @property
    def status_text(self) -> str:
        """获取状态的中文含义"""
        STATUS_MAP: dict[int, str] = {
            0: "待同意",
            1: "已同意",
            2: "已拒绝",
        }
        return STATUS_MAP.get(self.status, "未知状态")


class Token(Base):
    __tablename__ = "token"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="tokens", init=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default_factory=lambda: datetime.now(UTC) + timedelta(minutes=60), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class RegistrationLimit(Base):
    __tablename__ = "registration_limits"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)  # 支持IPv6的最大长度
    register_time: Mapped[datetime] = mapped_column(DateTime, default_factory=lambda: datetime.now(UTC), nullable=False)


class ResetPasswordToken(Base):
    __tablename__ = "reset_password_token"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_r_p_t: Mapped["User| None"] = relationship(back_populates="reset_password_token", init=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default_factory=lambda: datetime.now(UTC) + timedelta(minutes=60), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ActivationToken(Base):
    __tablename__ = "activation_token"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    user_active: Mapped["User"] = relationship(back_populates="activation_token", init=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default_factory=lambda: datetime.now(UTC) + timedelta(minutes=60), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ConfigModel(Base):
    __tablename__ = "config"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))
    update_time: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


# 投影信息表
class Schematic(Base):
    __tablename__ = "schematics"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 投影文件名 (30个汉字，这里设为100字符足够容纳)
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    uploader: Mapped["User"] = relationship("User", backref="schematics", init=False)
    original_author: Mapped[str] = mapped_column(String(100), nullable=True)
    schematic_type: Mapped[SchematicType] = mapped_column(Integer, nullable=False)
    game_version: Mapped[str] = mapped_column(String(50), nullable=False)
    tag: Mapped[str] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    file_size_KB: Mapped[int] = mapped_column(Integer, nullable=False)
    backup_link: Mapped[str] = mapped_column(String(255), nullable=True)  # 文件备用链接
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)

    upload_date: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))

    update_date: Mapped[datetime] = mapped_column(
        TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # 与文件分表建立一对一关系 (cascade确保删除主表时，关联的二进制文件也被删除)
    file_data: Mapped["SchematicFile"] = relationship(
        back_populates="schematics",  # 建立双向关系，两端的数据状态会自动保持同步
        cascade="all, delete-orphan",  # ORM 层操作
        uselist=False,
        # 这是实现一对一关系的核心参数。默认情况下，relationship 返回的是一个列表（一对多）。
        # 将其设置为 False 后，SQLAlchemy 知道这个属性返回的是单个对象而不是列表
        default=None,
    )

    @staticmethod
    def type_to_enum(type_: str | int) -> SchematicType | None:
        """将前端传入的类型值转换为合法的枚举整数值"""
        if isinstance(type_, str):
            upper_val = type_.upper()
            try:
                return SchematicType[upper_val]
            except KeyError:
                return None

        return SchematicType(type_)

    def __repr__(self):
        return f"<Schematics for ID {self.id}>"


# 投影文件二进制分表
class SchematicFile(Base):
    __tablename__ = "schematic_files"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    # 外键关联投影主表
    schematic_id: Mapped[int] = mapped_column(Integer, ForeignKey("schematics.id"), nullable=False, unique=True)

    # 文件二进制字段 (最大512KB = 524288 Bytes)
    file_blob: Mapped[bytes] = mapped_column(LargeBinary(524288), nullable=False)

    # 反向关联回主表
    schematics: Mapped["Schematic"] = relationship(back_populates="file_data", init=False)

    def __repr__(self):
        return f"<SchematicFiles for ID {self.schematic_id}>"


class StatusLog(Base):
    __tablename__ = "statuslog"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    server_address: Mapped[str] = mapped_column(String(100))
    player_count: Mapped[int] = mapped_column(Integer)
    create_time: Mapped[datetime] = mapped_column(TZ_AWARE_DATETIME, default_factory=lambda: datetime.now(UTC))
