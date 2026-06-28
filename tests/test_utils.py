"""单元测试：myapp.utils 中的纯函数"""

import io
from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture
from werkzeug.datastructures import FileStorage

from myapp.db_model import User
from myapp.utils import (
    check_data_size,
    check_password_format,
    get_file_size,
    is_white_list_url,
    parse_dt_to_iso_utc,
    parse_frontend_time_to_utc,
    validate_username,
)


class TestCheckPasswordFormat:
    """测试密码格式校验"""

    @pytest.mark.parametrize(
        "password",
        [
            "Abc12345!",
            "Strong@Pass1",
            "aB3$defghijk",
            "1A@bcdefghijklm",  # 16 位边界
        ],
    )
    def test_valid_passwords(self, password: str) -> None:
        """有效密码（大小写字母 + 数字 + 特殊字符，8~16 位）"""
        assert check_password_format(password) is True

    @pytest.mark.parametrize(
        "password",
        [
            "",  # 空字符串
            "abc12345",  # 无大写和特殊字符
            "ABCD1234!",  # 无小写
            "Abcdefgh!",  # 无数字
            "Abc12345",  # 无特殊字符
            "Ab1@",  # 太短（<8）
            "A1@bcdefghijklmno",  # 太长（>16）
            "12345678!",  # 无字母
            "abcdefgh!",  # 无大写和数字
        ],
    )
    def test_invalid_passwords(self, password: str) -> None:
        """各种无效密码均应返回 False"""
        assert check_password_format(password) is False


class TestIsWhiteListUrl:
    """测试 URL 白名单检测"""

    def test_empty_string(self) -> None:
        assert is_white_list_url("") is True
        assert is_white_list_url("   ") is True

    def test_baidu_pan_url(self) -> None:
        assert is_white_list_url("https://pan.baidu.com/s/abc123") is True
        assert is_white_list_url("https://pan.baidu.com/share/init?s=xxx") is True

    def test_quark_pan_url(self) -> None:
        assert is_white_list_url("https://pan.quark.cn/s/abc123") is True

    def test_lanzou_url(self) -> None:
        assert is_white_list_url("https://www.lanzou.com/abc123") is True
        assert is_white_list_url("https://abc.lanzou.com/xxx") is True
        assert is_white_list_url("https://xxx.lanzoup.com/yyy") is True

    def test_non_whitelist_url(self) -> None:
        assert is_white_list_url("https://example.com/file") is False
        assert is_white_list_url("https://pan.google.com") is False
        assert is_white_list_url("https://123pan.com/abc") is False
        assert is_white_list_url("random text") is False


class TestGetFileSize:
    """测试文件大小获取"""

    @staticmethod
    def _make_fs(content: bytes) -> FileStorage:
        return FileStorage(stream=io.BytesIO(content))

    def test_kb(self) -> None:
        f: FileStorage = self._make_fs(b"x" * 2048)
        assert get_file_size(f, "KB") == 2

    def test_mb(self) -> None:
        f: FileStorage = self._make_fs(b"x" * (2 * 1024 * 1024))
        assert get_file_size(f, "MB") == 2

    def test_gb(self) -> None:
        f: FileStorage = self._make_fs(b"x" * (3 * 1024**3))
        assert get_file_size(f, "GB") == 3

    def test_minimum_size(self) -> None:
        f: FileStorage = self._make_fs(b"x" * 100)
        assert get_file_size(f, "KB") == 1

    def test_default_unit_is_kb(self) -> None:
        f: FileStorage = self._make_fs(b"x" * 2048)
        assert get_file_size(f) == 2

    def test_empty_file(self) -> None:
        f: FileStorage = self._make_fs(b"")
        assert get_file_size(f, "KB") == 1


class TestParseFrontendTimeToUtc:
    """测试前端 ISO 时间 → UTC datetime 解析"""

    def test_parse(self) -> None:
        result: datetime = parse_frontend_time_to_utc("2026-06-07T10:43:00.000Z")
        expected: datetime = datetime(2026, 6, 7, 10, 43, 0, 0, tzinfo=UTC)
        assert result == expected

    def test_round_trip(self) -> None:
        """解析后再格式化应得到原始字符串（UTC）"""
        dt: datetime = parse_frontend_time_to_utc("2026-06-07T10:43:00.000Z")
        assert dt.isoformat() == "2026-06-07T10:43:00+00:00"


class TestParseDtToIsoUtc:
    """测试 datetime → ISO UTC 字符串"""

    def test_naive_datetime(self) -> None:
        dt: datetime = datetime(2026, 6, 7, 10, 43, 0)
        assert parse_dt_to_iso_utc(dt) == "2026-06-07T10:43:00+00:00"

    def test_already_utc(self) -> None:
        dt: datetime = datetime(2026, 6, 7, 10, 43, 0, tzinfo=UTC)
        assert parse_dt_to_iso_utc(dt) == "2026-06-07T10:43:00+00:00"

    def test_other_timezone(self) -> None:
        """其他时区的 datetime 会被真正转换到 UTC（如 UTC+8 → UTC-8小时）"""
        from datetime import timedelta, timezone

        dt: datetime = datetime(2026, 6, 7, 18, 43, 0, tzinfo=timezone(timedelta(hours=8)))
        result: str = parse_dt_to_iso_utc(dt)
        assert result == "2026-06-07T10:43:00+00:00"


class TestCheckDataSize:
    """测试字符串数据大小校验"""

    def test_within_kb_limit(self) -> None:
        """1KB 以内的数据，限制 1KB 应通过"""
        data: str = "a" * 500
        assert check_data_size(data, "KB", 1) is True

    def test_exceed_kb_limit(self) -> None:
        """超过 1KB 的数据应被拒绝"""
        data: str = "a" * 1500
        assert check_data_size(data, "KB", 1) is False

    def test_within_mb_limit(self) -> None:
        """4MB 的数据，限制 5MB 应通过"""
        data: str = "a" * (4 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is True

    def test_exceed_mb_limit(self) -> None:
        """6MB 的数据，限制 5MB 应被拒绝"""
        data: str = "a" * (6 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is False

    def test_gb_limit(self) -> None:
        """500MB 的数据，限制 1GB 应通过"""
        data: str = "a" * (500 * 1024 * 1024)
        assert check_data_size(data, "GB", 1) is True

    def test_exact_boundary(self) -> None:
        """正好等于限制值应通过"""
        data: str = "a" * (5 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is True

    def test_empty_string(self) -> None:
        """空字符串应通过"""
        assert check_data_size("", "MB", 5) is True

    def test_unicode_data(self) -> None:
        """中文字符（多字节编码）应正确计算大小"""
        data: str = "你好世界"
        # UTF-8 下每个中文 3 字节，共 12 字节
        assert check_data_size(data, "KB", 1) is True


class TestValidateUsername:
    """测试用户名校验（不需要数据库 — 纯逻辑部分用 mock 隔离）"""

    # ── 空值校验（不依赖 DB） ──

    def test_empty_string(self) -> None:
        """空字符串应返回 code=1"""
        result: dict[str, Any] = validate_username("")
        assert result["code"] == 1
        assert "不能为空" in result["desc"]

    def test_whitespace_only(self) -> None:
        """纯空白字符应返回 code=1"""
        result: dict[str, Any] = validate_username("   ")
        assert result["code"] == 1
        assert "不能为空" in result["desc"]

    # ── 长度校验（不依赖 DB） ──

    def test_length_exceeds_100(self) -> None:
        """超过 100 字符应返回 code=2"""
        long_name: str = "a" * 101
        result: dict[str, Any] = validate_username(long_name)
        assert result["code"] == 2
        assert "100" in result["desc"]

    def test_length_100_ok(self, mocker: MockerFixture) -> None:
        """正好 100 字符应通过"""
        mocker.patch("myapp.utils.db.session.scalar", return_value=None)
        name: str = "a" * 100
        result: dict[str, Any] = validate_username(name)
        assert result["code"] == 0
        assert result["username"] == name

    # ── 唯一性校验（需要 mock db.session.scalar） ──

    def test_duplicate_username(self, mocker: MockerFixture) -> None:
        """与已存在的用户名重复应返回 code=3"""
        mock_user: User = mocker.Mock(spec=User, id=1)
        mocker.patch("myapp.utils.db.session.scalar", return_value=mock_user)
        result: dict[str, Any] = validate_username("ExistingUser")
        assert result["code"] == 3
        assert "已被使用" in result["desc"]

    def test_unique_username(self, mocker: MockerFixture) -> None:
        """不重复的用户名应通过"""
        mocker.patch("myapp.utils.db.session.scalar", return_value=None)
        result: dict[str, Any] = validate_username("NewUser123")
        assert result["code"] == 0
        assert result["username"] == "NewUser123"

    # ── exclude_user_id 排除自身 ──

    def test_exclude_self_ok(self, mocker: MockerFixture) -> None:
        """排除自身 ID 后，自己的用户名应通过校验"""
        mocker.patch("myapp.utils.db.session.scalar", return_value=None)
        result: dict[str, Any] = validate_username("ExistingUser", exclude_user_id=1)
        assert result["code"] == 0

    def test_exclude_other_still_detects_duplicate(self, mocker: MockerFixture) -> None:
        """排除其他 ID 时，重复用户名仍应被检测到"""
        mock_user: User = mocker.Mock(spec=User, id=2)
        mocker.patch("myapp.utils.db.session.scalar", return_value=mock_user)
        result: dict[str, Any] = validate_username("ExistingUser", exclude_user_id=1)
        assert result["code"] == 3

    # ── 合法用户名（不依赖 DB） ──

    @pytest.mark.parametrize(
        "name",
        [
            "NewUser",
            "abc123",
            "user_name",
            "测试用户",
            "a",
            "你好世界",
        ],
    )
    def test_valid_username(self, mocker: MockerFixture, name: str) -> None:
        """合法用户名应返回 code=0，并返回清洗后的用户名"""
        mocker.patch("myapp.utils.db.session.scalar", return_value=None)
        result: dict[str, Any] = validate_username(name)
        assert result["code"] == 0
        assert result["username"] == name.strip()

    def test_strip_whitespace(self, mocker: MockerFixture) -> None:
        """前后空白应被去除"""
        mocker.patch("myapp.utils.db.session.scalar", return_value=None)
        result: dict[str, Any] = validate_username("  HelloWorld  ")
        assert result["code"] == 0
        assert result["username"] == "HelloWorld"
