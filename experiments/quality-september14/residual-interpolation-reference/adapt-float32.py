"""Explicit, reproducible RI-only dtype/headroom adaptation; no algorithm run."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source"
OUTPUT = HERE / "float32-ri"
FILES = ["demosaic_RI.py", "mosaic_bayer.py", "RIgreen_interpolation.py",
         "RIGuidefilterResidual.py", "RIguidedfilter3gf.py", "RIred_interpolation.py",
         "RIblue_interpolation.py", "RIHaResidual.py", "filtertools.py"]


def main():
    OUTPUT.mkdir(exist_ok=False)
    changes = []
    bindings = {}
    for name in FILES:
        source = (SOURCE / name).read_text(encoding="utf-8")
        starts = [0]
        for line in source.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        edits = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "np":
                continue
            begin = starts[node.lineno-1] + node.col_offset
            end = starts[node.end_lineno-1] + node.end_col_offset
            if node.func.attr in ("array", "zeros", "ones"):
                assert not any(k.arg == "dtype" for k in node.keywords)
                edits.append((end-1, end-1, ", dtype=np.float32"))
            if node.func.attr == "clip":
                assert len(node.args) == 3 and ast.literal_eval(node.args[1]) == 0
                assert ast.literal_eval(node.args[2]) == 255
                edits.append((begin, end, ast.get_source_segment(source, node.args[0])))
        adapted = source
        for begin, end, replacement in sorted(edits, reverse=True):
            adapted = adapted[:begin] + replacement + adapted[end:]
        if name == "filtertools.py":
            adapted = adapted.replace("cv2.getGaussianKernel(sz, sigma)",
                "cv2.getGaussianKernel(sz, sigma, ktype=cv2.CV_32F)")
        if name == "RIguidedfilter3gf.py":
            adapted = adapted.replace("th = 0.00001 * 255 * 255",
                "th = np.float32(0.00001) * np.float32(255) * np.float32(255)")
        adapted = "# Adapted locally: explicit f32 constructors; published clips disabled for RAW headroom.\n" + adapted
        (OUTPUT / name).write_text(adapted, encoding="utf-8", newline="\n")
        changes.extend(difflib.unified_diff(source.splitlines(True), adapted.splitlines(True),
            fromfile="source/"+name, tofile="float32-ri/"+name))
        bindings[name] = {"original_sha256": hashlib.sha256((SOURCE/name).read_bytes()).hexdigest(),
            "adapted_sha256": hashlib.sha256((OUTPUT/name).read_bytes()).hexdigest()}
    (OUTPUT / "LICENSE.txt").write_bytes((SOURCE / "LICENSE.txt").read_bytes())
    (HERE / "float32-adaptation.diff").write_text("".join(changes), encoding="utf-8", newline="\n")
    (HERE / "float32-adaptation.json").write_text(json.dumps(bindings, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
