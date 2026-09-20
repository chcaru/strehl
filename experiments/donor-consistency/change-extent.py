"""Describe actual changed RGB16 support; these counts are not quality scores."""
from pathlib import Path
import hashlib
import json
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
RUN = HERE / "full-1"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    completion = json.loads((RUN / "completion.json").read_text())
    receipt = json.loads((RUN / "photo-comparison-1/coordinate-receipt.json").read_text())
    baseline_path = RUN / "output/baseline.tiff"
    assert digest(baseline_path) == completion["baseline"]["sha256"]
    baseline = tifffile.memmap(baseline_path)
    result = {"scope": "RGB16 change extent, not quality or noise measurements", "arms": {}}
    for arm in ("candidate", "late"):
        path = RUN / f"output/{arm}.tiff"
        assert digest(path) == completion[arm]["sha256"]
        image = tifffile.memmap(path)
        delta = np.max(np.abs(image.astype(np.int32) - baseline.astype(np.int32)), axis=2)
        support = {}
        for threshold in (0, 1, 16, 257):
            y, x = np.nonzero(delta > threshold)
            support[str(threshold)] = {"pixels": len(y), "fraction": len(y) / delta.size,
                "bbox_xywh": ([int(x.min()), int(y.min()), int(x.max()-x.min()+1),
                                int(y.max()-y.min()+1)] if len(y) else None)}
        regions = {}
        for r in receipt["regions"]:
            x, y, w, h = r["pair_xywh"]
            patch = delta[y:y+h, x:x+w]
            regions[r["name"]] = {"changed_pixels": int(np.count_nonzero(patch)),
                "max_channel_change_dn": int(patch.max())}
        result["arms"][arm] = {"sha256": digest(path), "strict_channel_threshold_dn": support,
                              "frozen_windows": regions}
    result["script_sha256"] = digest(Path(__file__))
    with (RUN / "change-extent.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
