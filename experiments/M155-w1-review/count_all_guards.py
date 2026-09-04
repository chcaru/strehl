import ast
import json
from pathlib import Path

source = Path("projects/strehl/experiments/M138-w1-gate-audit/adjudicate.py").read_text(
    encoding="utf-8"
)
tree = ast.parse(source)
counts = {
    "if": 0,
    "ifexp": 0,
    "while": 0,
    "comprehension-if": 0,
    "match-guard": 0,
    "assert": 0,
}
for node in ast.walk(tree):
    if isinstance(node, ast.If):
        counts["if"] += 1
    elif isinstance(node, ast.IfExp):
        counts["ifexp"] += 1
    elif isinstance(node, ast.While):
        counts["while"] += 1
    elif isinstance(node, ast.comprehension):
        counts["comprehension-if"] += len(node.ifs)
    elif isinstance(node, ast.match_case) and node.guard is not None:
        counts["match-guard"] += 1
    elif isinstance(node, ast.Assert):
        counts["assert"] += 1
print(
    json.dumps(
        {
            "all_executable_predicates_including_self_test_asserts": sum(
                counts.values()
            ),
            "by_kind": counts,
        },
        sort_keys=True,
    )
)
