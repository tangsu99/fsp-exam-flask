"""pytest 全局配置：为测试设置必要的环境变量与共享 fixture"""

import os
from collections.abc import Iterator

# 在导入 myapp 之前设置测试数据库，避免 myapp/__init__.py 因缺少 DATABASE_URL 而报错
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from flask import Flask  # noqa: E402
from sqlalchemy.dialects import mysql  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


# sqlite 不支持 MySQL 的 LONGTEXT 类型，测试环境将其编译为 TEXT
@compiles(mysql.LONGTEXT, "sqlite")
def _compile_longtext_sqlite(type_, compiler, **kw):  # type: ignore[no-untyped-def]
    return "TEXT"


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    """收集测试前创建应用，使全局 APP / db / limiter 初始化完成。"""
    import myapp

    myapp.create_app()


@pytest.fixture()
def app() -> Iterator[Flask]:
    """复用全局测试应用，并自动进入应用上下文（sqlite 内存库，跨测试共享，数据由 _clean_tables 清理）"""
    import myapp

    ctx = myapp.APP.app_context()
    ctx.push()
    yield myapp.APP
    ctx.pop()


@pytest.fixture(autouse=True)
def _clean_tables(app: Flask) -> Iterator[None]:  # type: ignore[reportUnusedFunction]
    """每个测试前清空业务表，保证用例隔离"""
    from myapp import db
    from myapp.db_model import (
        ActivationToken,
        Guarantee,
        Profile,
        RegistrationLimit,
        ResetPasswordToken,
        Response,
        Schematic,
        StatusLog,
        Token,
        User,
        Whitelist,
    )

    for model in (
        Token,
        ActivationToken,
        ResetPasswordToken,
        Profile,
        Whitelist,
        Guarantee,
        Response,
        Schematic,
        StatusLog,
        RegistrationLimit,
    ):
        db.session.query(model).delete()
    db.session.query(User).delete()
    db.session.commit()
    yield
