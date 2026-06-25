"""Tests for utils/parsing shared functions."""

from utils.parsing import parse_kda, parse_int, parse_time


class TestParseKda:
    def test_normal(self):
        assert parse_kda("5/3/12") == (5, 3, 12)

    def test_with_spaces(self):
        assert parse_kda("5 / 3 / 12") == (5, 3, 12)

    def test_zeros(self):
        assert parse_kda("0/0/0") == (0, 0, 0)

    def test_empty(self):
        assert parse_kda("") == (0, 0, 0)

    def test_none_like(self):
        assert parse_kda(None) == (0, 0, 0)  # type: ignore[arg-type]

    def test_invalid_format(self):
        assert parse_kda("abc") == (0, 0, 0)

    def test_two_parts(self):
        assert parse_kda("5/3") == (0, 0, 0)


class TestParseInt:
    def test_normal(self):
        assert parse_int("123") == 123

    def test_with_comma(self):
        assert parse_int("12,345") == 12345

    def test_with_spaces(self):
        assert parse_int("12 345") == 12345

    def test_empty(self):
        assert parse_int("") == 0

    def test_invalid(self):
        assert parse_int("abc") == 0

    def test_none_like(self):
        assert parse_int(None) == 0  # type: ignore[arg-type]


class TestParseTime:
    def test_normal(self):
        assert parse_time("5:30") == 330.0

    def test_zero(self):
        assert parse_time("0:00") == 0.0

    def test_large(self):
        assert parse_time("25:00") == 1500.0

    def test_empty(self):
        assert parse_time("") == 0.0

    def test_invalid(self):
        assert parse_time("abc") == 0.0

    def test_single_number(self):
        assert parse_time("300") == 0.0
