"""Wraps analysis text with a standard opinion disclaimer.

Single source of truth for the "In my Opinion / not financial advice" framing
used both standalone (CLI) and wired into the pipeline scripts.
"""

OPINION_PREFIX = "In my Opinion,"
DISCLAIMER_SUFFIX = "This is not a financial advice, just my view."


def wrap_analysis(text: str) -> str:
    return f"{OPINION_PREFIX} {text.strip()}\n\n{DISCLAIMER_SUFFIX}"


if __name__ == "__main__":
    import sys

    content = " ".join(sys.argv[1:]) or input("Analysis text: ")
    print(wrap_analysis(content))
