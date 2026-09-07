"""Independent M193c grid semantics and pixels. Source-only until root release.

No producer imports, RAW access or RNG. The parent owns release/index/launch
authority and final persistence; these functions never mint an authority file.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import sys
import time
import weakref
from fractions import Fraction

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

ROOT = Path(__file__).resolve().parents[2]
PARSER = ROOT / "experiments/m194g-larger-pupil/independent-rgb-tiff.py"
PARSER_SHA = "d01a74aefcfa15b2146256b54ea51876715ab203b7de123b3cff2b0af4a1b19c"
WIDTH, HEIGHT, BLACK, RANGE = 320, 240, 512, 14848
RUNGS = (0, 40, 80, 112, 144, 184, 224, 264, 298)
SCALES = (.9999999999999998, .9856299999999998, .9726649999999999,
          .9642499999999998, .9468599999999999, .9285849999999999,
          .9090699999999999, .8795899999999999, .85714)
IMAG = (0., 1/128, 0., -1/256, 0., 1/256, 0., -1/128, 0.)
TRANSLATIONS = ((-2., 1.), (-1.5, 1.), (-1., .5), (-.5, .25), (0., 0.),
                (.5, -.25), (1., -.5), (1.5, -1.), (2., -1.5))
CASES = ("identity-nine", "curved-nine-off", "curved-nine-count", "curved-nine-placebo",
         "curved-nine-scale", "original-one-correct", "original-one-swapped",
         "original-one-restored", "original-one-inverse", "constant-nine-null")
PAIRS = tuple((x, y) for y in (36, 68, 100, 132) for x in (40, 68, 96, 124, 152, 180, 208, 236))
ENV = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
           STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
TEST = "merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case"
SIM_KEYS = ("a_re", "a_im", "b_re", "b_im")


class Refusal(ValueError):
    def __init__(self, boundary, message):
        super().__init__(f"{boundary}: {message}")
        self.boundary = boundary


def need(condition, boundary, message):
    if not condition:
        raise Refusal(boundary, message)


def keys(value, expected, boundary):
    need(type(value) is dict and set(value) == set(expected), boundary, "closed keys")


def integer(value, boundary, lo=0, hi=None):
    need(type(value) is int and value >= lo and (hi is None or value <= hi), boundary, "integer range")
    return value


def number(value, boundary):
    need(type(value) in (int, float) and math.isfinite(value), boundary, "finite real")
    return float(value)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def valid_hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def strict_json(raw):
    def pairs(values):
        out = {}
        for k, v in values:
            need(k not in out, "json", "duplicate key")
            out[k] = v
        return out
    def bad(value):
        raise Refusal("json", f"nonfinite {value}")
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    def walk(v):
        if type(v) is float:
            need(math.isfinite(v), "json", "overflow literal")
        elif type(v) is dict:
            for item in v.values():
                walk(item)
        elif type(v) is list:
            for item in v:
                walk(item)
    walk(value)
    return value


def same(actual, expected, boundary, atol=0.):
    """Strict bool/string/integer/shape; only explicitly real expectations allow tolerance."""
    if type(expected) is dict:
        keys(actual, expected, boundary)
        for k, v in expected.items():
            same(actual[k], v, boundary, atol)
    elif type(expected) in (tuple, list):
        need(type(actual) is list and len(actual) == len(expected), boundary, "list extent")
        for a, b in zip(actual, expected):
            same(a, b, boundary, atol)
    elif type(expected) is float:
        need(abs(number(actual, boundary) - expected) <= atol, boundary, "real value")
    else:
        need(type(actual) is type(expected) and actual == expected, boundary, "typed literal")


class Budget:
    """Local stop budget; parent separately charges the entire private job tree."""
    def __init__(self, *, cpu=120., wall=240., arrays=32 << 20, read_bytes=512 << 20,
                 start_cpu=None, start_wall=None):
        self.start_cpu = time.process_time() if start_cpu is None else start_cpu
        self.start_wall = time.monotonic() if start_wall is None else start_wall
        self.cpu_limit, self.wall_limit = cpu, wall
        self.array_limit, self.read_limit = arrays, read_bytes
        self.owners, self.peak, self.read_bytes = {}, 0, 0
        self.check()

    def _prune(self):
        self.owners = {k: v for k, v in self.owners.items() if v[0]() is not None}

    def check(self):
        self._prune()
        need(time.process_time() - self.start_cpu <= self.cpu_limit, "resource", "CPU ceiling")
        need(time.monotonic() - self.start_wall <= self.wall_limit, "resource", "wall ceiling")
        need(self.read_bytes <= self.read_limit, "resource", "cumulative input bytes")
        need(sum(v[1] for v in self.owners.values()) <= self.array_limit, "resource", "live array bytes")

    def check_allocation(self, shape, dtype):
        import numpy as np
        self.check()
        n = math.prod(shape) * np.dtype(dtype).itemsize
        need(n + sum(v[1] for v in self.owners.values()) <= self.array_limit,
             "resource", "prospective array bytes")

    def watch(self, array, label):
        import numpy as np
        self._prune()
        root = array
        while isinstance(root.base, np.ndarray):
            root = root.base
        old = self.owners.get(id(root))
        if old is None or old[0]() is not root:
            self.owners[id(root)] = (weakref.ref(root), root.nbytes, label)
        self.peak = max(self.peak, sum(v[1] for v in self.owners.values()))
        self.check()

    def receipt(self):
        self.check()
        return dict(cpu_seconds=time.process_time()-self.start_cpu,
                    wall_seconds=time.monotonic()-self.start_wall,
                    read_bytes=self.read_bytes, peak_array_bytes=self.peak,
                    limits=dict(cpu=self.cpu_limit, wall=self.wall_limit,
                                arrays=self.array_limit, read_bytes=self.read_limit))


class Reads:
    def __init__(self, budget):
        self.budget, self.used = budget, {}

    def file(self, ref, cap=4 << 20):
        keys(ref, ("path", "sha256", "bytes"), "reference")
        path = reference_path(ref)
        integer(ref["bytes"], "reference", 1, cap)
        need(valid_hash(ref["sha256"]), "reference", "hash")
        self.budget.check()
        with path.open("rb") as stream:
            raw = stream.read(cap + 1)
        self.budget.read_bytes += len(raw)
        need(len(raw) == ref["bytes"] and len(raw) <= cap and sha(raw) == ref["sha256"],
             "reference", "payload binding")
        ledger_key = str(path).casefold()
        previous = self.used.get(ledger_key)
        need(previous is None or (previous["sha256"], previous["bytes"]) ==
             (ref["sha256"], ref["bytes"]), "reference", "conflicting prior binding")
        self.used[ledger_key] = dict(ref)
        self.budget.check()
        return raw

    def json(self, ref):
        return strict_json(self.file(ref))

    def recheck(self):
        for ref in list(self.used.values()):
            self.file(ref, max(4 << 20, ref["bytes"]))


def reference_path(ref):
    value = ref.get("path") if type(ref) is dict else None
    need(type(value) is str and value, "reference", "path string")
    path = Path(value)
    if not path.is_absolute():
        need(".." not in path.parts and "." not in path.parts, "reference", "repository relative path")
        path = ROOT / path
    resolved = path.resolve()
    need(resolved.is_relative_to(ROOT), "reference", "repository containment")
    return resolved


def same_ref(a, b):
    keys(a, ("path", "sha256", "bytes"), "association")
    keys(b, ("path", "sha256", "bytes"), "association")
    need(reference_path(a) == reference_path(b), "association", "resolved file identity")
    same(a["sha256"], b["sha256"], "association")
    same(a["bytes"], b["bytes"], "association")


def load_parser(budget):
    budget.check()
    with PARSER.open("rb") as stream:
        raw = stream.read((1 << 20) + 1)
    budget.read_bytes += len(raw)
    need(len(raw) <= 1 << 20 and sha(raw) == PARSER_SHA, "source", "pinned TIFF parser")
    spec = importlib.util.spec_from_loader("m193c_frozen_rgb_parser", loader=None, origin=str(PARSER))
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(PARSER)
    sys.modules[spec.name] = mod
    exec(compile(raw, str(PARSER), "exec"), mod.__dict__)
    budget.check()
    return mod


def track(ordinal):
    integer(ordinal, "population", 0, 9)
    return [(1., 0., 0., 0.) if ordinal == 0 else
            (SCALES[i]/SCALES[4], IMAG[i], *TRANSLATIONS[i]) for i in range(9)]


def sim_record(t):
    return dict(zip(SIM_KEYS, t))


def sim(value):
    keys(value, SIM_KEYS, "map")
    return tuple(number(value[k], "map") for k in SIM_KEYS)


def apply(t, xy):
    a, b, tx, ty = t
    x, y = xy[0]-160., xy[1]-120.
    return (160. + a*x-b*y+2*tx, 120. + b*x+a*y+2*ty)


def inverse(t):
    a, b, tx, ty = t
    d = a*a+b*b
    need(math.isfinite(d) and d > 0., "map", "nonsingular inverse")
    return (a/d, -b/d, -(a*tx+b*ty)/d, (b*tx-a*ty)/d)


def cover(ts):
    """Intersect affine corner inequalities, independently of product bisection."""
    upper = 1.
    for a, b, tx, ty in ts:
        for x, y in ((0., 0.), (159., 0.), (0., 119.), (159., 119.)):
            dx, dy = x-80., y-60.
            for base, slope, lo, hi in ((80.+tx, a*dx-b*dy, 3., 156.),
                                       (60.+ty, b*dx+a*dy, 3., 116.)):
                need(lo <= base <= hi, "cover", "centre unsupported")
                if slope > 0:
                    upper = min(upper, (hi-base)/slope)
                elif slope < 0:
                    upper = min(upper, (lo-base)/slope)
    need(0. < upper < 1. and math.isfinite(upper), "cover", "nontrivial bounded cover")
    rect = []
    for n in (160, 120):
        lo = .5*n*(1.-upper)
        begin, end = math.ceil(lo), math.floor(lo+upper*(n-1.))
        rect.append((begin, end-begin+1))
    return upper, (rect[0][0], rect[1][0], rect[0][1], rect[1][1])


def level_sizes(w, h):
    out = [[w, h]]
    for _ in range(3):
        w, h = (w+1)//2, (h+1)//2
        out.append([w, h])
    return out


def predicted(ordinal):
    ts = track(ordinal)
    k, crop = cover(ts)
    post = [(a*k, b*k, tx, ty) for a, b, tx, ty in ts] if ordinal == 4 else list(ts)
    fault = list(post)
    if ordinal == 6:
        fault[1], fault[7] = fault[7], fault[1]
    elif ordinal == 8:
        fault[1] = inverse(fault[1])
    rect = (0, 0, 160, 120) if ordinal == 4 else crop
    selected = [1] if 5 <= ordinal <= 8 else list(range(9))
    return dict(track=ts, post=post, fault=fault, k=k, rect=rect, selected=selected)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def validate_plan(plan, ordinal, context):
    keys(context, ("build", "compiled_inputs", "precision_witness_sha256"), "context")
    keys(context["build"], ("path", "sha256", "bytes", "software"), "context")
    need(valid_hash(context["build"]["sha256"]) and valid_hash(context["precision_witness_sha256"]),
         "context", "externally bound source/executable hashes")
    integer(context["build"]["bytes"], "context", 1)
    keys(context["compiled_inputs"], ("private_protocol_sha256", "private_adapter_sha256"), "context")
    need(all(valid_hash(v) for v in context["compiled_inputs"].values()), "context", "compiled source pins")
    keys(plan, ("schema", "status", "case", "track", "selected", "geometry", "fields",
                "sensor", "config", "environment", "build", "compiled_inputs"), "plan")
    same(plan["schema"], "m193c-private-grid-plan-v1", "plan")
    same(plan["status"], "PLAN_ONLY", "plan")
    p = predicted(ordinal)
    mode = "count" if ordinal == 2 else "placebo" if ordinal == 3 else "off"
    fault = "swap-original-1-7" if ordinal == 6 else "invert-selected-pull" if ordinal == 8 else "none"
    same(plan["case"], dict(ordinal=ordinal, id=CASES[ordinal], fault=fault, observer=mode,
                            restored_from=6 if ordinal == 7 else None), "case")
    expected_track = [dict(original_index=i, retained_rung=RUNGS[i], retained_scale=SCALES[i],
                           source_generation_pull=sim_record(p["track"][i]),
                           correct_post_cover_pull=sim_record(p["post"][i]),
                           actual_post_fault_pull=sim_record(p["fault"][i])) for i in range(9)]
    same(plan["track"], expected_track, "map", 2e-14)
    selected = [dict(local_index=j, original_index=i, probe_seed_index=j,
                     path=f"M193C-NO-SUCH-RAW-{i}.ARW", actual_quad_pull=sim_record(p["fault"][i]))
                for j, i in enumerate(p["selected"])]
    same(plan["selected"], selected, "association", 2e-14)
    x, y, w, h = p["rect"]
    geometry = dict(full_native=[320, 240], full_quad=[160, 120], native_centre=[160., 120.],
                    canonical_private_index=4, local_reference=0 if len(selected) == 1 else 4,
                    crop_quad=dict(x=x, y=y, width=w, height=h), output_native=[2*w, 2*h],
                    cover_k=p["k"], cover_mode="Scale" if ordinal == 4 else "Crop",
                    output_to_canonical="C+k*(z-C)" if ordinal == 4 else "z+2*crop_origin",
                    level_sizes=level_sizes(w, h))
    same(plan["geometry"], geometry, "geometry", 2e-14)
    fields = [[1800, 0, 0], [2300, 0, 0], [2900, 0, 0]] if ordinal == 9 else [[1100, 40, 0], [1700, 0, 40], [2100, 12, 8]]
    same(plan["fields"], dict(kind="constant" if ordinal == 9 else "affine", rgb_affine=fields), "fields")
    same(plan["sensor"], dict(black=512, white=15360, range_dn=14848, cfa="RGGB", stride=320,
         buffer_height=240, active=dict(x=0, y=0, width=320, height=240), frame_wb_f32=[1., 1., 1.],
         writer_wb_f32=[1., 1., 1.], gain_dn_per_e=[.25]*4, read_noise_e=[4.]*4, iso=160,
         provenance="Fallback: injected synthetic coefficients; no calibration claim",
         source_rounding="positive half-up, no clipping permitted", tiff_u16_to_dn=14848./65535.), "sensor")
    same(plan["config"], dict(backend="Pyramid", bands=3, gate=2., exponent=2.,
         sharpen_per_octave=f32(1.4), select="SoftPower", admission="HardFloor", base="Mean",
         fallback="Mean", hull="InputRange", mean_coarse=0, significance_scale=0., resampler="CatmullRom",
         fullres_gather=True, demosaic="MHC", space="CameraLinear", exposure=0, photometric="Off",
         confidence=False, defect=False, ca=False, restoration=False, gate_floor=True), "config")
    same(plan["environment"], ENV, "environment")
    keys(plan["build"], ("path", "sha256", "bytes", "software"), "build")
    # Windows current_exe may retain its verbatim prefix. Compare actual resolved
    # file identity, then exact hash/extent/software; no basename/path guessing.
    need(reference_path(plan["build"]) == reference_path(context["build"]), "build", "executable path")
    for key in ("sha256", "bytes", "software"):
        same(plan["build"][key], context["build"][key], "build")
    same(plan["compiled_inputs"], context["compiled_inputs"], "source")
    return p


def field(channel, xy, constant=False):
    if constant:
        return (1800., 2300., 2900.)[channel]
    x, y = xy
    return (1100.+40.*x, 1700.+40.*y, 2100.+12.*x+8.*y)[channel]


def channel_at(x, y):
    return (0, 1, 1, 2)[(y % 2)*2+x % 2]


class Sources:
    def __init__(self, budget):
        self.budget, self.cache, self.checked = budget, {}, set()
        self.maximum_source_evaluation_error = 0.

    def get(self, t, constant):
        import numpy as np
        key = (tuple(t), constant)
        if key in self.cache:
            self.budget.check()
            return self.cache[key]
        self.budget.check_allocation((240, 320), "<u2")
        raw = bytearray(320*240*2)
        lo, hi = math.inf, -math.inf
        a, b, tx, ty = t
        d = a*a+b*b
        for y in range(240):
            self.budget.check()
            for x in range(320):
                vx, vy = x-160.-2.*tx, y-120.-2.*ty
                q = (160.+(a*vx+b*vy)/d, 120.+(-b*vx+a*vy)/d)
                v = field(channel_at(x, y), q, constant)
                need(math.isfinite(v) and 0. < v < 14848., "source-range", "whole-active unrounded value")
                code = math.floor(512.+v+.5)
                need(512 < code < 15360, "source-range", "whole-active rounded value")
                struct.pack_into("<H", raw, 2*(y*320+x), code)
                lo, hi = min(lo, v), max(hi, v)
        array = np.frombuffer(raw, dtype="<u2").reshape(240, 320)
        self.budget.watch(array, "independent source CFA")
        result = (array, dict(sha256_u16_le=sha(raw), bytes=len(raw), samples=320*240,
                              minimum_unrounded_dn=lo, maximum_unrounded_dn=hi))
        self.cache[key] = result
        return result

    def check_stencil_evaluation(self, t, xy, constant):
        """Exact binary-rational field check on every consumed source stencil site."""
        ix, iy = math.floor(xy[0]), math.floor(xy[1])
        a, b, tx, ty = t
        aa, bb, txx, tyy = map(Fraction, t)
        den = aa*aa+bb*bb
        for y in range(iy-3, iy+5):
            for x in range(ix-3, ix+5):
                key = (tuple(t), constant, x, y)
                if key in self.checked:
                    continue
                self.budget.check()
                vx, vy = x-160.-2.*tx, y-120.-2.*ty
                q = (160.+(a*vx+b*vy)/(a*a+b*b), 120.+(-b*vx+a*vy)/(a*a+b*b))
                fv = field(channel_at(x,y), q, constant)
                xx, yy = Fraction(x-160)-2*txx, Fraction(y-120)-2*tyy
                ex, ey = 160+(aa*xx+bb*yy)/den, 120+(-bb*xx+aa*yy)/den
                c = channel_at(x,y)
                exact = Fraction((1800,2300,2900)[c]) if constant else (
                    1100+40*ex, 1700+40*ey, 2100+12*ex+8*ey)[c]
                error = float(abs(Fraction(fv)-exact))
                need(error <= 1e-8, "precision", "binary64 source evaluation allowance")
                self.maximum_source_evaluation_error = max(self.maximum_source_evaluation_error, error)
                self.checked.add(key)


# Independent dyadic stencil tables; no producer or Python image package call.
G = ((0,0,4),(-1,0,2),(1,0,2),(0,-1,2),(0,1,2),(-2,0,-1),(2,0,-1),(0,-2,-1),(0,2,-1))
H = ((0,0,5),(-1,0,4),(1,0,4),(-2,0,-1),(2,0,-1),(-1,-1,-1),(1,-1,-1),(-1,1,-1),(1,1,-1),(0,-2,.5),(0,2,.5))
V = tuple((dy, dx, w) for dx, dy, w in H)
X = ((0,0,6),(-1,-1,2),(1,-1,2),(-1,1,2),(1,1,2),(-2,0,-1.5),(2,0,-1.5),(0,-2,-1.5),(0,2,-1.5))


def mhc(array, x, y, channel):
    need(2 <= x < 318 and 2 <= y < 238, "support", "MHC reflection forbidden")
    known = channel_at(x, y)
    if channel == known:
        return float(int(array[y, x])-BLACK)
    if known in (0, 2):
        taps = G if channel == 1 else X
    else:
        horizontal = (y % 2 == 0 and channel == 0) or (y % 2 == 1 and channel == 2)
        taps = H if horizontal else V
    terms = [w*(int(array[y+dy, x+dx])-BLACK) for dx, dy, w in taps]
    exact = math.fsum(terms)/8.
    # Independent operation-by-operation f32 companion; all dyadic sums exact here.
    acc = 0.
    for term in terms:
        acc = f32(acc+f32(term))
    need(f32(acc*.125) == exact, "precision", "dyadic MHC exactness")
    return exact


def weights64(t):
    return (t*(-.5+t*(1.-.5*t)), 1.+t*t*(-2.5+1.5*t),
            t*(.5+t*(2.-1.5*t)), .5*t*t*(t-1.))


def weights32(t):
    t = f32(t)
    t2, t3 = f32(t*t), f32(f32(t*t)*t)
    return (f32(f32(f32(-.5*t3)+t2)-f32(.5*t)),
            f32(f32(f32(1.5*t3)-f32(2.5*t2))+1.),
            f32(f32(f32(-1.5*t3)+f32(2.*t2))+f32(.5*t)),
            f32(f32(.5*t3)-f32(.5*t2)))


def gather_oracle(array, xy, channel, private_fault=None):
    need(private_fault in (None, "omit-outer", "opposite-channel"), "control", "kernel fault id")
    x, y = xy
    need(all(math.isfinite(v) for v in xy), "support", "finite sample coordinates")
    ix, iy = math.floor(x), math.floor(y)
    need(ix-1 >= 2 and ix+2 < 318 and iy-1 >= 2 and iy+2 < 238,
         "support", "complete Catmull plus MHC interior")
    wx, wy = weights64(x-ix), weights64(y-iy)
    fx, fy = weights32(x-ix), weights32(y-iy)
    if private_fault == "omit-outer":
        wx, fx = (0., *wx[1:]), (0., *fx[1:])
    if private_fault == "opposite-channel":
        channel = 2 if channel == 0 else 0
    values = [[mhc(array, ix+dx-1, iy+dy-1, channel) for dx in range(4)] for dy in range(4)]
    exact = math.fsum(values[j][i]*wx[i]*wy[j] for j in range(4) for i in range(4))
    acc = 0.
    for row, yweight in zip(values, fy):
        r = 0.
        for v, xweight in zip(row, fx):
            r = f32(r+f32(v*xweight))
        acc = f32(acc+f32(r*yweight))
    added = f32(acc+512.)
    need(abs(added-(exact+512.)) <= .125, "precision", "f32 gather/black reserve")
    return dict(f64=exact, modeled_f32=acc, modeled_bits=bits(acc), black_added_f32=added,
                black_added_bits=bits(added), rounded_u16=math.floor(added+.5),
                error_dn=added-(exact+512.), support=[ix-3, iy-3, ix+4, iy+4])


def canonical(p, ordinal, xy, fault=None):
    x, y = xy
    cx, cy, _, _ = p["rect"]
    if fault == "zero-crop":
        cx, cy = 0, 0
    elif fault == "exchange-crop":
        cx, cy = cy, cx
    if ordinal == 4:
        k = 1. if fault == "unit-scale" else p["k"]
        q = (160.+k*(x-160.), 120.+k*(y-120.))
    else:
        factor = 1. if fault == "quad-as-native" else 2.
        q = (x+factor*cx, y+factor*cy)
    if fault == "transpose-output":
        q = (q[1], q[0])
    return q


def sample_expected(p, ordinal, original, xy):
    cx, cy, _, _ = p["rect"]
    # Inputs are final native sites, with even full-quad Crop origin restored.
    return apply(p["fault"][original], (xy[0]+2*cx, xy[1]+2*cy))


def fault_expected(p, ordinal, xy):
    return apply(inverse(p["track"][1]), sample_expected(p, ordinal, 1, xy))


def score_pixels(pixels, p, ordinal, private_fault=None):
    import numpy as np
    expected_shape = (p["rect"][3]*2, p["rect"][2]*2, 3)
    need(pixels.shape == expected_shape and pixels.dtype == np.dtype("<u2"), "pixels", "native shape/type")
    rows = []
    coefficients = [[1100,40,0],[1700,0,40]]
    if private_fault == "rank-one":
        coefficients = [[1100,40,20],[1700,80,40]]
    if ordinal != 9:
        coordinate_rank(coefficients)
    if ordinal == 9:
        try:
            coordinate_rank([[1800,0,0],[2300,0,0]])
        except Refusal as exc:
            need(exc.boundary == "rank", "constant", "specific rank-zero refusal")
        else:
            raise Refusal("constant", "constant coordinate inverse falsely admitted")
        for pair, (x, y) in enumerate(PAIRS):
            rgb = [int(v) for v in pixels[y, x]]
            dn = [v*RANGE/65535. for v in rgb]
            need(max(abs(v-e) for v, e in zip(dn, (1800., 2300., 2900.))) <= .125,
                 "constant", "value preservation")
            rows.append(dict(pair_index=pair, output_xy=[x, y], rgb_u16=rgb, rgb_dn=dn))
        return dict(kind="constant_rank_zero", coordinate_inversion="REFUSED_RANK_ZERO", rows=rows)
    norms, correct_norms, errors = [], [], []
    for pair, (x, y) in enumerate(PAIRS):
        rgb = [int(v) for v in pixels[y, x]]
        gc = int(pixels[y, x+1, 1])
        need(all(0 < c < 65535 for c in rgb+[gc]), "pixels", "sampled positive unclipped codes")
        dn, gdn = [v*RANGE/65535. for v in rgb], gc*RANGE/65535.
        ux = canonical(p, ordinal, (x, y), private_fault)
        uy = canonical(p, ordinal, (x+1, y), private_fault)
        correct = ((dn[0]-1100.)/40.-ux[0], (gdn-1700.)/40.-uy[1])
        bad = ordinal in (6, 8)
        ex = fault_expected(p, ordinal, (x, y)) if bad else ux
        ey = fault_expected(p, ordinal, (x+1, y)) if bad else uy
        if private_fault == "stale-association":
            ex, ey = ux, uy
        if private_fault == "wrong-inverse":
            ex, ey = apply(p["track"][1], ex), apply(p["track"][1], ey)
        error = (dn[0]-field(0, ex), gdn-field(1, ey))
        norm = math.hypot(error[0]/40., error[1]/40.)
        need(max(map(abs, error)) <= 2.75 and norm <= .1, "coordinate", "fixed paired-site bar")
        norms.append(norm)
        correct_norms.append(math.hypot(*correct))
        errors.extend(error)
        rows.append(dict(pair_index=pair, r_xy=[x,y], g1_xy=[x+1,y], rgb_u16=rgb, g1_u16=gc,
                         rgb_dn=dn, g1_dn=gdn, expected_r_canonical=list(ex), expected_g1_canonical=list(ey),
                         axis_errors_dn=list(error), paired_error_native=norm,
                         correct_u_error_native=correct_norms[-1],
                         descriptive_rgb_error_dn=[dn[c]-field(c, ex) for c in range(3)]))
    if ordinal in (6, 8):
        need(max(correct_norms) > 1., "fault-power", "actual wrong-map displacement >1 native pixel")
    return dict(kind="paired_two_site_coordinate", rows=rows,
                maximum_native=max(norms), rms_native=math.sqrt(math.fsum(v*v for v in norms)/len(norms)),
                maximum_axis_dn=max(map(abs, errors)), maximum_correct_u_native=max(correct_norms),
                expectation="fault-consistent" if ordinal in (6,8) else "correct-U")


def coordinate_rank(fields):
    need(type(fields) is list and len(fields) == 2 and all(type(r) is list and len(r) == 3 for r in fields),
         "rank", "two affine channel rows")
    a, b = fields
    det = number(a[1], "rank")*number(b[2], "rank")-number(a[2], "rank")*number(b[1], "rank")
    need(det != 0. and math.isfinite(det), "rank", "rank-two coordinates required")


def validate_source(receipt, p, ordinal, sources):
    source = receipt["source"]
    keys(source, ("attempts", "optional_counts", "optional_hooks", "records"), "source")
    n = len(p["selected"])
    same(source["attempts"], [1]*n, "source")
    same(source["optional_counts"], [int(ordinal == 2)]*n, "observer")
    same(source["optional_hooks"], n if ordinal in (2,3) else 0, "observer")
    need(type(source["records"]) is list and len(source["records"]) == n, "source", "record count")
    for local, original in enumerate(p["selected"]):
        _, evidence = sources.get(p["track"][original], ordinal == 9)
        expected = dict(local_index=local, original_index=original, probe_seed_index=local,
                        source_generation_pull=sim_record(p["track"][original]), **evidence)
        same(source["records"][local], expected, "source", 1e-8)


def read_case(plan_ref, receipt_ref, *, reads, budget, parser, context, ordinal,
              sources=None, private_fault=None):
    integer(ordinal, "population", 0, 9)
    need(private_fault in (None, "zero-crop", "exchange-crop", "quad-as-native", "unit-scale",
                            "transpose-output", "stale-association", "wrong-inverse", "rank-one"), "control", "named override")
    plan = reads.json(plan_ref)
    p = validate_plan(plan, ordinal, context)
    receipt = reads.json(receipt_ref)
    keys(receipt, ("schema", "status", "plan", "plan_sha256", "plan_bytes", "source", "output",
                   "command", "elapsed_seconds_before_receipt", "error", "secondary_errors", "validation_scope"), "receipt")
    same(receipt["schema"], "m193c-private-grid-receipt-v1", "receipt")
    same(receipt["status"], "COMPLETE_RGB_UNVERIFIED", "receipt")
    same(receipt["error"], None, "receipt")
    same(receipt["secondary_errors"], [], "receipt")
    same(receipt["plan"], plan, "receipt")
    same(receipt["plan_sha256"], plan_ref["sha256"], "receipt")
    same(receipt["plan_bytes"], plan_ref["bytes"], "receipt")
    same(receipt["command"], [context["build"]["path"], "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"], "command")
    need(0. <= number(receipt["elapsed_seconds_before_receipt"], "receipt") <= 240., "receipt", "reported child elapsed")
    same(receipt["validation_scope"], "actual shared production output; independent pixel read still required", "receipt")
    sources = Sources(budget) if sources is None else sources
    validate_source(receipt, p, ordinal, sources)
    output = receipt["output"]
    # Hash the bytes independently before parser, then parser checks the reopened bytes
    # against the same external SHA; replacement cannot silently alter admitted pixels.
    reads.file(output, 1 << 20)
    shape = [p["rect"][3]*2, p["rect"][2]*2, 3]
    budget.read_bytes += output["bytes"]
    try:
        pixels, evidence = parser.read_rgb_tiff(reference_path(output), shape, output["sha256"], budget)
    except parser.Refusal as exc:
        raise Refusal("tiff-format", str(exc)) from exc
    score = score_pixels(pixels, p, ordinal, private_fault)
    budget.check()
    return dict(schema="m193c-independent-grid-case-v1", ordinal=ordinal, id=CASES[ordinal],
                status="PASS_PRIVATE_CASE" if private_fault is None else "PRIVATE_OVERRIDE_RETURNED",
                plan=plan_ref, receipt=receipt_ref, tiff=output, tiff_evidence=evidence,
                predicted=dict(k=p["k"], crop_quad=list(p["rect"]), selected=p["selected"]),
                observer=receipt["source"], score=score)


def read_population(rows, *, reads, budget, parser, context, kernel_witness,
                    private_fault=None, partial=None):
    """Parent must separately validate launch/index authority before final admission."""
    sources = Sources(budget)
    result = partial if partial is not None else {}
    result.update(schema="m193c-independent-grid-population-v1", status="RUNNING", cases=[],
                  precision=None, error=None, authority_scope="semantic/pixel child; parent launch authority required")
    try:
        validate_rows(rows)
        for ordinal, row in enumerate(rows):
            result["cases"].append(dict(ordinal=ordinal,id=CASES[ordinal],status="STARTED",error=None))
            fault = private_fault[1] if private_fault and private_fault[0] == ordinal else None
            case = read_case(row["plan"], row["receipt"], reads=reads, budget=budget,
                             parser=parser, context=context, ordinal=ordinal, sources=sources, private_fault=fault)
            same_ref(case["tiff"], row["tiff"])
            result["cases"][-1] = case
        for group in ((1,2,3), (5,7)):
            hashes = [result["cases"][i]["tiff"]["sha256"] for i in group]
            pixels = [result["cases"][i]["tiff_evidence"]["pixel_sha256"] for i in group]
            need(len(set(hashes)) == len(set(pixels)) == 1, "byte-null", "complete file and pixel identity")
        need(kernel_witness is not None, "precision", "actual bound Rust component witness required")
        # Concrete component schema is attached after its producer is frozen.
        result["precision"] = verify_precision(kernel_witness, rows, reads=reads, budget=budget,
                                                context=context, sources=sources)
        reads.recheck()
        result["work"] = budget.receipt()
        result["status"] = "PASS_GRID_SEMANTICS_AND_PIXELS" if private_fault is None else "PRIVATE_OVERRIDE_RETURNED"
        return result
    except Exception as exc:
        result["status"] = "REFUSED_GRID_READER"
        result["error"] = dict(type=type(exc).__name__, message=str(exc), boundary=getattr(exc, "boundary", None))
        if result["cases"] and result["cases"][-1]["status"] == "STARTED":
            result["cases"][-1].update(status="REFUSED_CASE",error=dict(result["error"]))
        raise


def validate_rows(rows):
    need(type(rows) is list and len(rows) == 10, "population", "all ten rows")
    for ordinal, row in enumerate(rows):
        keys(row, ("ordinal", "id", "plan", "plan_launch", "receipt", "tiff", "render_launch"), "population")
        same(row["ordinal"], ordinal, "population")
        same(row["id"], CASES[ordinal], "population")


def verify_precision(witness, rows, *, reads, budget, context, sources):
    result = reads.json(witness)
    keys(result, ("schema", "status", "cases", "command", "environment", "elapsed_seconds_before_receipt",
                  "error", "secondary_errors", "compiled_inputs", "scope"), "precision")
    same(result["schema"], "m193c-precision-witness-v1", "precision")
    same(result["status"], "COMPONENT_OBSERVED_UNVERIFIED", "precision")
    same(result["error"], None, "precision")
    same(result["secondary_errors"], [], "precision")
    same(result["environment"], ENV, "environment")
    same(result["compiled_inputs"], dict(precision_witness_sha256=context["precision_witness_sha256"]), "source")
    name = TEST.rsplit("::", 1)[0] + "::precision_witness::m193c_private_precision_witness"
    same(result["command"], [context["build"]["path"], "--exact", name, "--ignored", "--test-threads=1", "--nocapture"], "command")
    need(0. <= number(result["elapsed_seconds_before_receipt"], "precision") <= 240., "precision", "reported component time")
    same(result["scope"], "58 generated frames,3712 fixed R/G1 component samples; no production TIFF/no random plant noise", "precision")
    need(type(result["cases"]) is list and len(result["cases"]) == 10, "precision", "ten component cases")
    checked, maximum = [], 0.
    live = dict(integer=0, fractional=0, positive_imaginary=0, negative_imaginary=0,
                positive_translation=0, negative_translation=0)
    for ordinal, child_ref in enumerate(result["cases"]):
        budget.check()
        child = reads.json(child_ref)
        keys(child, ("schema", "status", "plan", "plan_sha256", "plan_bytes", "source", "rows", "scope"), "precision")
        same(child["schema"], "m193c-precision-case-v1", "precision")
        same(child["status"], "COMPONENT_OBSERVED_UNVERIFIED", "precision")
        same(child["scope"], "existing MHC/Catmull f32 values and actual warp u16; independent numeric oracle pending", "precision")
        plan = reads.json(rows[ordinal]["plan"])
        same(child["plan"], plan, "precision")
        same(child["plan_sha256"], rows[ordinal]["plan"]["sha256"], "precision")
        same(child["plan_bytes"], rows[ordinal]["plan"]["bytes"], "precision")
        p = validate_plan(plan, ordinal, context)
        validate_source(child, p, ordinal, sources)
        need(type(child["rows"]) is list and len(child["rows"]) == 64*len(p["selected"]), "precision", "complete component rows")
        count = 0
        for local, original in enumerate(p["selected"]):
            array, evidence = sources.get(p["track"][original], ordinal == 9)
            for pair, (x, y) in enumerate(PAIRS):
                for channel, dx, label in ((0,0,"R"), (1,1,"G1")):
                    actual = child["rows"][count]
                    count += 1
                    keys(actual, ("pair_index", "channel", "output_native_xy", "full_native_xy",
                          "sample_native_xy", "sample_f32_dn", "sample_f32_bits", "black_restored_f32_dn",
                          "black_restored_f32_bits", "rounded_u16", "actual_warp_u16", "local_index", "original_index"), "precision")
                    for key, value in dict(pair_index=pair, channel=label, local_index=local,
                                           original_index=original, output_native_xy=[x+dx,y],
                                           full_native_xy=[x+dx+2*p["rect"][0],y+2*p["rect"][1]]).items():
                        same(actual[key], value, "precision-association")
                    xy = actual["sample_native_xy"]
                    need(type(xy) is list and len(xy) == 2, "precision-association", "coordinate extent")
                    xy = [number(v, "precision-association") for v in xy]
                    expected_xy = sample_expected(p, ordinal, original, (x+dx,y))
                    need(max(abs(a-b) for a,b in zip(xy, expected_xy)) <= 2e-11,
                         "precision-association", "actual source coordinates")
                    oracle = gather_oracle(array, xy, channel)
                    if all(v == math.floor(v) for v in xy):
                        need(oracle["modeled_f32"] == mhc(array,int(xy[0]),int(xy[1]),channel),
                             "precision", "integer Catmull reproduction")
                        live["integer"] += 1
                    else:
                        live["fractional"] += 1
                    t = p["track"][original]
                    live["positive_imaginary"] += int(t[1] > 0.)
                    live["negative_imaginary"] += int(t[1] < 0.)
                    live["positive_translation"] += int(t[2] > 0.)
                    live["negative_translation"] += int(t[2] < 0.)
                    sources.check_stencil_evaluation(p["track"][original], xy, ordinal == 9)
                    for key, expected in (("sample_f32_bits", oracle["modeled_bits"]),
                                          ("black_restored_f32_bits", oracle["black_added_bits"]),
                                          ("rounded_u16", oracle["rounded_u16"]),
                                          ("actual_warp_u16", oracle["rounded_u16"])):
                        same(actual[key], expected, "precision-kernel")
                    same(actual["sample_f32_dn"], oracle["modeled_f32"], "precision-kernel")
                    same(actual["black_restored_f32_dn"], oracle["black_added_f32"], "precision-kernel")
                    expected_field = field(channel, apply(inverse(p["track"][original]), xy), ordinal == 9)
                    quantization_error = oracle["f64"] - expected_field
                    need(abs(quantization_error) <= 1.953125+1e-7, "precision", "source/MHC/Catmull quantization envelope")
                    maximum = max(maximum, abs(oracle["error_dn"]))
                    checked.append(dict(case_ordinal=ordinal, local_index=local, original_index=original,
                        pair_index=pair, channel=label, sample_native_xy=xy, source_sha256=evidence["sha256_u16_le"],
                        quantization_error_dn=quantization_error, **oracle))
    need(len(checked) == 3712, "precision", "entire 3712 sample population")
    need(all(v > 0 for v in live.values()), "precision", "actual signed/nonidentity/integer population")
    return dict(schema="m193c-independent-grid-precision-v1", status="PASS_LITERAL_KERNEL_PRECISION",
                witness=witness, samples=checked, liveness=live, maximum_gather_error_dn=maximum,
                source_stencil_sites=len(sources.checked),
                maximum_source_evaluation_error_dn=sources.maximum_source_evaluation_error,
                scope="actual fixed-site f32/kernel+warp samples, not a universal floating-point bound")


def clone(value):
    return strict_json(json.dumps(value, allow_nan=False, separators=(",", ":")).encode())


def run_controls(rows, *, reads, budget, parser, context, kernel_witness,
                 write_bytes, partial=None):
    """Fixed entry controls; write_bytes(name,raw)->FileRef uses parent's counted store.

    The parent passes a mutable child before calling, retaining attempted history
    even if an assertion or persistence operation fails. No new production TIFF.
    """
    result = partial if partial is not None else {}
    result.update(schema="m193c-independent-grid-controls-v1", status="RUNNING", checks=[], error=None)
    sources = Sources(budget)

    def check(name, boundary, call):
        row = dict(id=name, expected_boundary=boundary, status="STARTED", observed=None)
        result["checks"].append(row)
        try:
            value = call()
        except Refusal as exc:
            row["observed"] = dict(boundary=exc.boundary, type=type(exc).__name__, message=str(exc))
            row["status"] = "FAILED_WRONG_REFUSAL"
            need(boundary is not None and exc.boundary == boundary, "instrument", "wrong refusal boundary: "+name)
            row["status"] = "PASS_EXPECTED_REFUSAL"
            return None
        except Exception as exc:
            row["observed"] = dict(type=type(exc).__name__, message=str(exc))
            row["status"] = "FAILED_UNEXPECTED_EXCEPTION"
            raise
        row["status"] = "FAILED_FALSE_ACCEPTANCE"
        need(boundary is None, "instrument", "false acceptance: "+name)
        row["status"] = "PASS_VALID_COMPANION"
        return value

    def case(ordinal, fault=None, plan_ref=None, receipt_ref=None):
        return read_case(plan_ref or rows[ordinal]["plan"], receipt_ref or rows[ordinal]["receipt"],
                         reads=reads, budget=budget, parser=parser, context=context,
                         ordinal=ordinal, sources=sources, private_fault=fault)

    def save_json(name, value):
        raw = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()+b"\n"
        need(len(raw) <= 4 << 20, "resource", "private JSON extent")
        return write_bytes(name, raw)

    def mutant(name, ordinal, edit_plan=None, edit_receipt=None, output=None):
        plan = reads.json(rows[ordinal]["plan"])
        receipt = reads.json(rows[ordinal]["receipt"])
        if edit_plan:
            edit_plan(plan)
        plan_ref = save_json(name+"-plan.json", plan)
        receipt["plan"] = plan
        receipt["plan_sha256"], receipt["plan_bytes"] = plan_ref["sha256"], plan_ref["bytes"]
        if edit_receipt:
            edit_receipt(receipt)
        if output is not None:
            receipt["output"] = output
        receipt_ref = save_json(name+"-receipt.json", receipt)
        return case(ordinal, plan_ref=plan_ref, receipt_ref=receipt_ref)

    try:
        validate_rows(rows)
        genuine = {}
        for i in (1,4,6,8,9):
            genuine[i] = check(f"genuine-case-{i}", None, lambda i=i: case(i))
        check("missing-case", "population", lambda: validate_rows(rows[:-1]))
        duplicate = clone(rows); duplicate[9] = clone(duplicate[8])
        check("duplicate-case", "population", lambda: validate_rows(duplicate))
        reordered = clone(rows); reordered[1], reordered[2] = reordered[2], reordered[1]
        check("reordered-case", "population", lambda: validate_rows(reordered))
        wrong_type = clone(rows); wrong_type[1]["ordinal"] = True
        check("bool-case-ordinal", "population", lambda: validate_rows(wrong_type))
        # Each mutation reaches the actual bounded read_case, with resealed plan
        # and receipt bytes. Status/hash-only rejection is not the claimed power.
        choices = (
            ("float-width", "geometry", lambda p: p["geometry"]["full_native"].__setitem__(0,320.), None),
            ("float-decode-count", "source", None, lambda r: r["source"]["attempts"].__setitem__(0,1.)),
            ("wrong-local", "association", lambda p: p["selected"][0].__setitem__("local_index",1), None),
            ("wrong-original", "association", lambda p: p["selected"][0].__setitem__("original_index",1), None),
            ("wrong-probe", "association", lambda p: p["selected"][0].__setitem__("probe_seed_index",1), None),
            ("stale-source", "source", None, lambda r: r["source"]["records"][0].__setitem__("sha256_u16_le","0"*64)),
            ("changed-range", "sensor", lambda p: p["sensor"].__setitem__("range_dn",15360), None),
            ("nonunity-wb", "sensor", lambda p: p["sensor"]["writer_wb_f32"].__setitem__(0,2.), None),
            ("missing-final-hull", "config", lambda p: p["config"].__setitem__("hull","Off"), None),
            ("unexpected-environment", "environment", lambda p: p["environment"].__setitem__("STREHL_DEMOSAIC","directional"), None),
            ("wrong-compiled-source", "source", lambda p: p["compiled_inputs"].__setitem__("private_adapter_sha256","0"*64), None),
            ("failed-receipt", "receipt", None, lambda r: r.__setitem__("status","REFUSED_PRIVATE_OUTPUT")),
            ("concealed-terminal-error", "receipt", None, lambda r: r.__setitem__("error","preserved failure")),
            ("wrong-half-pixel-centre", "geometry", lambda p: p["geometry"].__setitem__("native_centre",[159.5,119.5]), None),
        )
        for name, boundary, ep, er in choices:
            check(name, boundary, lambda name=name, ep=ep, er=er: mutant(name,1,ep,er))
        plan_raw = reads.file(rows[1]["plan"])
        need(plan_raw.lstrip().startswith(b"{"), "instrument", "JSON object companion")
        for name, prefix in (("duplicate-json-key", b'"schema":"duplicate",'),
                             ("overflow-json-real", b'"private_overflow":1e999,')):
            at = plan_raw.index(b"{")+1
            pref = write_bytes(name+".json", plan_raw[:at]+prefix+plan_raw[at:])
            check(name,"json",lambda pref=pref: case(1,plan_ref=pref))
        tiff_ref = genuine[1]["tiff"]
        evidence = genuine[1]["tiff_evidence"]
        original_raw = reads.file(tiff_ref,1 << 20)
        tags = evidence["tags"]
        offsets = tags[273]["value"]
        heights = tags[278]["value"][0]
        width = evidence["shape"][1]
        endian = evidence["endian"]
        altered = bytearray(original_raw)
        x,y = PAIRS[0]
        offset = offsets[y//heights]+((y%heights)*width+x)*6
        code = struct.unpack_from(endian+"H",altered,offset)[0]
        need(code+200 < 65535,"instrument","changed-code headroom")
        struct.pack_into(endian+"H",altered,offset,code+200)
        ref = write_bytes("changed-r-code.tif",bytes(altered))
        check("changed-r-code","coordinate",lambda: mutant("changed-r-code",1,output=ref))
        altered = bytearray(original_raw)
        for offset, count in zip(offsets,tags[279]["value"]):
            for at in range(offset,offset+count,6):
                altered[at:at+2],altered[at+4:at+6] = altered[at+4:at+6],altered[at:at+2]
        ref = write_bytes("swapped-r-b.tif",bytes(altered))
        check("swapped-r-b","coordinate",lambda: mutant("swapped-r-b",1,output=ref))
        altered = bytearray(original_raw)
        x,y = PAIRS[0]
        target = offsets[y//heights]+((y%heights)*width+x+1)*6+2
        other = offsets[(y+1)//heights]+(((y+1)%heights)*width+x)*6+2
        altered[target:target+2] = original_raw[other:other+2]
        ref = write_bytes("spatial-green-swap.tif",bytes(altered))
        check("spatial-green-swap","coordinate",lambda: mutant("spatial-green-swap",1,output=ref))
        ref = write_bytes("appended-tiff.tif",original_raw+b"\0\0")
        check("appended-tiff","tiff-format",lambda: mutant("appended-tiff",1,output=ref))
        for name, ordinal in (("transpose-output",1),("zero-crop",1),("exchange-crop",1),
                              ("quad-as-native",1),("unit-scale",4),("stale-association",6),("wrong-inverse",6)):
            check(name,"coordinate",lambda name=name,ordinal=ordinal: case(ordinal,name))
        check("rank-one-field","rank",lambda: case(1,"rank-one"))
        check("restored-crop-pixels",None,lambda: case(1))
        check("restored-scale-pixels",None,lambda: case(4))
        check("restored-association-pixels",None,lambda: case(6))
        precision = check("genuine-complete-precision",None,
            lambda: verify_precision(kernel_witness,rows,reads=reads,budget=budget,context=context,sources=sources))
        # Reseal a genuine component child and top manifest, then reread the actual
        # complete component entry. The fault is actual saved f32 data, not a label.
        base = reads.json(kernel_witness)
        child = reads.json(base["cases"][1])
        changed = clone(child)
        sample = changed["rows"][66]  # local1, pair1, R; fixed before execution.
        need(sample["local_index"] == 1 and sample["pair_index"] == 1 and sample["channel"] == "R",
             "instrument","literal precision fault site")
        sample["sample_f32_dn"] = f32(sample["sample_f32_dn"]+1.)
        sample["sample_f32_bits"] = bits(sample["sample_f32_dn"])
        sample["black_restored_f32_dn"] = f32(sample["sample_f32_dn"]+512.)
        sample["black_restored_f32_bits"] = bits(sample["black_restored_f32_dn"])
        sample["rounded_u16"] = math.floor(sample["black_restored_f32_dn"]+.5)
        sample["actual_warp_u16"] = sample["rounded_u16"]
        base["cases"][1] = save_json("changed-kernel-case.json",changed)
        pref = save_json("changed-kernel-index.json",base)
        check("coherent-kernel-value-fault","precision-kernel",
            lambda: verify_precision(pref,rows,reads=reads,budget=budget,context=context,sources=sources))
        for fault in ("omit-outer","opposite-channel"):
            base = reads.json(kernel_witness)
            changed = clone(child)
            sample = changed["rows"][66]
            p = predicted(1)
            array,_ = sources.get(p["track"][1],False)
            bad = gather_oracle(array,sample["sample_native_xy"],0,private_fault=fault)
            need(abs(bad["modeled_f32"]-sample["sample_f32_dn"]) > .125,
                 "instrument","literal kernel destroyer must be live")
            sample.update(sample_f32_dn=bad["modeled_f32"],sample_f32_bits=bad["modeled_bits"],
                black_restored_f32_dn=bad["black_added_f32"],black_restored_f32_bits=bad["black_added_bits"],
                rounded_u16=bad["rounded_u16"],actual_warp_u16=bad["rounded_u16"])
            base["cases"][1] = save_json(fault+"-kernel-case.json",changed)
            pref = save_json(fault+"-kernel-index.json",base)
            check(fault+"-kernel","precision-kernel",lambda pref=pref:
                verify_precision(pref,rows,reads=reads,budget=budget,context=context,sources=sources))
        check("restored-complete-precision",None,
            lambda: verify_precision(kernel_witness,rows,reads=reads,budget=budget,context=context,sources=sources))
        result["precision"] = precision
        result["counts"] = dict(total=len(result["checks"]),
            rejected=sum(r["status"] == "PASS_EXPECTED_REFUSAL" for r in result["checks"]),
            valid=sum(r["status"] == "PASS_VALID_COMPANION" for r in result["checks"]))
        same(result["counts"], dict(total=45,rejected=35,valid=10), "instrument")
        result["status"] = "PASS_GRID_READER_CONTROLS"
        result["work"] = budget.receipt()
        return result
    except Exception as exc:
        result["status"] = "REFUSED_GRID_READER_CONTROLS"
        result["error"] = dict(type=type(exc).__name__,message=str(exc),boundary=getattr(exc,"boundary",None))
        raise
