"""Tests for judge output comparison."""
import pytest

from judge.compare import compare_outputs, normalize_output


class TestNormalizeOutput:
    def test_basic_normalization(self):
        output = "hello\nworld\n"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_trailing_spaces(self):
        output = "hello   \nworld  \n"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_crlf_line_endings(self):
        output = "hello\r\nworld\r\n"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_cr_only_line_endings(self):
        output = "hello\rworld\r"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_trailing_empty_lines(self):
        output = "hello\nworld\n\n\n"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_trailing_whitespace_lines(self):
        output = "hello\nworld\n  \n\t\n"
        result = normalize_output(output)
        assert result == ["hello", "world"]

    def test_empty_input(self):
        output = ""
        result = normalize_output(output)
        assert result == []

    def test_only_whitespace(self):
        output = "  \n\t\n  \n"
        result = normalize_output(output)
        assert result == []

    def test_no_trailing_newline(self):
        output = "hello\nworld"
        result = normalize_output(output)
        assert result == ["hello", "world"]


class TestCompareOutputs:
    def test_exact_match(self):
        actual = "hello\nworld\n"
        expected = "hello\nworld\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_trailing_space_difference(self):
        actual = "hello\nworld\n"
        expected = "hello  \nworld  \n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_line_ending_difference(self):
        actual = "hello\nworld\n"
        expected = "hello\r\nworld\r\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_trailing_newline_difference(self):
        actual = "hello\nworld"
        expected = "hello\nworld\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_wrong_answer_content(self):
        actual = "hello\nworld\n"
        expected = "hello\nworld2\n"
        assert compare_outputs(actual, expected) == "WRONG_ANSWER"

    def test_wrong_answer_extra_line(self):
        actual = "hello\nworld\nextra\n"
        expected = "hello\nworld\n"
        assert compare_outputs(actual, expected) == "WRONG_ANSWER"

    def test_wrong_answer_missing_line(self):
        actual = "hello\n"
        expected = "hello\nworld\n"
        assert compare_outputs(actual, expected) == "WRONG_ANSWER"

    def test_empty_outputs(self):
        actual = ""
        expected = ""
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_whitespace_only_outputs(self):
        actual = "  \n\t\n"
        expected = "\n\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_multiline_numbers(self):
        actual = "1\n2\n3\n"
        expected = "1\n2\n3\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"

    def test_floating_point_output(self):
        actual = "3.14159\n2.71828\n"
        expected = "3.14159\n2.71828\n"
        assert compare_outputs(actual, expected) == "ACCEPTED"
