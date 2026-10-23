"""Small CPU-only adversarial controls for the V4 cache guards; no photo access."""

from pathlib import Path
import importlib.util
import json
import tempfile

import torch


path = Path(__file__).with_name("train-v4.py")
spec = importlib.util.spec_from_file_location("runner_guards", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def rejects(callable_, name):
    try:
        callable_()
    except ValueError:
        return name
    raise AssertionError(f"negative control passed: {name}")


passed = []
base = {"group_id": "a", "split": "train", "path": "C:/photos/A.jpg", "source_id": "first"}
independent = {"group_id": "b", "split": "validation", "path": "C:/photos/B.jpg", "source_id": "second"}
runner.validate_split_identities([base, independent])
for field, value in (("group_id", "a"), ("source_id", "first"), ("path", "c:\\PHOTOS\\a.JPG"),
                     ("paired_display_render", "c:/photos/a.jpg")):
    conflicting = {**independent, field: value}
    passed.append(rejects(lambda: runner.validate_split_identities([base, conflicting]), "cross_split_" + field))
for field in ("source_sha256", "decoded_sha256"):
    passed.append(rejects(lambda: runner.validate_split_identities([{**base, field: "abc"}, {**independent, field: "ABC"}]),
                          "cross_split_" + field))
runner.validate_label_values({"pgtm": torch.ones(1), "rgbt_0": torch.tensor([1.000000119]), "exposure": torch.ones(1)})
for key, value, name in (("pgtm", 0.0, "zero_gain"), ("pgtm", 200000.0, "unsupported_gain"),
                         ("rgbt_0", 1.01, "material_color_overshoot"), ("exposure", float("nan"), "nonfinite_exposure")):
    passed.append(rejects(lambda: runner.validate_label_values({key: torch.tensor([value])}), name))
with tempfile.TemporaryDirectory(dir=path.parent) as name:
    cache = Path(name)
    for filename in ("manifest.json", *(f"{key}.npy" for key in ("inputs", *runner.V4.OUTPUT_NAMES))):
        (cache / filename).write_bytes(b"receipt-only-fixture")
    before = runner.cache_file_receipt(cache)
    (cache / "rgbt_0.npy").write_bytes(b"replaced-cache-content-longer")
    assert before != runner.cache_file_receipt(cache), "cache replacement escaped metadata receipt"
    passed.append("cache_file_replacement")
print(json.dumps({"passed": passed, "photos_or_teacher_labels_read": False, "device": "cpu"}, indent=2))
