"""单元测试：myapp.utils 中的纯函数"""

import io
from datetime import UTC, datetime

import pytest
from werkzeug.datastructures import FileStorage

from myapp.utils import (
    check_data_size,
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
        """其他时区的 datetime 会被真正转换到 UTC（如 UTC+8 → UTC-8小时）"""
        from datetime import timedelta, timezone

        dt = datetime(2026, 6, 7, 18, 43, 0, tzinfo=timezone(timedelta(hours=8)))
        result = parse_dt_to_iso_utc(dt)
        assert result == "2026-06-07T10:43:00+00:00"


class TestCheckDataSize:
    """测试字符串数据大小校验"""

    def test_within_kb_limit(self):
        """1KB 以内的数据，限制 1KB 应通过"""
        data = "a" * 500
        assert check_data_size(data, "KB", 1) is True

    def test_exceed_kb_limit(self):
        """超过 1KB 的数据应被拒绝"""
        data = "a" * 1500
        assert check_data_size(data, "KB", 1) is False

    def test_within_mb_limit(self):
        """4MB 的数据，限制 5MB 应通过"""
        data = "a" * (4 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is True

    def test_exceed_mb_limit(self):
        """6MB 的数据，限制 5MB 应被拒绝"""
        data = "a" * (6 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is False

    def test_gb_limit(self):
        """500MB 的数据，限制 1GB 应通过"""
        data = "a" * (500 * 1024 * 1024)
        assert check_data_size(data, "GB", 1) is True

    def test_exact_boundary(self):
        """正好等于限制值应通过"""
        data = "a" * (5 * 1024 * 1024)
        assert check_data_size(data, "MB", 5) is True

    def test_empty_string(self):
        """空字符串应通过"""
        assert check_data_size("", "MB", 5) is True

    def test_unicode_data(self):
        """中文字符（多字节编码）应正确计算大小"""
        data = "你好世界"
        # UTF-8 下每个中文 3 字节，共 12 字节
        assert check_data_size(data, "KB", 1) is True
