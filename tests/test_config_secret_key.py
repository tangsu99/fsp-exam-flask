"""单元测试：SECRET_KEY 解析策略（环境变量优先，否则随机生成，且不落库）"""

from typing import cast

import pytest
from flask import Flask
from sqlalchemy import select

from myapp import db
from myapp.config import Config
from myapp.db_model import ConfigModel


def _make_config(app: Flask) -> Config:
    """构造一个不触发 __init__（需数据库）的 Config 实例，仅用于测试私有方法"""
    cfg = Config.__new__(Config)
    cfg.app = app
    cfg.db = db
    return cfg


def _call_private(cfg: Config, method: str) -> None:
    """通过 getattr 调用 Config 的私有方法（避免名称改写与 pyright reportPrivateUsage）"""
    getattr(cfg, method)()


class TestApplySecretKey:
    def test_env_var_has_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "env-secret-key-0123456789abcdef")
        app = Flask(__name__)

        _call_private(_make_config(app), "_Config__apply_secret_key")

        assert app.config["SECRET_KEY"] == "env-secret-key-0123456789abcdef"

    def test_random_fallback_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
        app = Flask(__name__)

        _call_private(_make_config(app), "_Config__apply_secret_key")

        key = cast(str, app.config["SECRET_KEY"])
        assert key != ""
        assert len(key) == 64  # secrets.token_hex(32) 生成 64 位十六进制

    def test_random_keys_differ_between_starts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
        app1, app2 = Flask(__name__), Flask(__name__)

        _call_private(_make_config(app1), "_Config__apply_secret_key")
        _call_private(_make_config(app2), "_Config__apply_secret_key")

        assert app1.config["SECRET_KEY"] != app2.config["SECRET_KEY"]


class TestPurgeSecretKey:
    def test_purges_legacy_secret_key_row(self, app: Flask) -> None:
        db.session.add(ConfigModel(key="SECRET_KEY", value="legacy-weak", type="str", description=""))
        db.session.commit()

        _call_private(_make_config(app), "_Config__purge_secret_key_from_db")

        remaining = db.session.scalar(select(ConfigModel).where(ConfigModel.key == "SECRET_KEY"))
        assert remaining is None

    def test_keeps_other_config_rows(self, app: Flask) -> None:
        db.session.add(ConfigModel(key="TEST_UNIQUE_KEY", value="abc", type="str", description=""))
        db.session.add(ConfigModel(key="SECRET_KEY", value="legacy-weak", type="str", description=""))
        db.session.commit()

        _call_private(_make_config(app), "_Config__purge_secret_key_from_db")

        other = db.session.scalar(select(ConfigModel).where(ConfigModel.key == "TEST_UNIQUE_KEY"))
        secret = db.session.scalar(select(ConfigModel).where(ConfigModel.key == "SECRET_KEY"))
        assert other is not None
        assert secret is None
