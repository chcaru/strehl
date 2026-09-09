"""Independent coordinate arithmetic controls; no decoder, aligner fit or image metric."""
import numpy as np

INDICES = (0, 26, 52, 78, 104)
ORIGIN = (112, 1304)
SHAPE = (456, 640)
STROKE = (274, 1572, 320, 120)
CLEAN = (274, 1382, 320, 120)
PHASES = ((0, 0), (1, 0), (0, 1), (1, 1))
PHASE_DN = (0.0, 37.0, 91.0, 173.0)


def coordinates(rect, phase=(0, 0), step=2):
    x, y, w, h = rect
    xx, yy = np.meshgrid(x + phase[0] + step * np.arange(w // step),
                         y + phase[1] + step * np.arange(h // step))
    return xx.astype(np.float64), yy.astype(np.float64)


def map_native(x, y, transform, inverse=False):
    # Independent real 2x2 expansion: centre is native (3516,2344), b is QUAD.
    a, b = transform
    if inverse:
        rx, ry = x - 3516.0 - 2.0 * b.real, y - 2344.0 - 2.0 * b.imag
        det = a.real * a.real + a.imag * a.imag
        return (3516.0 + (a.real * rx + a.imag * ry) / det,
                2344.0 + (-a.imag * rx + a.real * ry) / det)
    rx, ry = x - 3516.0, y - 2344.0
    return (3516.0 + a.real * rx - a.imag * ry + 2.0 * b.real,
            2344.0 + a.imag * rx + a.real * ry + 2.0 * b.imag)


def feature(x, y):
    # Finite horizontal endpoints and unequal off-axis lobes defeat row-only evidence.
    return (2000.0 - 320.0 * np.exp(-0.5 * (((x-398.0)/24.0)**2 + ((y-1626.0)/8.0)**2))
            - 150.0 * np.exp(-0.5 * (((x-478.0)/10.0)**2 + ((y-1646.0)/12.0)**2)))


def mosaic(field, transform=None):
    x, y = coordinates((*ORIGIN, SHAPE[1], SHAPE[0]), step=1)
    if transform is not None:
        x, y = map_native(x, y, transform, inverse=True)
    out = field(x, y).astype(np.float32)
    for phase, dn in zip(PHASES, PHASE_DN):
        out[phase[1]::2, phase[0]::2] += np.float32(dn)
    return out


def residuals(views):
    ref = views[2].astype(np.float64)
    reference_energy = float(np.mean((ref-ref.mean())**2))
    # Engineering arithmetic guard, NOT a camera/noise estimate or a real-data verdict.
    two_axes = all(float(np.mean(np.diff(ref, axis=axis)**2)) >= 0.01 for axis in (0, 1))
    if not two_axes or reference_energy < 1.0:
        return None
    return [float(np.mean((v.astype(np.float64)-ref)**2) / reference_energy)
            for i, v in enumerate(views) if i != 2]


def preference(sensor, scene):
    sr, cr = residuals(sensor), residuals(scene)
    if sr is None or cr is None:
        return "ambiguous"
    if all(c <= 0.1*s and s > 0.0025 for s, c in zip(sr, cr)):
        return "scene"
    if all(s <= 0.1*c and c > 0.0025 for s, c in zip(sr, cr)):
        return "sensor"
    return "ambiguous"


def run(sampler, transforms):
    assert tuple(sorted(transforms)) == INDICES, "exactly the five admitted placements"
    assert all(abs(transforms[i][0]) > 0.5 for i in INDICES)
    ref_a, ref_b = transforms[52]
    assert abs(ref_a-1) < 1e-12 and abs(ref_b) < 1e-12, "reference-52 gauge"
    affine = mosaic(lambda x, y: 100.0 + 0.125*x + 0.5*y)
    literal_count, affine_max, cropped_max = 0, 0.0, 0.0
    # Same physical patch in a differently based storage view catches ROI-origin loss.
    trimmed, shifted_origin = affine[16:-16, 16:-16], (128, 1320)
    for rect in (STROKE, CLEAN):
        for phase, dn in zip(PHASES, PHASE_DN):
            x, y = coordinates(rect, phase)
            sensor = sampler.sample(affine, ORIGIN, rect, phase, transforms[52], gauge="sensor")
            exact = (100.0 + 0.125*x + 0.5*y + dn).astype(np.float32)
            assert sensor.shape == (rect[3]//2, rect[2]//2) and sensor.dtype == np.float32
            assert np.array_equal(sensor, exact), "sensor crop/phase must be literal exact"
            for index in INDICES:
                t = transforms[index]
                for inverse in (False, True):
                    sx, sy = map_native(x, y, t, inverse=inverse)
                    expected = (100.0 + 0.125*sx + 0.5*sy + dn).astype(np.float32)
                    direction = "inverse" if inverse else "forward"
                    got = sampler.sample(affine, ORIGIN, rect, phase, t, direction=direction)
                    other = sampler.sample(trimmed, shifted_origin, rect, phase, t, direction=direction)
                    error = float(np.max(np.abs(got-expected)))
                    origin_error = float(np.max(np.abs(got-other)))
                    assert error <= 0.003, ("affine coordinate/phase error", index, phase, direction, error)
                    assert origin_error <= 0.003, ("storage origin changed physical sample", origin_error)
                    affine_max, cropped_max = max(affine_max, error), max(cropped_max, origin_error)
                    literal_count += 1
    # A deliberately omitted delivered crop origin cannot accidentally satisfy this oracle.
    x, y = coordinates(STROKE)
    actual_literal = sampler.sample(affine, ORIGIN, STROKE, (0, 0), transforms[52], gauge="sensor")
    origin_destroyer = float(np.max(np.abs(actual_literal - (100+.125*(x-124)+.5*(y-82)))))
    assert origin_destroyer == 56.5

    outcomes = []
    for planted_gauge in ("scene", "sensor"):
        patches = [mosaic(feature, transforms[i] if planted_gauge == "scene" else None) for i in INDICES]
        for phase in ((1, 0), (0, 1)):
            views = {}
            for label, gauge, direction in (("sensor", "sensor", "forward"),
                                             ("scene", "scene", "forward"),
                                             ("inverse", "scene", "inverse")):
                views[label] = [sampler.sample(patch, ORIGIN, STROKE, phase, transforms[i],
                                               gauge=gauge, direction=direction)
                                for i, patch in zip(INDICES, patches)]
            assert preference(views["sensor"], views["scene"]) == planted_gauge, (planted_gauge, phase)
            good = residuals(views[planted_gauge])
            identity = residuals(views["sensor"])
            wrong = residuals(views["inverse"])
            assert good is not None and max(good) <= 0.0025, ("correct gauge must recover", good)
            assert wrong is not None and all(w > 0.0025 and g <= 0.1*w for g, w in zip(good, wrong)), ("wrong direction not live", wrong)
            if planted_gauge == "scene":
                assert all(v > 0.0025 for v in identity), "identity must lose every nonreference frame"
            outcomes.append(dict(plant=planted_gauge, phase=list(phase),
                                 preferred=preference(views["sensor"], views["scene"]),
                                 sensor_residual=identity, scene_residual=residuals(views["scene"]),
                                 inverse_residual=wrong))
    nulls = []
    for label, field in (("uniform", lambda x, y: np.full(x.shape, 2000.0)),
                         ("infinite-horizontal", lambda x, y: 2000.0-250.0*np.exp(-0.5*((y-1630.0)/14.0)**2))):
        patch = mosaic(field)
        for phase in ((1, 0), (0, 1)):
            sv = [sampler.sample(patch, ORIGIN, STROKE, phase, transforms[i], gauge="sensor") for i in INDICES]
            cv = [sampler.sample(patch, ORIGIN, STROKE, phase, transforms[i]) for i in INDICES]
            assert preference(sv, cv) == "ambiguous", ("null offered registration evidence", label, phase)
            if label == "uniform":
                assert all(float(np.max(np.abs(v-sv[0]))) <= 0.003 for v in sv+cv), "uniform must stay uniform within f32 roundoff"
            else:
                assert float(np.ptp(sv[0])) > 100.0, "horizontal refusal must contain a live dark feature"
            nulls.append(dict(field=label, phase=list(phase), decision="ambiguous"))
    return dict(status="PASS", scope="arithmetic controls only; no real alignment truth or calibration",
                indices=list(INDICES), literal_comparisons=literal_count,
                maximum_affine_error_dn=affine_max, maximum_storage_origin_error_dn=cropped_max,
                omitted_output_origin_destroyer_dn=origin_destroyer, plants=outcomes, nulls=nulls,
                rule="both-axis finite structure; every nonreference rung correct residual <=0.0025 and <=one tenth competing residual; nulls refuse")
