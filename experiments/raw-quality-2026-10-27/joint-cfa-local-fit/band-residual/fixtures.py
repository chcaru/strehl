"""Independent continuous scenes. This module does not import the fitted operator.

Root executes the driver. Originals are generated once as u16 sensor measurements;
truth is an analytic unit-sensel integral, never A(X) or a fitted Haar-band target.
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageCms

PANEL = 128
APRON = 8
CENTER = np.array([64., 64.])
SHOT = np.array([.15, .13, .17, .21], dtype=np.float32).astype(np.float64)
READ_E = (np.sqrt([9., 8., 11., 13.])/SHOT).astype(np.float32)
# Use the exact f32 parameterization consumed by the Rust NoiseModel. The
# intended read variances9/8/11/13 differ only by this declared f32 rounding.
READ = np.square(SHOT.astype(np.float32)*READ_E, dtype=np.float32).astype(np.float64)
BLACK = 512
WHITE = 15360
WB = [2., 1., 1.5]
CHANNEL = np.array([0, 1, 1, 2])
CASES = (
    "flat-neutral", "flat-colour", "fine-far", "coarse-only",
    "alias-repeated", "alias-diverse", "independent-colour",
    "cofocused-colour", "flat-green-colour", "visibility-glint",
)
EXTRA_FIT_MODES = {"fine-far": ("no-focus", "full-value"),
                   "alias-repeated": ("no-focus", "full-value")}
YY, XX = np.mgrid[:PANEL, :PANEL]
XY = np.stack((XX, YY), -1).astype(np.int32)
PHASE = ((YY & 1)*2+(XX & 1)).astype(np.uint8)
ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value.resolve())
    raise TypeError(type(value).__name__)


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False,
                           default=json_default)+"\n")


def file_ref(path):
    p = Path(path).resolve()
    return dict(path=str(p), bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def array_ref(path, value):
    p = Path(path)
    a = np.ascontiguousarray(value)
    with p.open("xb") as f:
        np.save(f, a, allow_pickle=False)
    return dict(**file_ref(p), shape=list(a.shape), dtype=str(a.dtype))


def preview(path, rgb):
    """One fixed diagnostic display, no per-image tone or camera matrix fit."""
    a = np.asarray(rgb, dtype=np.float32)
    if not np.isfinite(a).all():
        raise ValueError("nonfinite preview input")
    v = np.clip(a*np.float32(3/(WHITE-BLACK)), 0, 1)
    s = np.where(v <= .0031308, 12.92*v, 1.055*np.power(v, 1/2.4)-.055)
    Image.fromarray(np.rint(s*255).astype(np.uint8)).save(path, icc_profile=ICC)
    return dict(**file_ref(path), width=a.shape[1], height=a.shape[0],
                display="clip(3*camera_DN/14848,0,1), sRGB OETF, round255",
                icc_sha256=hashlib.sha256(ICC).hexdigest(), resized=False)


def geometry(case, index):
    if case in ("fine-far", "coarse-only", "alias-repeated", "visibility-glint"):
        return np.eye(2), np.zeros(2)
    if case == "alias-diverse":
        return np.eye(2), np.array([(0., 0.), (.25, .5), (.5, -.5),
            (.75, .25), (-.25, -.25), (-.5, .75), (-.75, -.75)][index])
    scale = [1., 1.005, .996, 1.009, .993, 1.004, .998][index]
    angle = [0., .004, -.006, .003, -.005, .006, -.003][index]
    shift = [(0., 0.), (.37, -.41), (-.28, .23), (.43, .31),
             (-.39, -.27), (.19, -.36), (-.33, .42)][index]
    c, s = math.cos(angle), math.sin(angle)
    return scale*np.array([[c, -s], [s, c]]), np.array(shift)


def mapped(xy, matrix, shift):
    return (np.asarray(xy, np.float64)-CENTER)@matrix.T+CENTER+shift


def nodes(matrix, shift, *, wrong_footprint=False):
    n, w = np.polynomial.legendre.leggauss(3)
    dx, dy = np.meshgrid(n*.5, n*.5)
    sub = np.stack((dx.ravel(), dy.ravel()), -1)
    footprint = sub if wrong_footprint else sub@matrix.T
    q = mapped(XY, matrix, shift)[..., None, :]+footprint+APRON
    return q.astype(np.float64), (np.outer(w, w).ravel()/4).astype(np.float32)


def terms(case):
    # Tuples: name, frequency(native cycles/pixel), phase, RGB radiance amplitude, depth.
    if case.startswith("flat-") and case != "flat-green-colour":
        return []
    if case in ("fine-far", "coarse-only"):
        far = ("far-coarse", (.025, 0.), .31, (400., 400., 400.), "far")
        return ([far] if case == "coarse-only" else [
            ("near-fine", (.22, 0.), .73, (400., 400., 400.), "near"), far])
    if case.startswith("alias-"):
        return [("red-020", (.20, 0.), 0., (400/np.sinc(.20), 0., 0.), "alias"),
                ("red-030", (.30, 0.), 0., (-400/np.sinc(.30), 0., 0.), "alias")]
    if case in ("independent-colour", "cofocused-colour", "flat-green-colour"):
        far_owner = "near" if case == "cofocused-colour" else "far"
        rows = [("red-detail", (.18, .025), .43, (450., 0., 0.), "near"),
                ("blue-detail", (-.035, .20), .81, (0., 0., 450.), far_owner)]
        if case != "flat-green-colour":
            rows.append(("weak-green", (-.07, .12), .37, (0., 8., 0.), "near"))
        return rows
    return []


def dc(case):
    return np.array([2048., 2048., 2048.] if case == "flat-neutral"
                    else [1800., 2100., 2400.])


def attenuation(case, index, frequency, owner):
    if index is None:
        return 1.
    if case in ("alias-repeated", "alias-diverse"):
        # Identical blur competition in both arms; only sampling phases differ.
        sigma = [0., 0., 0., .5, 1., 2., 3.][index]
    elif case in ("fine-far", "coarse-only"):
        near = [0., .75, 1.5, 3., 6., 12., 20.]
        sigma = (near if owner == "near" else near[::-1])[index]
    else:
        sigma = ([0., .5, 1., 2., 3., 4., 5.] if owner == "near"
                 else [4., 3., 2., 1., .5, 0., 1.5])[index]
    return math.exp(-2*math.pi**2*sigma*sigma*np.dot(frequency, frequency))


def field(case, xy, *, index=None, matrix=None, shift=None, integrate=True,
          component=None, wrong_footprint=False):
    matrix = np.eye(2) if matrix is None else matrix
    shift = np.zeros(2) if shift is None else shift
    q = mapped(xy, matrix, shift)
    result = np.broadcast_to(dc(case) if component is None else np.zeros(3),
                             (*q.shape[:-1], 3)).copy()
    for name, frequency, phase, amplitude, owner in terms(case):
        if component is not None and name != component:
            continue
        f = np.asarray(frequency)
        ff = f if wrong_footprint else matrix.T@f
        area = np.sinc(ff[0])*np.sinc(ff[1]) if integrate else 1.
        wave = np.cos(2*math.pi*(q@f)+phase)
        result += wave[..., None]*np.array(amplitude)*area*attenuation(case, index, f, owner)
    return result.astype(np.float32)


def rect_area(xy, rect):
    """Exact overlap of an axis-aligned reference unit sensel and finite rectangle."""
    x, y = np.asarray(xy, np.float64)[..., 0], np.asarray(xy, np.float64)[..., 1]
    x0, y0, x1, y1 = rect
    return np.maximum(0., np.minimum(x+.5, x1)-np.maximum(x-.5, x0))*np.maximum(
        0., np.minimum(y+.5, y1)-np.maximum(y-.5, y0))


def visibility(xy, *, index=None, pupil_count=128, clipped=False):
    """Independent first-hit scene; exact pixel area, deterministic shared disk rays.

    Rectangular finite ends are deliberate. This is not a capsule/PSF fit or H truth.
    All source maps for this scene are identity, so its physical sensor squares remain
    axis-aligned and the sensor-area integral below is exact for every pupil ray.
    """
    xy = np.asarray(xy, np.float64)
    background = np.array([2200., 2100., 2000.])
    near_colour = np.array([4600., 4200., 3600.])
    far_colour = np.array([700., 900., 1000.])
    glint_colour = np.array([24000., 23000., 22000.] if clipped else [11000., 10000., 9000.])
    near = np.array([46.3, 20.4, 47.2, 103.2])
    far = np.array([20.2, 67.4, 110.1, 69.2])
    glint = np.array([46.3, 37.1, 47.2, 40.1])
    count = 1 if index is None else pupil_count
    focus = None if index is None else [0., .7, 1.4, 2., 2.8, 3.5, 4.][index]
    result = np.zeros((*xy.shape[:-1], 3), np.float64)
    for k in range(count):
        if focus is None:
            shift_near = shift_far = np.zeros(2)
        else:
            radius = math.sqrt((k+.5)/count)
            angle = k*math.pi*(3-math.sqrt(5))
            pupil = radius*np.array([math.cos(angle), math.sin(angle)])
            shift_near, shift_far = focus*pupil, (focus-4.)*pupil
        n = near+np.tile(shift_near, 2)
        f = far+np.tile(shift_far, 2)
        g = glint+np.tile(shift_near, 2)
        intersect = [max(n[0], f[0]), max(n[1], f[1]),
                     min(n[2], f[2]), min(n[3], f[3])]
        an, af, overlap, ag = (rect_area(xy, r) for r in (n, f, intersect, g))
        av = np.maximum(af-overlap, 0.)
        result += (background+(near_colour-background)*an[..., None]
                   +(far_colour-background)*av[..., None]
                   +(glint_colour-near_colour)*ag[..., None])
    return (result/count).astype(np.float32)


def truth(case):
    return visibility(XY) if case == "visibility-glint" else field(case, XY)


def components(case):
    if case == "visibility-glint":
        near = rect_area(XY, [46.3, 20.4, 47.2, 103.2])
        far = rect_area(XY, [20.2, 67.4, 110.1, 69.2])
        overlap = rect_area(XY, [46.3, 67.4, 47.2, 69.2])
        glint = rect_area(XY, [46.3, 37.1, 47.2, 40.1])
        return {"near-visible": (near[..., None]*np.array([2400., 2100., 1600.])).astype(np.float32),
                "far-visible": ((far-overlap)[..., None]*np.array([-1500., -1200., -1000.])).astype(np.float32),
                "compact-glint": (glint[..., None]*np.array([6400., 5800., 5400.])).astype(np.float32)}
    return {row[0]: field(case, XY, component=row[0]) for row in terms(case)}


def component_specification(case):
    if case == "visibility-glint":
        return [dict(name=name, amplitude_dn=amplitude) for name, amplitude in (
            ("near-visible", [2400., 2100., 1600.]),
            ("far-visible", [-1500., -1200., -1000.]),
            ("compact-glint", [6400., 5800., 5400.]))]
    return [dict(name=row[0], amplitude_dn=list(row[3])) for row in terms(case)]


def make_case(case, ordinal):
    rng = np.random.default_rng(2026102700+ordinal)
    originals, rows = [], []
    for i in range(7):
        matrix, shift = geometry(case, i)
        rgb = (visibility(XY, index=i) if case == "visibility-glint" else
               field(case, XY, index=i, matrix=matrix, shift=shift))
        sensor = np.take_along_axis(rgb, CHANNEL[PHASE][..., None], axis=-1)[..., 0]
        variance = SHOT[PHASE]*np.maximum(sensor, 0.)+READ[PHASE]
        noise = rng.normal(size=sensor.shape)*np.sqrt(variance)
        codes = np.clip(np.rint(sensor+BLACK+noise), 0, WHITE).astype("<u2")
        originals.append(codes)
        rows.append(dict(source_id=i, source_to_reference=[float(matrix[0, 0]),
            float(matrix[1, 0]), float(shift[0]), float(shift[1])],
            noiseless_sensor_min=float(sensor.min()), noiseless_sensor_max=float(sensor.max()),
            clipped_codes=int(np.count_nonzero(codes >= WHITE))))
    return originals, rows


def export_case(root, case, ordinal):
    out = Path(root)/case
    out.mkdir()
    originals, rows = make_case(case, ordinal)
    for codes, row in zip(originals, rows):
        p = out/f"source-{row['source_id']:02d}.u16le"
        with p.open("xb") as f:
            f.write(codes.tobytes())
        row.update(file_ref(p))
    ref = truth(case)
    metadata = dict(id=case, width=PANEL, height=PANEL, black=BLACK, white=WHITE,
        wb_rgb=WB, iso=100, noise=dict(gain_dn_per_e4=SHOT.tolist(),
        read_noise_e4=READ_E.astype(np.float64).tolist(), phase_order=["R", "G1", "G2", "B"]),
        source_to_reference_center=CENTER.tolist(), sources=rows,
        seed=2026102700+ordinal, truth=array_ref(out/"truth-rgb-dn.npy", ref),
        truth_display=preview(out/"truth-complete.png", ref),
        templates={name: array_ref(out/(name+"-truth.npy"), value)
                   for name, value in components(case).items()},
        component_specification=component_specification(case),
        acquisition_noise="independent Gaussian using the supplied original phase variance; round to u16 afterward",
        quantization="rounding is disclosed; no extra per-stage noise model or added1/12 profile term",
        output_truth="reference unit-square RGB integrals, independent of A/H",
        alias_blur_sigmas=([0., 0., 0., .5, 1., 2., 3.] if case.startswith("alias-") else None),
        extra_fit_modes=list(EXTRA_FIT_MODES.get(case, ())))
    save_json(out/"fixture.json", metadata)
    return metadata


def export_all(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    with (root/"display-srgb.icc").open("xb") as f:
        f.write(ICC)
    cases = [export_case(root, case, i) for i, case in enumerate(CASES)]
    # The clipped companion is a declared input-refusal control, not another fit.
    sensor_rgb = visibility(XY, index=0, clipped=True)
    sensor = np.take_along_axis(sensor_rgb, CHANNEL[PHASE][..., None], axis=-1)[..., 0]
    codes = np.clip(np.rint(sensor+BLACK), 0, WHITE).astype("<u2")
    p = root/"visibility-clipped.u16le"
    with p.open("xb") as f:
        f.write(codes.tobytes())
    # Actual Rust bridge deliberately denies unknown fields; keep its strict
    # input separate from the richer independent truth/lineage receipt.
    baseline_cases = []
    for case in cases:
        item = {k: case[k] for k in ("id", "width", "height", "black", "white",
            "wb_rgb", "iso", "noise", "source_to_reference_center")}
        item["sources"] = [{k: s[k] for k in ("source_id", "path", "sha256",
                            "bytes", "source_to_reference")} for s in case["sources"]]
        baseline_cases.append(item)
    save_json(root/"baseline-manifest.json", dict(schema=1, cases=baseline_cases))
    manifest = dict(schema=1, cases=cases, cases_order=list(CASES),
        baseline_manifest=file_ref(root/"baseline-manifest.json"),
        display_icc=file_ref(root/"display-srgb.icc"),
        candidate_fits=10, auxiliary_fits=4, total_full_screen_fits=14,
        clipped_refusal=dict(**file_ref(p), source_id=0,
                            clipped_codes=int(np.count_nonzero(codes >= WHITE))),
        score_xywh=[16, 16, 96, 96], candidate_output_wh=[128, 128], latent_wh=[144, 144],
        baseline_crop_native_xywh=[16, 16, 96, 96], admission=False,
        photographic_admission=False)
    save_json(root/"fixture-manifest.json", manifest)
    return manifest


def load_case(manifest, case):
    row = next(r for r in manifest["cases"] if r["id"] == case)
    arrays = []
    for source in row["sources"]:
        ref = file_ref(source["path"])
        if any(ref[k] != source[k] for k in ("sha256", "bytes")):
            raise ValueError("fixture identity changed")
        arrays.append(np.fromfile(source["path"], dtype="<u2").reshape(PANEL, PANEL).copy())
    return row, arrays
