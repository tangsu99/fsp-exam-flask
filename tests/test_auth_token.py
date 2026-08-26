"""单元测试：认证 token 生成（不依赖真实邮件服务器，发送环节通过 mock 屏蔽）"""

import base64
import json
import re
from typing import Any

import pytest
from flask import Flask
from pytest_mock import MockerFixture
from sqlalchemy import select

from myapp import db
from myapp.auth import generate_token, send_activation_mail, send_reset_password
from myapp.db_model import ActivationToken, ResetPasswordToken, User, UserRole, UserStatus

# secrets.token_urlsafe 的字符集：[A-Za-z0-9_-]
URLSAFE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _parse_payload(token: str) -> dict[str, Any]:
    """手动解析 JWT 的 payload 段（不验签；测试仅校验生成内容与过期时间）"""
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


@pytest.fixture()
def user(app: Flask) -> User:
    u = User(username="testuser", user_qq="123456789", role=UserRole.USER, status=UserStatus.INACTIVE)
    u.password = "Abc12345!"
    db.session.add(u)
    db.session.commit()
    return u


class TestEmailToken:
    """邮件激活/重置密码 token 应使用 secrets.token_urlsafe 不透明随机串（非 JWT）"""

    def test_activation_token_is_urlsafe_and_stored(self, app: Flask, user: User, mocker: MockerFixture) -> None:
        mocker.patch("myapp.auth.send_mail")  # 屏蔽真实邮件发送

        send_activation_mail(user)

        row = db.session.scalar(select(ActivationToken).where(ActivationToken.user_id == user.id))
        assert row is not None
        token = row.token

        assert "." not in token, "不应是 JWT（JWT 以点分隔为三段）"
        assert len(token) == 43, "secrets.token_urlsafe(32) 应为 43 字符"
        assert URLSAFE_PATTERN.fullmatch(token) is not None

    def test_reset_password_token_is_urlsafe_and_stored(self, app: Flask, user: User, mocker: MockerFixture) -> None:
        mocker.patch("myapp.auth.send_mail")

        send_reset_password(user)

        row = db.session.scalar(select(ResetPasswordToken).where(ResetPasswordToken.user_id == user.id))
        assert row is not None
        token = row.token

        assert "." not in token
        assert len(token) == 43
        assert URLSAFE_PATTERN.fullmatch(token) is not None


class TestJwtLoginToken:
    """登录 JWT 应携带完整标准声明，且 exp 与 expires_in 精确一致"""

    def test_payload_has_standard_claims(self, user: User) -> None:
        payload = _parse_payload(generate_token(user))

        assert payload["user_id"] == user.id
        assert payload["iss"] == "fsp-exam"
        assert "iat" in payload
        assert "jti" in payload
        assert "exp" in payload

    def test_exp_equals_one_hour_by_default(self, user: User) -> None:
        payload = _parse_payload(generate_token(user))

        assert payload["exp"] - payload["iat"] == 3600  # 默认 1 小时（秒）

    def test_jti_is_unique_per_token(self, user: User) -> None:
        p1 = _parse_payload(generate_token(user))
        p2 = _parse_payload(generate_token(user))

        assert p1["jti"] != p2["jti"]
