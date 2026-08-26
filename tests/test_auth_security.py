"""单元测试：认证安全逻辑（verify_token / is_token_revoked / request_loader / 登录限速）"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
import pytest
from flask import Flask
from sqlalchemy import select

from myapp import db
from myapp.auth import create_token, is_token_revoked, verify_token
from myapp.db_model import Token, User, UserRole, UserStatus

# 登录限速测试专用的唯一 IP（避免与其它测试共用计数）
RATE_LIMIT_TEST_IP = "203.0.113.99"


def _secret(app: Flask) -> str:
    return cast(str, app.config["SECRET_KEY"])


def _make_token(payload: dict[str, Any], secret: str) -> str:
    """构造任意 payload 的 JWT（测试用，绕过 create_token 的入库逻辑）"""
    return cast(str, jwt.encode(payload, secret, algorithm="HS256"))  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]


@pytest.fixture()
def user(app: Flask) -> User:
    u = User(username="securuser", user_qq="987654321", role=UserRole.USER, status=UserStatus.ACTIVE)
    u.password = "Abc12345!"
    db.session.add(u)
    db.session.commit()
    return u


class TestIsTokenRevoked:
    def test_missing_record_is_revoked(self, app: Flask) -> None:
        assert is_token_revoked("no-such-token") is True

    def test_active_record_not_revoked(self, app: Flask, user: User) -> None:
        token = create_token(user)
        assert is_token_revoked(token) is False

    def test_revoked_record(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        record.is_revoked = True
        db.session.commit()
        assert is_token_revoked(token) is True

    def test_deleted_record_is_revoked(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        db.session.delete(record)
        db.session.commit()
        assert is_token_revoked(token) is True


class TestVerifyToken:
    def test_valid_token_returns_user_id(self, app: Flask, user: User) -> None:
        token = create_token(user)
        assert verify_token(token, _secret(app)) == user.id

    def test_expired_token_returns_minus_one(self, app: Flask, user: User) -> None:
        secret = _secret(app)
        expired = _make_token({"user_id": user.id, "exp": datetime.now(UTC) - timedelta(hours=1)}, secret)
        assert verify_token(expired, secret) == -1

    def test_invalid_token_returns_zero(self, app: Flask) -> None:
        assert verify_token("not-a-jwt", _secret(app)) == 0

    def test_revoked_token_returns_two(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        record.is_revoked = True
        db.session.commit()
        assert verify_token(token, _secret(app)) == 2

    def test_deleted_token_returns_two(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        db.session.delete(record)
        db.session.commit()
        assert verify_token(token, _secret(app)) == 2


class TestRequestLoader:
    """request_loader：真正用于认证的路径，吊销/删除/过期 token 均应被拒绝"""

    def test_valid_token_authenticates(self, app: Flask, user: User) -> None:
        token = create_token(user)
        resp = app.test_client().post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.get_json()["code"] == 0  # 登录成功进入 logout

    def test_revoked_token_rejected(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        record.is_revoked = True
        db.session.commit()
        resp = app.test_client().post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.get_json()["code"] == 1  # 未登录

    def test_deleted_token_rejected(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        db.session.delete(record)
        db.session.commit()
        resp = app.test_client().post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.get_json()["code"] == 1  # 未登录

    def test_expired_token_rejected(self, app: Flask, user: User) -> None:
        token = create_token(user)
        record = db.session.scalar(select(Token).where(Token.token == token))
        assert record is not None
        record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.session.commit()
        resp = app.test_client().post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.get_json()["code"] == 1  # 未登录


class TestLoginRateLimit:
    """登录接口限速：同一 IP 每分钟最多 5 次，第 6 次返回 429"""

    def test_sixth_attempt_returns_429(self, app: Flask) -> None:
        client = app.test_client()
        codes: list[int] = []
        for _ in range(6):
            resp = client.post(
                "/auth/login",
                json={"username": "nobody", "password": "wrong"},
                headers={"X-Forwarded-For": RATE_LIMIT_TEST_IP},
            )
            codes.append(resp.status_code)

        assert codes[:5] == [200, 200, 200, 200, 200]
        assert codes[5] == 429
