"""Output comparison for judge verdicts."""


def normalize_output(text: str) -> list[str]:
    """Strip trailing whitespace per line and normalize line endings."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    return [line.rstrip() for line in lines]


def compare_outputs(actual: str, expected: str) -> str:
    """Compare actual vs expected output. Returns 'ACCEPTED' or 'WRONG_ANSWER'."""
    if normalize_output(actual) == normalize_output(expected):
        return "ACCEPTED"
    return "WRONG_ANSWER"
