"""Prospective independent arithmetic controls for one nominated sidecar proposal."""
import math
import numpy as np

INDICES = (0, 26, 52, 78, 104)
CENTRE = (414.0, 1630.0)
ORIGIN = (112, 1304)
SHAPE = (456, 640)
PHASES = ((0, 0), (1, 0), (0, 1), (1, 1))


def phi(x, y):
    radius = np.hypot(x-CENTRE[0], y-CENTRE[1])
    return np.where(radius < 32.0, np.cos(radius * (math.pi/64.0))**2, 0.0)


def inverse_native(x, y, transform):
    a, b = transform
    rx, ry = x-3516.0-2.0*b.real, y-2344.0-2.0*b.imag
    det = a.real*a.real+a.imag*a.imag
    return (3516.0+(a.real*rx+a.imag*ry)/det,
            2344.0+(-a.imag*rx+a.real*ry)/det)


def planted(amplitudes, transforms=None, background="affine"):
    x, y = np.meshgrid(ORIGIN[0]+np.arange(SHAPE[1]), ORIGIN[1]+np.arange(SHAPE[0]))
    signals = {}
    for index in INDICES:
        if background == "constant":
            base = np.full(SHAPE, 3500.0)
        elif background == "quadratic":
            base = 3500.0+0.04*(x-414.0)**2+0.025*(y-1630.0)**2
        else:
            base = 3500.0+1.7*(x-414.0)-0.9*(y-1630.0)
        # Distinct CFA illumination and changing capture level, not a private noise plant.
        for n, (dx, dy) in enumerate(PHASES):
            base[dy::2, dx::2] += 137.0*n
        base *= 0.90 + 0.20*index/104.0
        # The nominated sidecar has one attenuation per quad, evaluated at its centre.
        px, py = (inverse_native(x, y, transforms[index]) if transforms is not None else
                  (2*(x//2)+0.5, 2*(y//2)+0.5))
        signals[index] = (base*(1.0-amplitudes[index]*phi(px, py))).astype(np.float32)
    return signals



def scene_placebo(signals, transforms, amplitude=0.08):
    """Copy saved clean context190native rows into the target; plant a moving feature."""
    assert set(signals) == set(transforms) == set(INDICES) and amplitude == 0.08
    x, y = np.meshgrid(ORIGIN[0]+np.arange(SHAPE[1]), ORIGIN[1]+np.arange(SHAPE[0]))
    result = {}
    for index in INDICES:
        source = np.asarray(signals[index])
        assert source.shape == SHAPE and source.dtype == np.float32
        moved = source.copy()
        # Entire target annulus y1550..1710 lies in this overwritten portion.
        # The even190 shift preserves every original CFA phase. No wrap or new pixels.
        moved[190:] = source[:-190]
        px, py = inverse_native(x, y, transforms[index])
        attenuation = (1.0-amplitude*phi(px, py)).astype(np.float32)
        assert float(attenuation.min()) < 0.925, "each shifted plant must exist"
        result[index] = (moved*attenuation).astype(np.float32)
    return result


def literal_apply(raw, black_by_phase, gain, white):
    result = raw.copy()
    for y in range(raw.shape[0]):
        for x in range(raw.shape[1]):
            g = np.float32(gain[y//2, x//2])
            if g == np.float32(1):
                continue  # Unlisted quads do not lift even below-black storage values.
            value = int(raw[y, x])
            if np.float32(value) >= np.float32(white):
                continue
            black = np.float32(black_by_phase[2*(y % 2)+(x % 2)])
            signal = np.maximum(np.float32(value)-black, np.float32(0))
            restored = np.float32(np.float32(signal*g)+black)
            if restored >= np.float32(white):
                continue  # Current production skips instead of clamping new clipping.
            rounded = math.floor(float(restored)+0.5)
            result[y, x] = min(65535, max(0, rounded))
    return result


def run(proposer, transforms):
    assert tuple(sorted(transforms)) == INDICES
    x = np.array([414.0, 430.0, 414.0, 446.0, 414.0, 450.0])
    y = np.array([1630.0, 1630.0, 1614.0, 1630.0, 1662.0, 1700.0])
    literal = np.array([1.0, 0.5, 0.5, 0.0, 0.0, 0.0])
    assert np.max(np.abs(proposer.profile(x, y)-literal)) <= 2e-7
    qx, qy = np.meshgrid(112.5+2*np.arange(320), 1304.5+2*np.arange(228))
    expected_gain = (1.0/(1.0-0.08*phi(qx, qy))).astype(np.float32)
    gain = proposer.gain_map(0.08)
    assert gain.shape == (228, 320) and gain.dtype == np.float32
    assert np.max(np.abs(gain-expected_gain)) <= 2e-7, "quad centre/native origin/profile convention"
    outside = np.repeat(np.repeat(gain == np.float32(1), 2, axis=0), 2, axis=1)
    assert np.count_nonzero(~outside) > 0 and np.count_nonzero(outside) > 0
    assert float(gain.max()) <= 1.25

    # Literal scalar controls cover exact black handling, ties, pre/new clipping and unity.
    values = np.array([0, 511, 512, 513, 514, 1024, 15359, 15360, 65535], dtype=np.uint16)
    raw = values[np.arange(8*18).reshape(8,18) % values.size]
    gsmall = np.array([1.0, 1.01, 1.25, 1.125, 1.0001, 1.05, 1.0, 1.125, 1.25]*4, dtype=np.float32).reshape(4,9)
    scalar_cases = 0
    for black in ([512.0]*4, [512.25, 513.5, 511.75, 514.0]):
        frozen = raw.copy()
        expected = literal_apply(raw, black, gsmall, 15360.0)
        actual = proposer.apply_map(raw, black, gsmall, white=15360.0)
        assert actual.dtype == np.uint16 and np.array_equal(actual, expected)
        assert np.array_equal(raw, frozen), "proposal preview must not mutate source"
        assert np.count_nonzero(actual != raw) > 0, "integer correction must be live"
        scalar_cases += raw.size
    # Deliberate half tie: 513-512=1, times1.5 would exceed allowed gain; use4*1.125=4.5.
    tie_raw = np.full((2,2), 516, dtype=np.uint16)
    tie = proposer.apply_map(tie_raw, [512.0]*4, np.array([[1.125]], dtype=np.float32))
    assert np.array_equal(tie, np.full((2,2), 517, dtype=np.uint16)), "round-half-away-from-zero"
    fullraw = (np.arange(SHAPE[0]*SHAPE[1]).reshape(SHAPE) % 15380).astype(np.uint16)
    before = fullraw.copy()
    corrected = proposer.apply_map(fullraw, [512.0]*4, gain)
    assert np.array_equal(fullraw, before)
    assert np.array_equal(corrected[outside], before[outside]), "outside nominated quads must be bit-identical"
    assert np.count_nonzero(corrected[~outside] != before[~outside]) > 0
    assert np.array_equal(corrected[before >= 15360], before[before >= 15360])

    positive_signals = planted(dict.fromkeys(INDICES, 0.08))
    positive = proposer.fit_shared(positive_signals)
    assert positive["proceed"] is True, positive["reasons"]
    assert abs(positive["amplitude"]-0.08) <= 2e-5, "analytic independent attenuation amplitude"
    rows = positive["per_frame_phase"]
    assert len(rows) == 5*4*2 and {v["model"] for v in rows} == {"affine", "quadratic"}
    forced = proposer.evaluate(positive_signals, 0.16)
    assert forced["proceed"] is False and forced["reasons"], "overcorrection must be refused"
    assert any(v["index"] in (26,52,78) and v["core_after"] > 0.01 for v in forced["per_frame_phase"]), "bright-core falsifier is live"

    refusals = []
    for label, signals in (("constant-clean", planted(dict.fromkeys(INDICES,0.0), background="constant")),
                           ("affine-clean", planted(dict.fromkeys(INDICES,0.0))),
                           ("quadratic-clean", planted(dict.fromkeys(INDICES,0.0), background="quadratic")),
                           ("scene-following", planted(dict.fromkeys(INDICES,0.08), transforms=transforms))):
        result = proposer.fit_shared(signals)
        assert result["proceed"] is False and result["reasons"], (label, result)
        refusals.append(dict(input=label, amplitude=result["amplitude"], reasons=result["reasons"]))
    quadratic = proposer.evaluate(planted(dict.fromkeys(INDICES,0.0), background="quadratic"), 0.08)
    assert quadratic["proceed"] is False
    assert any(v["index"] in (26,52,78) and v["model"] == "quadratic" and v["rmse_after"] > v["rmse_before"]
               for v in quadratic["per_frame_phase"]), "quadratic nuisance stress must reject brightening clean shading"
    # Isolate the EACH-phase .015 depth floor from presence and heldout fidelity.
    shallow_phase = planted(dict.fromkeys(INDICES,0.08))
    shallow_red = planted(dict.fromkeys(INDICES,0.018))
    for index in INDICES:
        shallow_phase[index][0::2,0::2] = shallow_red[index][0::2,0::2]
    shallow = proposer.evaluate(shallow_phase, 0.01)
    red = [v for v in shallow["per_frame_phase"] if v["phase"] == "R"]
    assert len(red) == 10 and all(0.010 <= v["core_deficit"] < 0.015 for v in red)
    assert all(v["rmse_after"] <= v["rmse_before"] and abs(v["mean_after"]) <= abs(v["mean_before"])
               and v["core_after"] <= .010 for v in shallow["per_frame_phase"] if v["index"] in (26,52,78))
    assert shallow["proceed"] is False and shallow["reasons"], "pooled phase depth concealed shallow R"
    altered = dict.fromkeys(INDICES,0.08)
    altered[52] = 0.0
    held_change = proposer.fit_shared(planted(altered))
    assert abs(held_change["amplitude"]-positive["amplitude"]) <= 1e-8, "heldout leaked into training amplitude"
    assert held_change["proceed"] is False and held_change["reasons"], "a wrong heldout must not pass"
    return dict(status="PASS", scalar_cases=scalar_cases, positive_amplitude=positive["amplitude"],
                positive_rows=len(rows), forced_overcorrection_reasons=forced["reasons"],
                shallow_phase_reasons=shallow["reasons"],
                refusals=refusals, altered_heldout_reasons=held_change["reasons"],
                outside_unchanged_values=int(np.count_nonzero(outside)),
                scope="arithmetic/source-proposal controls; no physical dust identification or noise calibration")
