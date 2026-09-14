"""Run the unchanged continuous-scene fixtures with the frozen Lanczos basis."""
from pathlib import Path
import importlib.util
import hashlib
import json

HERE=Path(__file__).resolve().parent
FIXTURE=HERE/"joint-cfa-controls.py"
FIXTURE_SHA="f7f68ab015a01f731585860ec3a875bc30d007185c2fb45743b12210a3842682"
AUTHOR_SHA="3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4"

def main():
    assert AUTHOR_SHA!="AWAITING_AUTHOR_FREEZE", "author has not yet frozen source"
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==FIXTURE_SHA
    spec=importlib.util.spec_from_file_location("same_joint_truth_controls",FIXTURE)
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    fixture.AUTHOR=HERE/"joint-cfa-lanczos.py"
    fixture.EXPECTED=AUTHOR_SHA
    fixture.OUT=HERE/"joint-cfa-lanczos-controls-1"
    fixture.SUPPORT_LOW=2
    fixture.SUPPORT_HIGH=fixture.SIZE-3
    fixture.main()
    # Different reconstruction basis must not alter truth or either comparator.
    before=json.loads((HERE/"joint-cfa-controls-3/result.json").read_text())
    after=json.loads((fixture.OUT/"result.json").read_text())
    for left,right in zip(before["nominal_cases"],after["nominal_cases"],strict=True):
        for key in ("kind","frequency","orientation","anchor_mhc","nine_mhc_mean"):
            assert left[key]==right[key],key
    flat_before=json.loads((HERE/"joint-cfa-controls-3/flat-first.json").read_text())
    flat_after=json.loads((fixture.OUT/"flat-first.json").read_text())
    for left,right in zip(flat_before,flat_after,strict=True):
        for key in ("layout","noise_seed","anchor_mhc","nine_mhc_mean"):
            assert left[key]==right[key],key
    fixture.save(fixture.OUT/"same-fixtures-verified.json",dict(
        fixture_sha256=FIXTURE_SHA,solver_sha256=AUTHOR_SHA,
        anchor_and_mean_nominal_and_noise_metrics_exact=True,
        change="Only reconstruction basis and its required support bounds; identical scenes, phases, noise draws, bars and comparators."))

if __name__=="__main__":main()
