"""单元测试：myapp.utils 中的纯函数"""

import io
from datetime import UTC, datetime

import pytest
from werkzeug.datastructures import FileStorage

from myapp.utils import (
    check_password_format,
    get_file_size,
    is_white_list_url,
    parse_dt_to_iso_utc,
    parse_frontend_time_to_utc,
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
    def test_valid_passwords(self, password: str):
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
    def test_invalid_passwords(self, password: str):
        """各种无效密码均应返回 False"""
        assert check_password_format(password) is False


class TestIsWhiteListUrl:
    """测试 URL 白名单检测"""

    def test_empty_string(self):
        assert is_white_list_url("") is True
        assert is_white_list_url("   ") is True

    def test_baidu_pan_url(self):
        assert is_white_list_url("https://pan.baidu.com/s/abc123") is True
        assert is_white_list_url("https://pan.baidu.com/share/init?s=xxx") is True

    def test_quark_pan_url(self):
        assert is_white_list_url("https://pan.quark.cn/s/abc123") is True

    def test_lanzou_url(self):
        assert is_white_list_url("https://www.lanzou.com/abc123") is True
        assert is_white_list_url("https://abc.lanzou.com/xxx") is True
        assert is_white_list_url("https://xxx.lanzoup.com/yyy") is True

    def test_non_whitelist_url(self):
        assert is_white_list_url("https://example.com/file") is False
        assert is_white_list_url("https://pan.google.com") is False
        assert is_white_list_url("https://123pan.com/abc") is False
        assert is_white_list_url("random text") is False


class TestGetFileSize:
    """测试文件大小获取"""

    @staticmethod
    def _make_fs(content: bytes) -> FileStorage:
        return FileStorage(stream=io.BytesIO(content))

    def test_kb(self):
        f = self._make_fs(b"x" * 2048)
        assert get_file_size(f, "KB") == 2

    def test_mb(self):
        f = self._make_fs(b"x" * (2 * 1024 * 1024))
        assert get_file_size(f, "MB") == 2

    def test_gb(self):
        f = self._make_fs(b"x" * (3 * 1024**3))
        assert get_file_size(f, "GB") == 3

    def test_minimum_size(self):
        f = self._make_fs(b"x" * 100)
        assert get_file_size(f, "KB") == 1

    def test_default_unit_is_kb(self):
        f = self._make_fs(b"x" * 2048)
        assert get_file_size(f) == 2

    def test_empty_file(self):
        f = self._make_fs(b"")
        assert get_file_size(f, "KB") == 1


class TestParseFrontendTimeToUtc:
    """测试前端 ISO 时间 → UTC datetime 解析"""

    def test_parse(self):
        result = parse_frontend_time_to_utc("2026-06-07T10:43:00.000Z")
        expected = datetime(2026, 6, 7, 10, 43, 0, 0, tzinfo=UTC)
        assert result == expected

    def test_round_trip(self):
        """解析后再格式化应得到原始字符串（UTC）"""
        dt = parse_frontend_time_to_utc("2026-06-07T10:43:00.000Z")
        assert dt.isoformat() == "2026-06-07T10:43:00+00:00"


class TestParseDtToIsoUtc:
    """测试 datetime → ISO UTC 字符串"""

    def test_naive_datetime(self):
        dt = datetime(2026, 6, 7, 10, 43, 0)
        assert parse_dt_to_iso_utc(dt) == "2026-06-07T10:43:00+00:00"

    def test_already_utc(self):
        dt = datetime(2026, 6, 7, 10, 43, 0, tzinfo=UTC)
        assert parse_dt_to_iso_utc(dt) == "2026-06-07T10:43:00+00:00"

    def test_other_timezone(self):
        """其他时区的 datetime 会被替换为 UTC"""
        from datetime import timedelta, timezone

        dt = datetime(2026, 6, 7, 18, 43, 0, tzinfo=timezone(timedelta(hours=8)))
        result = parse_dt_to_iso_utc(dt)
        assert result == "2026-06-07T18:43:00+00:00"
