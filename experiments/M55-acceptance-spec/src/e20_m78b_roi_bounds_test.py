"""M78b property tests for B6's registration-time geometry guard."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec_v1 as S


EXPECTED = [
    (750, 458, 512, 512),
    (2252, 458, 512, 512),
    (1501, 916, 512, 512),
    (1501, 1466, 512, 512),
]
LEGACY = [
    (458, 750, 512, 512),
    (1374, 750, 512, 512),
    (916, 1501, 512, 512),
    (916, 2402, 512, 512),
]


def raises_with(fn, required):
    try:
        fn()
    except ValueError as exc:
        text = str(exc)
        return all(fragment in text for fragment in required), text
    return False, "did not raise ValueError"


def main():
    checks = []
    actual = S.roi_rule()
    checks.append(("normative fractions produce repaired registry", actual == EXPECTED, str(actual)))

    validated = S.validate_roi_registry(actual, (4688, 7028), stack="synthetic-header")
    checks.append(("four repaired ROIs pass real geometry", len(validated) == 4, str(validated)))

    ok, detail = raises_with(
        lambda: S.validate_roi_registry(LEGACY, (4688, 7028), stack="plant"),
        ("roi_index=3", "y1=2946", "required_raw_extent=(5892, 2920)",
         "visible_raw_shape=(4688, 7028)"),
    )
    checks.append(("legacy fourth ROI is rejected with exact bounds", ok, detail))

    ok, detail = raises_with(
        lambda: S.validate_roi_registry(actual, (7028, 4688), stack="transposed"),
        ("quad_shape=(3514, 2344)", "registered_quad_shape=(2344, 3514)"),
    )
    checks.append(("transposed real geometry is rejected", ok, detail))

    ok, detail = raises_with(
        lambda: S.validate_roi_registry(actual[:3], (4688, 7028), stack="short"),
        ("registered_rois=3", "required_rois=4"),
    )
    checks.append(("incomplete registry is rejected", ok, detail))

    ok, detail = raises_with(
        lambda: S.validate_roi_registry(actual, (4687, 7028), stack="odd"),
        ("is not even in both dimensions",),
    )
    checks.append(("odd raw geometry is rejected", ok, detail))

    bad = 0
    print("M78b B6 ROI BOUNDS PROPERTY TEST")
    print("MEASURED: no corpus data read")
    for name, passed, detail in checks:
        print(f"   {'PASS' if passed else 'FAIL'}: {name}")
        if not passed:
            print(f"      {detail}")
        bad += not passed
    print(f"MEASURED: assertions={len(checks)} passed={len(checks) - bad} failed={bad}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
