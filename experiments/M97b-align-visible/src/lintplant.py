"""Positive control for the corpus_lint encoding fix (e3c01aa).

The fix is `sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")`.
Running corpus_lint with 0 violations cannot test it: the reporter loop never
runs, and the summary line's em dash is encodable in cp1252 anyway (0x97). So
"both encodings agree" was a null from a probe that never touched the defect.

This exercises the actual failure characters through both arms.
"""

import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "prefix"

# Exactly the characters the fix names: U+0394, U+2192, U+2264, U+2212.
VIOLATION = "docs/research/M0-x.md:1: [C3] \u0394 \u2192 \u2264 \u2212 fail"

if MODE == "postfix":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass

print("header line 1")
print("header line 2")
try:
    print(VIOLATION)
except UnicodeEncodeError as e:
    # Mimic the real failure: die mid-loop, summary never printed, exit 1.
    sys.stderr.write("UnicodeEncodeError: %s\n" % e)
    sys.exit(1)
print("corpus_lint: FAIL - 1 violation(s)")
sys.exit(1)
