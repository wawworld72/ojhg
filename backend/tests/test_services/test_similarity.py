"""Tests for similarity analysis service."""
import pytest

from app.services.similarity import compute_jaccard_similarity, tokenize


class TestTokenize:
    def test_tokenize_python_simple(self):
        code = "x = 1\ny = 2"
        tokens = tokenize(code, "python3")
        assert len(tokens) > 0
        assert "x" in tokens
        assert "y" in tokens

    def test_tokenize_python_strings(self):
        code = 'name = "John"'
        tokens = tokenize(code, "python3")
        assert 'STR' in tokens
        assert 'name' in tokens

    def test_tokenize_python_numbers(self):
        code = "x = 123\ny = 45.67"
        tokens = tokenize(code, "python3")
        assert 'NUM' in tokens
        assert 'x' in tokens
        assert 'y' in tokens

    def test_tokenize_python_comments(self):
        code = "x = 1  # this is a comment\ny = 2"
        tokens = tokenize(code, "python3")
        assert "comment" not in tokens
        assert "x" in tokens

    def test_tokenize_java_simple(self):
        code = "int x = 1;"
        tokens = tokenize(code, "java17")
        assert "int" in tokens
        assert "x" in tokens

    def test_tokenize_java_strings(self):
        code = 'String s = "hello";'
        tokens = tokenize(code, "java17")
        assert 'STR' in tokens

    def test_tokenize_cpp_simple(self):
        code = "int x = 1;"
        tokens = tokenize(code, "cpp17")
        assert "int" in tokens
        assert "x" in tokens

    def test_tokenize_empty_code(self):
        code = ""
        tokens = tokenize(code, "python3")
        assert tokens == []


class TestComputeJaccardSimilarity:
    def test_identical_code(self):
        code = "x = 1\ny = 2\nprint(x + y)"
        score = compute_jaccard_similarity(code, "python3", code, "python3")
        assert score == 100.0

    def test_completely_different_code(self):
        code1 = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5"
        code2 = "f = 6\ng = 7\nh = 8\ni = 9\nj = 10"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert score == 0.0

    def test_similar_variable_names(self):
        code1 = "x = 1\ny = 2\nz = x + y"
        code2 = "x = 1\ny = 2\nz = x + y"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert score == 100.0

    def test_same_logic_different_vars(self):
        code1 = "x = 1\ny = 2\nz = x + y\nresult = z * 2\nprint(result)"
        code2 = "a = 1\nb = 2\nc = a + b\nresult = c * 2\nprint(result)"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert 0 < score < 50

    def test_empty_code_similarity(self):
        score = compute_jaccard_similarity("", "python3", "", "python3")
        assert score == 0.0

    def test_short_code_too_small(self):
        code1 = "x = 1\ny"
        code2 = "x = 1\ny"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert score == 0.0

    def test_cross_language_similarity(self):
        code1 = "int x = 1;"
        code2 = "x = 1"
        score = compute_jaccard_similarity(code1, "java17", code2, "python3")
        assert 0 <= score <= 100

    def test_similarity_with_comments_ignored(self):
        code1 = "x = 1\n# comment\ny = 2\n# another comment\nz = x + y"
        code2 = "x = 1\ny = 2\nz = x + y"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert score == 100.0

    def test_similarity_range(self):
        code1 = "for i in range(10):\n    print(i)\nx = 1\ny = 2\nz = 3\na = 4\nb = 5"
        code2 = "for i in range(10):\n    print(i)\nx = 1\ny = 2\nz = 3\na = 5\nb = 6"
        score = compute_jaccard_similarity(code1, "python3", code2, "python3")
        assert 0 <= score <= 100
        assert score > 0
