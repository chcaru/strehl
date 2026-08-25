"""M87 / s36 -- fixes the harness/measurement misclassification, two ways.

verify_s32's smuggling check flagged three of my new scripts. Two flags were
CORRECT and one was a false alarm, and the two need opposite repairs.

CORRECT: 111-provenance.py and 112-launder.py genuinely load
frame cubes and measure images. Giving them a `probe_` prefix excluded them
from the audit's measurement denominator while they were doing measurement,
which is exactly the smuggling the check exists to catch. They are renamed to
numbered measurement scripts. The check was right and I was wrong.

FALSE ALARM: fix_s36_provenance.py is a document editor that never touches an
image. It matched because it QUOTES the string `rawpy.imread` inside a fact
row -- the row that states which reader the headline uses. A regex over
source text cannot distinguish a call from a quotation of a call.

So the check is moved onto the AST and matched against call sites only. That
is a strengthening, not a relaxation: it now tests the property it always
claimed to test ("this script measures an image") rather than a proxy that
any mention satisfies. The regex is retained as a fallback if a file will not
parse, because a syntactically broken script should still be flagged.
"""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parent
DOC = SRC.parents[2] / "docs" / "research" / "M87-occlusion.md"

RENAMES = {"111-provenance.py": "111-provenance.py",
           "112-launder.py": "112-launder.py"}

OLD = '''    if re.search(r"rawpy\\.imread|np\\.load\\(\\s*CACHE", t):
        smuggled.append(p.name)'''

NEW = '''    if _measures_image(t):
        smuggled.append(p.name)'''

HELPER = '''

def _measures_image(t):
    """True if the SOURCE CALLS a frame reader, not merely mentions one.

    The original form of this check was a regex over raw source text. It
    flagged fix_s36_provenance.py, which never opens an image and only quotes
    the reader's name inside a fact row describing which reader the headline
    uses. A quotation is not a call, and a check that cannot tell them apart
    is testing spelling.

    Matching on the AST is not enough on its own either: rendering each call
    back to source and re-applying the regex would flag this very file, whose
    own re.compile() argument necessarily contains the pattern. So the match
    is STRUCTURAL -- an attribute call of the right shape -- which a string
    literal cannot satisfy no matter what it spells.
    """
    import ast
    try:
        tree = ast.parse(t)
    except SyntaxError:
        return True  # unparseable: flag rather than silently pass
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not isinstance(f, ast.Attribute) or not isinstance(f.value, ast.Name):
            continue
        if f.value.id == "rawpy" and f.attr == "imread":
            return True
        if f.value.id == "np" and f.attr == "load" and node.args:
            seg = ast.get_source_segment(t, node.args[0]) or ""
            if "CACHE" in seg:
                return True
    return False
'''


def main():
    # ---- 1. rename the two genuine measurement scripts -------------------
    for old, new in RENAMES.items():
        p, q = SRC / old, SRC / new
        if q.exists():
            print(f"  {new} already exists, skipping rename")
            continue
        if not p.exists():
            sys.exit("EXPECTED SOURCE %s NOT FOUND" % old)
        p.rename(q)
        print(f"  renamed {old} -> {new}")

    # ---- 2. update every reference, including the report -----------------
    targets = sorted(SRC.glob("*.py")) + [DOC]
    for f in targets:
        raw = f.read_bytes().decode("utf-8")
        new = raw
        for o, n in RENAMES.items():
            new = new.replace(o, n)
        if new != raw:
            crlf_before = raw.count("\r\n") == raw.count("\n")
            f.write_bytes(new.encode("utf-8"))
            if crlf_before:
                assert new.count("\r\n") == new.count("\n"), "CRLF broken in %s" % f
            print(f"  updated references in {f.name}")

    # ---- 3. move the smuggling check onto the AST ------------------------
    v = (SRC / "verify_s32.py").read_text(encoding="utf-8")
    if "_measures_image" in v:
        print("  verify_s32 already AST-based")
    else:
        if v.count(OLD) != 1:
            sys.exit("SMUGGLING-CHECK ANCHOR NOT UNIQUE (%d)" % v.count(OLD))
        v = v.replace(OLD, NEW, 1)
        marker = ("import fix_audit  # noqa: E402  -- single owner of the "
                  "harness/measurement split")
        if v.count(marker) != 1:
            sys.exit("MODULE ANCHOR NOT UNIQUE (%d)" % v.count(marker))
        v = v.replace(marker, marker + HELPER, 1)
        (SRC / "verify_s32.py").write_text(v, encoding="utf-8")
        print("  verify_s32.py: smuggling check moved onto the AST")
    return 0


if __name__ == "__main__":
    sys.exit(main())
