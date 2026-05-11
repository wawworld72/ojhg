"""Token-based similarity analyzer for student code submissions."""
import re
from typing import Iterable


def _tokenize_python(code: str) -> list[str]:
    """Normalize and tokenize Python code."""
    code = re.sub(r"#.*", "", code)
    code = re.sub(r'""".*?"""', '""', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", "''", code, flags=re.DOTALL)
    code = re.sub(r'"[^"]*"', '"STR"', code)
    code = re.sub(r"'[^']*'", "'STR'", code)
    code = re.sub(r"\b\d+(\.\d+)?\b", "NUM", code)
    code = re.sub(r"\b(def|class)\s+\w+", r"\1 IDENT", code)
    tokens = re.findall(r"[a-zA-Z_]\w*|[^\s\w]", code)
    return tokens


def _tokenize_java(code: str) -> list[str]:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r'"[^"]*"', '"STR"', code)
    code = re.sub(r"\b\d+[lLfFdD]?\b", "NUM", code)
    code = re.sub(r"\b(class|interface|enum)\s+\w+", r"\1 IDENT", code)
    tokens = re.findall(r"[a-zA-Z_]\w*|[^\s\w]", code)
    return tokens


def _tokenize_cpp(code: str) -> list[str]:
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r'"[^"]*"', '"STR"', code)
    code = re.sub(r"\b\d+[uUlLfF]*\b", "NUM", code)
    code = re.sub(r"\b(class|struct)\s+\w+", r"\1 IDENT", code)
    tokens = re.findall(r"[a-zA-Z_]\w*|[^\s\w]", code)
    return tokens


def tokenize(code: str, language: str) -> list[str]:
    lang = language.lower()
    if "python" in lang:
        return _tokenize_python(code)
    elif "java" in lang:
        return _tokenize_java(code)
    elif "cpp" in lang or "c17" in lang or lang in ("c", "cpp"):
        return _tokenize_cpp(code)
    else:
        return re.findall(r"\S+", code)


def _ngrams(tokens: list[str], n: int = 5) -> set[tuple]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def compute_jaccard_similarity(code_a: str, lang_a: str, code_b: str, lang_b: str) -> float:
    """Compute Jaccard similarity of token n-gram sets. Returns 0.0–100.0."""
    tokens_a = tokenize(code_a, lang_a)
    tokens_b = tokenize(code_b, lang_b)

    if len(tokens_a) < 5 or len(tokens_b) < 5:
        return 0.0

    ngrams_a = _ngrams(tokens_a)
    ngrams_b = _ngrams(tokens_b)

    if not ngrams_a or not ngrams_b:
        return 0.0

    intersection = len(ngrams_a & ngrams_b)
    union = len(ngrams_a | ngrams_b)

    if union == 0:
        return 0.0

    return round((intersection / union) * 100.0, 2)
