"""Independent descriptor/refusal controls; root alone executes the fixed program."""
import math
import numpy as np

RUNGS = (0, 8, 64, 128, 144, 200, 298)
REFERENCE = 144
R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)
MAX_PLANE_ERROR = 2.0


def gauge_controls(truth):
    """truth is exactly seven stored, UNGAUGED ln-scale values."""
    assert set(truth) == set(RUNGS)
    literal_scales = (1.0, .99743, .97653, .9545, .94686, .9216, .85714)
    for j, scale in zip(RUNGS, literal_scales, strict=True):
        assert math.isfinite(truth[j]) and abs(truth[j]-math.log(scale)) < 1e-12
    expected = {j: truth[j]-truth[REFERENCE] for j in RUNGS}
    chord = {j: truth[0]+j/298.0*(truth[298]-truth[0]) for j in RUNGS}
    chord = {j: chord[j]-chord[REFERENCE] for j in RUNGS}
    reverse = {j: -expected[j] for j in RUNGS}
    errors = lambda track: {j: R_PLANE*abs(track[j]-expected[j]) for j in RUNGS}
    zero, wrong_sign, wrong_chord = errors(expected), errors(reverse), errors(chord)
    assert max(zero.values()) == 0.0  # Arithmetic gauge identity, not independent evidence.
    assert max(wrong_sign.values()) > MAX_PLANE_ERROR
    assert max(wrong_chord.values()) > MAX_PLANE_ERROR
    assert wrong_chord[200] > MAX_PLANE_ERROR, "curved interior must reject its straight chord"
    return dict(rungs=list(RUNGS), reference=REFERENCE, radius_plane_px=R_PLANE,
                tolerance_plane_px=MAX_PLANE_ERROR, true_log_scales=expected,
                sign_destroyer_errors_plane_px=wrong_sign,
                chord_destroyer_errors_plane_px=wrong_chord,
                scope="Literal stored curved metadata and gauge falsifiers; identity is arithmetic")


def run(op):
    nr, nt, step, search = 257, 64, 0.0125, 12
    u = ((np.arange(nr, dtype=np.float64)-(nr-1)/2)*step)[:, None]
    theta = (2*math.pi*np.arange(nt, dtype=np.float64)/nt)[None, :]
    a = np.cos(2*theta)
    b = np.sin(4*theta)
    c = np.cos(6*theta)

    def field(x):
        return (np.cos(5*x+.3)*a + .4*np.sin(9*x-.2)*b
                + .2*np.exp(-((x-.4)/.5)**2)*c).astype(np.float32)

    reference = field(u)
    records = []
    for shift in (-3, 0, 4):
        planted = shift*step
        moving = field(u+planted)
        got = op.estimate_scale(reference, moving, step, search)
        assert got["accepted"], ("informative direct-shift control refused", shift, got)
        assert abs(got["log_scale"]-planted) <= 2e-4, ("direct scale sign/magnitude", shift, got)
        if shift:
            assert abs(-got["log_scale"]-planted) > 0.05, "sign destroyer is inactive"
        records.append(dict(case="literal-shift", planted_log_scale=planted, result=got))

    # Angular centering must remove an independently added radial nuisance, while
    # leaving a large, radius-dependent angular field. Ordinary retains nuisance.
    nuisance = (.7*u*u + .3*np.exp(2*u)).astype(np.float32)
    base = reference + np.float32(2.0)
    moved = base + nuisance
    q0, q1 = op.descriptor(base, True), op.descriptor(moved, True)
    assert q0.dtype == q1.dtype == np.float32
    assert np.max(np.abs(q1-q0)) < 3e-6
    assert np.max(np.abs(op.descriptor(moved, False)-op.descriptor(base, False))) > 1.0
    assert np.mean(q0*q0, dtype=np.float64) > .01
    nuisance_fit = op.estimate_scale(q0, q1, step, search)
    assert nuisance_fit["accepted"] and abs(nuisance_fit["log_scale"]) <= 2e-4
    records.append(dict(case="radial-nuisance-removed", result=nuisance_fit))

    # |F|=R(r)A(theta): a strongly structured Q independent of radius has no scale.
    angular = (.3*a + .2*b).astype(np.float32)
    sep0 = (-.7*u*u + angular).astype(np.float32)
    sep1 = (-.7*(u+.06)**2 - .4*np.exp(2*u) + angular).astype(np.float32)
    qs0, qs1 = op.descriptor(sep0, True), op.descriptor(sep1, True)
    assert np.mean(qs0*qs0, dtype=np.float64) > .01, "separable null must carry angular structure"
    separated = op.estimate_scale(qs0, qs1, step, search)
    assert not separated["accepted"] and separated["reason"] == "scale-information", separated
    records.append(dict(case="separable-nonzero-angular-null", result=separated))

    # Stronger null: nonzero radial derivative, but shifting is only an NCC gain.
    exponential = (np.exp(2*u)*(.2*a+.1*b)).astype(np.float32)
    gain_shifted = (np.exp(2*(u+.06))*(.2*a+.1*b)).astype(np.float32)
    assert np.mean(np.diff(exponential, axis=0)**2, dtype=np.float64) > 1e-6
    gain_null = op.estimate_scale(exponential, gain_shifted, step, search)
    assert not gain_null["accepted"] and gain_null["reason"] == "scale-information", gain_null
    records.append(dict(case="nonzero-derivative-gain-only-null", result=gain_null))

    radial = np.broadcast_to(-.7*u*u, (nr, nt)).copy().astype(np.float32)
    radial_fit = op.estimate_scale(op.descriptor(radial, True), op.descriptor(radial, True), step, search)
    assert not radial_fit["accepted"] and radial_fit["reason"] in ("zero-energy", "weak-energy"), radial_fit
    weak = op.estimate_scale(reference*np.float32(.001), reference*np.float32(.001), step, search)
    assert not weak["accepted"] and weak["reason"] == "weak-energy", weak
    records.extend([dict(case="exact-radial-null", result=radial_fit), dict(case="weak-contrast-null", result=weak)])

    # Several equal local peaks have high information but do not identify a shift.
    phase = 2*math.pi*np.arange(nr, dtype=np.float64)[:, None]/12
    periodic = (np.cos(phase)*a + .4*np.sin(phase)*b).astype(np.float32)
    aliased = op.estimate_scale(periodic, periodic, step, 25)
    assert not aliased["accepted"] and aliased["reason"] == "ambiguous-peak", aliased
    assert aliased["info_reference"]["information"] >= 1e-3
    records.append(dict(case="periodic-alias-null", result=aliased))
    invalid = reference.copy(); invalid[128, 0] = np.nan
    refused = op.estimate_scale(reference, invalid, step, search)
    assert not refused["accepted"] and refused["reason"] == "nonfinite"
    records.append(dict(case="nonfinite-refusal", result=refused))
    return dict(status="INDEPENDENT_DESCRIPTOR_CONTROLS_PASS", cases=records,
                literal_log_scale_tolerance=2e-4,
                scope="Small literal descriptor controls; full-image informative/radial/model-violation cases remain required")
