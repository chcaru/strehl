"""Independent saved M194h consumer checker; no subject calls or native input reads.
Prospective until source review, exact release and one authorized execution.
"""
import time
START_CPU, START_WALL = time.process_time(), time.monotonic()
from fractions import Fraction
import math

SCHEMA = "m194h-independent-saved-consumer-check-v1"
SITES_NATIVE = ((202, 104), (205, 113))
ORIGIN_NATIVE = (10, 8)
OUTPUT_NATIVE = (300, 226)
LEVEL_SIZES = ((150, 113), (75, 57), (38, 29), (19, 15))
CFA_OFFSETS = ((0, 0), (1, 0), (0, 1), (1, 1))
FRAME_IDS = (0, 1, 2, 3, 4)
MODES = ("H", "P", "P0")
OBSERVERS = ("off", "on", "placebo")
OLD_READER = {
    "path": "experiments/m194g-larger-pupil/independent-quality-result-check.py",
    "bytes": 50432,
    "sha256": "6c69efa777efccca740901edac9e633deb9a16f3dbe539d66c4e6337994e8539",
}
OLD_RESULT = {
    "path": "experiments/m194g-larger-pupil/independent-quality-result-check-1/result.json",
    "bytes": 317942,
    "sha256": "5a0c6dcc84608a64e7545ee9ac751441c468194347eb0cf7534793b0c971a4c5",
}
IDEAL = {
    "path": "experiments/m194g-larger-pupil/independent-quality-target-1/scalar.npy",
    "bytes": 614528,
    "sha256": "91fbd5bf692f9411c4394d4a60e805d998eec0061553c5fcba2059f2e505e795",
}
ARCHIVED_TIFFS = {
    "noise-free": {"path": "experiments/m194g-larger-pupil/production-matrix-1/case-00.tif",
                   "bytes": 407403,
                   "sha256": "34e13e84725cc792607a0e05834bf69607cc45f3f92910503259133d6f62c771"},
    "P": {"path": "experiments/m194g-larger-pupil/production-matrix-1/case-14.tif",
          "bytes": 407403,
          "sha256": "36a995a53f842077bd9ffa0ad705a8da3af432c28c42a8da3793bce4513a8372"},
    "H": {"path": "experiments/m194g-larger-pupil/production-matrix-1/case-15.tif",
          "bytes": 407403,
          "sha256": "a1b6be484b9f13914c95a03d60fb80ef02761b935f478ffb3eed8b9e18704874"},
}


class ContractError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise ContractError(reason)


def integer(value, lo, hi, label):
    need(type(value) is int and lo <= value <= hi, label)
    return value


def scalar(value, label, nonnegative=False):
    need(type(value) in (int, float) and math.isfinite(value), label)
    need(not nonnegative or value >= 0, label)
    return value


def file_ref(value):
    need(type(value) is dict and set(value) == {"path", "bytes", "sha256"}, "closed FileRef")
    path = value["path"]
    need(type(path) is str and 0 < len(path) <= 512 and "\\" not in path
         and ":" not in path and not path.startswith("/")
         and all(part not in ("", ".", "..") for part in path.split("/")), "relative FileRef path")
    integer(value["bytes"], 1, 64 << 20, "positive FileRef extent")
    h = value["sha256"]
    need(type(h) is str and len(h) == 64 and all(c in "0123456789abcdef" for c in h), "FileRef digest")
    return value


def above_floor(energy, floor):
    """Independent strict partition; booleans/nonfinite values cannot alias numbers."""
    scalar(energy, "nonnegative finite E", True)
    scalar(floor, "nonnegative finite F", True)
    return energy > floor


def check_partition(energy, floor, declared_above, p_weight, used_p0):
    need(type(declared_above) is bool, "typed classification bit")
    actual = above_floor(energy, floor)
    need(declared_above is actual, "classification equals independent E>F")
    scalar(p_weight, "positive P weight", True)
    need(p_weight > 0, "positive P weight")
    scalar(used_p0, "nonnegative P0 weight", True)
    need(used_p0 == (p_weight if actual else 0), "P0 differs only at E<=F")
    return actual


def _plus(table, key, value):
    table[key] = table.get(key, Fraction(0)) + value
    if table[key] == 0:
        del table[key]


def expand_parent_taps(position, parent_extent):
    """Adjoint dependencies, not a call to the producer's forward EXPAND."""
    integer(parent_extent, 1, 320, "expand parent extent")
    integer(position, 0, 2 * parent_extent - 1, "expand child position")
    c = position // 2
    choices = ((c - 1, Fraction(1, 8)), (c, Fraction(6, 8)), (c + 1, Fraction(1, 8)))
    if position % 2:
        choices = ((c, Fraction(1, 2)), (c + 1, Fraction(1, 2)))
    result = {}
    for index, weight in choices:
        _plus(result, min(parent_extent - 1, max(0, index)), weight)
    return result


def collapse_influence(quad_xy):
    """Every band/base coefficient influencing one pre-hull CFA plane sample.

    Exact dyadic coefficients describe the real linear operator; they are not
    a claim of bit-exact floating-point reconstruction or post-hull linearity.
    """
    x, y = quad_xy
    integer(x, 0, LEVEL_SIZES[0][0] - 1, "root quad x")
    integer(y, 0, LEVEL_SIZES[0][1] - 1, "root quad y")
    current = {(x, y): Fraction(1)}
    levels = [dict(current)]
    for k in range(1, len(LEVEL_SIZES)):
        width, height = LEVEL_SIZES[k]
        previous = LEVEL_SIZES[k - 1]
        need(((previous[0] + 1) // 2, (previous[1] + 1) // 2) == (width, height), "level size reduction")
        following = {}
        for (cx, cy), influence in current.items():
            for px, wx in expand_parent_taps(cx, width).items():
                for py, wy in expand_parent_taps(cy, height).items():
                    _plus(following, (px, py), influence * wx * wy)
        levels.append(following)
        current = following
    return levels


def native_to_cfa(local_xy):
    x, y = local_xy
    integer(x, 0, OUTPUT_NATIVE[0] - 1, "local native x")
    integer(y, 0, OUTPUT_NATIVE[1] - 1, "local native y")
    return 2 * (y % 2) + (x % 2), x // 2, y // 2


def red_mhc_taps(native_xy):
    """Exact red-output MHC dependencies for the two fixed interior sites."""
    need(tuple(native_xy) in SITES_NATIVE, "fixed selected native site")
    x, y = (native_xy[i] - ORIGIN_NATIVE[i] for i in range(2))
    need(2 <= x < OUTPUT_NATIVE[0] - 2 and 2 <= y < OUTPUT_NATIVE[1] - 2, "interior MHC support")
    if x % 2 == 0 and y % 2 == 0:
        offsets = ((0, 0, Fraction(1)),)
    else:
        need(x % 2 == y % 2 == 1, "fixed second site is blue CFA phase")
        offsets = ((0, 0, Fraction(3, 4)),
                   (-1, -1, Fraction(1, 4)), (1, -1, Fraction(1, 4)),
                   (-1, 1, Fraction(1, 4)), (1, 1, Fraction(1, 4)),
                   (-2, 0, Fraction(-3, 16)), (2, 0, Fraction(-3, 16)),
                   (0, -2, Fraction(-3, 16)), (0, 2, Fraction(-3, 16)))
    result = {}
    for dx, dy, weight in offsets:
        _plus(result, native_to_cfa((x + dx, y + dy)), weight)
    return result


def support_contract():
    """Conservative 5x5 native envelopes and exact red dependencies are distinct."""
    quad_roots = set()
    exact = {}
    for site in SITES_NATIVE:
        x, y = (site[i] - ORIGIN_NATIVE[i] for i in range(2))
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                _, qx, qy = native_to_cfa((x + dx, y + dy))
                quad_roots.add((qx, qy))
        exact[site] = red_mhc_taps(site)
    all_levels = [set() for _ in LEVEL_SIZES]
    influence = {}
    for root in sorted(quad_roots):
        influence[root] = collapse_influence(root)
        for k, entries in enumerate(influence[root]):
            all_levels[k].update(entries)
    return dict(quad_roots=tuple(sorted(quad_roots)),
                quad_sites_by_level=tuple(tuple(sorted(sites)) for sites in all_levels),
                red_mhc=exact, collapse=influence)


def check_support(actual_levels):
    need(type(actual_levels) is list and len(actual_levels) == 4, "three bands plus mean base")
    expected = support_contract()["quad_sites_by_level"]
    for k, (rows, wanted) in enumerate(zip(actual_levels, expected, strict=True)):
        need(type(rows) is list, "support row list")
        for row in rows:
            need(type(row) is list and len(row) == 2, "quad xy pair")
            integer(row[0], 0, LEVEL_SIZES[k][0] - 1, "quad support x")
            integer(row[1], 0, LEVEL_SIZES[k][1] - 1, "quad support y")
        normalized = [tuple(row) for row in rows]
        need(len(set(normalized)) == len(normalized) and tuple(sorted(normalized)) == wanted,
             "complete inverse support, no duplicates or omitted sites")
    return True


def expected_case_keys():
    noisy = [(743, mode, observer) for mode in MODES for observer in OBSERVERS]
    return tuple(noisy + [(None, mode, "off") for mode in MODES])


def check_case_population(keys, complete):
    need(type(keys) is list and type(complete) is bool, "typed finite population")
    expected = set(expected_case_keys())
    normalized = []
    for row in keys:
        need(type(row) in (list, tuple) and len(row) == 3, "case seed/mode/observer")
        seed, mode, observer = row
        need(seed is None or type(seed) is int, "typed seed")
        need(type(mode) is str and type(observer) is str, "typed arm and observer")
        key = (seed, mode, observer)
        need(key in expected and key not in normalized, "fixed unique case")
        normalized.append(key)
    need(not complete or set(normalized) == expected, "complete twelve-case consumer population")
    return tuple(normalized)


# Saved-output entry point. This file is prospective until independently reviewed.
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import time
import traceback
import weakref

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()
KIB, MIB = 1024, 1 << 20
LIMITS = dict(cpu_seconds=60, wall_seconds=120, committed_bytes=1 << 30, file_bytes=16 << 20)
PUBLICATION = dict(cpu_seconds=.5, wall_seconds=1)
NP = None
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
CASE_CAPS = {"plan.json":128*KIB,"trace.bin":128*KIB,"trace.json":16*KIB,
             "output.tif":512*KIB,"result.json":32*KIB,"result-stage.json":32*KIB,"failure.json":8*KIB}
STAGE_CAPS = {"build":(300,240,8 << 30),"components":(60,60,1 << 30),"render":(120,180,1 << 30)}
SUBJECT = HERE / "subject-1"
CORE_TEST = "pyramid::m194h::controls::fixed_threshold_null_and_observer_controls"
CLI_TEST = "merge_cmd::known_scene_benchmark::noise_pupil_bridge::pedestal_causality::m194h_fixed_pedestal_case"
COMPONENT_IDS = (
 "all-above-floor-weight-identity-exact-floor-destroyer-restoration",
 "threshold-three-floors-and-actual-partition-fault","noise-free-four-plane-flat-null",
 "all-arms-off-on-placebo-and-unarmed-H-P-bit-identity","strong-stripe-rejects-plain-mean",
 "session-rejects-nesting-and-restores-after-panic","unsupported-consumer-refused-before-frame-and-restored")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def strict(raw):
    def pairs(rows):
        out = {}
        for k, v in rows:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda x: need(False, "nonfinite JSON token"))
    def walk(x):
        if type(x) is float:
            need(math.isfinite(x), "nonfinite JSON value")
        elif type(x) is dict:
            for v in x.values(): walk(v)
        elif type(x) is list:
            for v in x: walk(v)
    walk(value)
    return value


def exact(a, b, label):
    need(encoded(a) == encoded(b), label)


def path_identity(value):
    need(type(value) is str and 0 < len(value) <= 1024, "bounded path text")
    if value.startswith("\\\\?\\"):
        value = value[4:]
        need(not value.upper().startswith("UNC"), "no network FileRef")
    p = Path(value)
    p = Path(os.path.abspath(p if p.is_absolute() else ROOT / p))
    need(p.is_relative_to(ROOT), "FileRef stays in repository")
    for part in (p, *p.parents):
        if part.exists():
            s = part.lstat()
            need(not stat.S_ISLNK(s.st_mode) and not getattr(s, "st_file_attributes", 0) & 0x400,
                 "no reparse or symlink evidence")
    need(p.resolve() == p, "canonical owned path identity")
    return p


def typed_ref(ref, cap, empty=False):
    need(type(ref) is dict and set(ref) == {"path", "bytes", "sha256"}, "closed actual FileRef")
    integer(ref["bytes"], 0 if empty else 1, cap, "role-specific FileRef extent")
    h = ref["sha256"]
    need(type(h) is str and len(h) == 64 and all(c in "0123456789abcdef" for c in h), "actual FileRef SHA")
    p = path_identity(ref["path"])
    if ref["bytes"] == 0:
        need(empty and h == EMPTY_SHA, "canonical empty evidence")
    return p


def same_ref(a, b):
    return (type(a) is dict and type(b) is dict and set(a) == set(b) == {"path", "bytes", "sha256"}
            and type(a["bytes"]) is type(b["bytes"]) is int
            and path_identity(a["path"]) == path_identity(b["path"])
            and a["bytes"] == b["bytes"] and a["sha256"] == b["sha256"])


def object_identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns,
            getattr(s, "st_file_attributes", 0), s.st_nlink)


def shared_identity(s):
    # Windows stat/fstat ctime conventions differ; retain ctime within each API.
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
            getattr(s, "st_file_attributes", 0), s.st_nlink)


class Budget:
    def __init__(self):
        self.owners = {}; self.peak = 0; self.decodes = 0; self.read_bytes = 0
    def check(self):
        need(time.process_time() - START_CPU + PUBLICATION["cpu_seconds"] <= LIMITS["cpu_seconds"], "independent CPU envelope")
        need(time.monotonic() - START_WALL + PUBLICATION["wall_seconds"] <= LIMITS["wall_seconds"], "independent wall envelope")
        self.owners = {k:v for k,v in self.owners.items() if v[0]() is not None}
        live = sum(v[1] for v in self.owners.values()); self.peak = max(self.peak, live)
        need(live <= 64*MIB, "named live numerical backing bound")
        need(self.decodes <= 15 and self.read_bytes <= 512*MIB, "finite decode/read work")
    def watch(self, *values):
        for a in values:
            if isinstance(a, NP.ndarray):
                root = a
                while isinstance(root.base, NP.ndarray): root = root.base
                self.owners[id(root)] = (weakref.ref(root), root.nbytes)
        self.check()
        return values[0] if len(values) == 1 else values
    def receipt(self):
        return dict(cpu_seconds=time.process_time()-START_CPU, wall_seconds=time.monotonic()-START_WALL,
                    decoded_tiffs=self.decodes, input_bytes_read=self.read_bytes,
                    peak_named_ndarray_bytes=self.peak, scope="sampled own process CPU/wall and named ndarray backing; OS memory/whole interval require external wrapper")


class Files:
    def __init__(self, budget): self.budget=budget; self.seen={}
    def read(self, ref, cap, empty=False, role_path=None, retain=True):
        p=typed_ref(ref,cap,empty)
        if role_path is not None: need(p==path_identity(str(role_path)), "exact evidence role path")
        before=p.stat();need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==ref["bytes"], "plain owned evidence identity")
        identity=object_identity(before);key=p.relative_to(ROOT).as_posix()
        prior=self.seen.get(key)
        record=dict(ref=dict(path=key,bytes=ref["bytes"],sha256=ref["sha256"]),identity=list(identity))
        if prior is not None:
            exact({k:prior[k] for k in ("ref","identity")},record,"stable repeated FileRef and path identity")
        h=hashlib.sha256();parts=[];count=0
        with p.open("rb") as stream:
            opened=os.fstat(stream.fileno());handle_identity=object_identity(opened)
            need(shared_identity(opened)==shared_identity(before),"same opened file shared identity")
            if prior is not None:
                exact(prior["handle_identity"],list(handle_identity),"stable repeated handle identity")
            while True:
                self.budget.check();block=stream.read(min(MIB,ref["bytes"]-count+1))
                if not block: break
                count+=len(block);need(count<=ref["bytes"],"file grew beyond exact extent")
                self.budget.read_bytes+=len(block);h.update(block)
                if retain: parts.append(block)
            need(object_identity(os.fstat(stream.fileno()))==handle_identity,"same final handle")
        need(object_identity(p.stat())==identity and count==ref["bytes"] and h.hexdigest()==ref["sha256"],"actual same-buffer extent/hash")
        record["handle_identity"]=list(handle_identity);self.seen[key]=record
        self.budget.check();return b"".join(parts) if retain else None
    def json(self, ref, cap=4*MIB, role_path=None): return strict(self.read(ref,cap,role_path=role_path))
    def actual(self,p,cap,empty=False):
        p=path_identity(str(p));need(len(p.relative_to(ROOT).as_posix())<=512,"finite inventory path width");s=p.stat();integer(s.st_size,0 if empty else 1,cap,"bounded actual extent")
        # Initial discovery is confined to a released fixed artifact role.
        before=object_identity(s);h=hashlib.sha256();n=0
        with p.open("rb") as f:
            opened=os.fstat(f.fileno());handle_identity=object_identity(opened)
            need(shared_identity(opened)==shared_identity(s),"actual ref open shared identity")
            while block:=f.read(min(MIB,cap-n+1)):
                n+=len(block);need(n<=cap,"actual ref cap");h.update(block);self.budget.read_bytes+=len(block);self.budget.check()
            need(object_identity(os.fstat(f.fileno()))==handle_identity,"actual ref close identity")
        need(object_identity(p.stat())==before,"actual ref final identity")
        return dict(path=p.relative_to(ROOT).as_posix(),bytes=n,sha256=h.hexdigest())
    def finish(self):
        for row in list(self.seen.values()):
            r=row["ref"];self.read(r,max(1,r["bytes"]),empty=r["bytes"]==0,retain=False)


class Output:
    def __init__(self,path):
        self.root=path_identity(str(path));need(self.root==HERE/"independent-check-1" and not self.root.exists(),"fresh fixed independent output")
        self.root.mkdir();self.phases=[];self.bytes=0
    def write(self,name,value,cap):
        raw=encoded(value);need(len(raw)<=cap and self.bytes+len(raw)<=8*MIB,"independent bounded record and aggregate")
        p=self.root/name;need(not p.exists(),"fresh independent file")
        with p.open("xb") as f:need(f.write(raw)==len(raw),"complete independent write");f.flush();os.fsync(f.fileno())
        self.bytes+=len(raw)
        return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=digest(raw))
    def phase(self,name,value):
        need(len(self.phases)<20,"fixed independent phase count")
        ref=self.write(f"phase-{len(self.phases):02d}.json",dict(phase=name,verified=value,overall_complete=False),256*KIB)
        self.phases.append(ref);return ref


def sources(files,mapping):
    need(type(mapping) is dict and 1<=len(mapping)<=512,"bounded source map")
    total=0
    for name,pin in mapping.items():
        need(type(name) is str and type(pin) is dict and set(pin)=={"bytes","sha256"},"source map record")
        ref=dict(path=name,**pin);file_ref(ref)
        need(path_identity(name).relative_to(ROOT).as_posix()==name,"canonical relative source name")
        integer(pin["bytes"],1,4*MIB,"positive source cap");total+=pin["bytes"]
    need(total<=16*MIB,"whole positive source cap")
    for name,pin in mapping.items():files.read(dict(path=name,**pin),4*MIB,retain=False)
    return dict(count=len(mapping),bytes=total,sha256=digest(encoded(mapping)))


def job_cpu(record):
    need(type(record) is dict,"Job record")
    for k in ("total_user_100ns","total_kernel_100ns","total_cpu_100ns","active_processes"):
        integer(record.get(k),0,1<<63,"typed Job accounting")
    need(record["total_cpu_100ns"]==record["total_user_100ns"]+record["total_kernel_100ns"],"Job component sum")
    return record["total_cpu_100ns"]/1e7


def child_record(files,ref,stage,index,expected_command):
    d=HERE/(stage+"-1" if stage!="render" else "subject-1")
    v=files.json(ref,32*KIB,d/f"child-{index:02}.json")
    need(v["command"]==expected_command,"detached actual child command")
    cap=16*MIB if stage=="build" and index<2 else 64*KIB
    lp=d/f"child-{index:02}.log";lr=files.actual(lp,cap,empty=True) if lp.exists() else None
    log=files.read(lr,cap,empty=True,role_path=lp) if lr else b""
    linked=lr is not None and v.get("log") is not None
    if linked:need(same_ref(lr,v["log"]),"detached terminal actual log binding")
    need(type(v["log_bytes"]) is int and v["log_bytes"]==len(log),"exact retained child log extent")
    cpu=job_cpu(v["job_accounting"]) if v["job_accounting"] is not None else None
    wall=v["wall_seconds"]
    if wall is not None:scalar(wall,"finite whole child wall",True)
    peak=v["job_memory"]["peak_job_memory_used_bytes"] if v["job_memory"] is not None else None
    if peak is not None:integer(peak,0,1<<63,"typed peak committed bytes")
    configured=v["configured_job_limits"]
    installed=False
    if configured is not None:
        integer(configured["flags"],0,0xffffffff,"typed installed Job flags")
        integer(configured["committed_bytes"],0,1<<63,"typed installed Job memory")
        installed=bool(configured["flags"] & 0x200 and configured["flags"] & 0x2000
                       and configured["committed_bytes"]==STAGE_CAPS[stage][2])
    resources=(None if cpu is None or wall is None or peak is None else
        cpu<=(20 if stage=="render" else STAGE_CAPS[stage][0]) and
        wall<=(20 if stage=="render" else STAGE_CAPS[stage][1]) and peak<=STAGE_CAPS[stage][2])
    terminal=bool(v["terminal_job_accounting"] is True and cpu is not None and v["job_accounting"]["active_processes"]==0)
    okay=(linked and terminal and installed and resources is True and v["error"] is None and not v["cleanup_errors"]
          and v["exit_code"]==0 and v["direct_exit_observed"] is True and v["pipe_eof_observed"] is True
          and type(v["post_exit_drain"]) is dict and v["post_exit_drain"]["completed"] is True)
    return dict(ref=ref,cpu_seconds=cpu,wall_seconds=wall,complete=bool(okay),terminal=terminal,
                resource_admissible=resources,committed_limit_installed=installed,log_association_verified=linked,log=log,log_ref=lr)


def stage_bundle(files,bundle,stage):
    caps={"result":64*KIB,"tail":8*KIB,"outer":64*KIB,"stdout":8*KIB,"stderr":32*KIB,"exit":KIB}
    need(type(bundle) is dict and set(bundle)==set(caps),"closed six-ref stage bundle")
    raw={k:files.read(bundle[k],cap,empty=k=="stderr") for k,cap in caps.items()}
    v,t,o,a=(strict(raw[k]) for k in ("result","tail","outer","stdout"))
    d=HERE/(stage+"-1" if stage!="render" else "subject-1")
    need(path_identity(bundle["result"]["path"])==d/"result.json" and path_identity(bundle["tail"]["path"])==d/"parent-tail.json","fixed stage terminal roles")
    need(set(o)=={"schema","command","source","exit_code","timeout_terminated","elapsed_wall_seconds","stdout","stderr","exit","stdout_bytes","stderr_bytes","scope"} and o["schema"]=="m194h-stage-external-v1","closed external stage receipt")
    need(v["schema"]=="m194h-owned-stage-v1" and v["stage"]==stage and o["command"]==v["invocation"],"actual stage identity")
    release=files.json(v["release"],MIB)
    need(set(release)=={"schema","stage","source_bindings","inputs","command","children","binaries","subject_grant","prerequisites"}
         and release["schema"]=="m194h-owned-stage-release-v1" and release["stage"]==stage,"closed original stage release")
    need([v["release"]["sha256"] if x=="ACTUAL_RELEASE_SHA256" else x for x in release["command"]]==v["invocation"],"stage release exact argv")
    driver="experiments/m194h-pedestal-causality/build-and-run.py"
    need(same_ref(o["source"],dict(path=driver,**release["source_bindings"][driver])),"executed driver source")
    for k in ("stdout","stderr","exit"):need(same_ref(o[k],bundle[k]),"outer actual stream identity")
    need(type(o["stdout_bytes"]) is int and type(o["stderr_bytes"]) is int and o["stdout_bytes"]==len(raw["stdout"]) and o["stderr_bytes"]==len(raw["stderr"]),"outer stream extents")
    need(set(a)=={"status","result","tail"} and same_ref(a["result"],bundle["result"]) and same_ref(a["tail"],bundle["tail"]) and a["status"]==v["status"] and raw["stdout"]==encoded(a),"exact final advertisement")
    need(t["schema"]=="m194h-parent-publication-tail-v1" and same_ref(t["result"],bundle["result"]),"tail canonical association")
    exact(t["final_external_allowance"],dict(cpu_seconds=2,wall_seconds=3),"parent publication reserve")
    for k in ("actual_parent_cpu_sample","whole_wall_sample","completed_child_cpu_seconds","live_child_cpu_seconds"):
        scalar(t[k],"finite nonnegative parent sample",True)
    scalar(o["elapsed_wall_seconds"],"actual whole outer wall",True)
    need(o["elapsed_wall_seconds"]<=t["whole_wall_sample"]+3,"actual outer publication tail")
    complete=(v["status"]=="COMPLETE_STAGE_UNVERIFIED" and v.get("error") is None and not v.get("finalization_errors")
              and type(o["exit_code"]) is int and o["exit_code"]==0 and raw["exit"].strip()==b"0" and o["timeout_terminated"] is False
              and t["cpu_accounting_complete"] is True and t["live_child_cpu_seconds"]==0)
    children=v["children"];need(type(children) is list and len(children)<=len(release["children"]),"stage child prefix")
    observed=[child_record(files,r,stage,i,release["children"][i]) for i,r in enumerate(children)]
    total=math.fsum(c["cpu_seconds"] for c in observed if c["cpu_seconds"] is not None)
    job_association=abs(total-t["completed_child_cpu_seconds"])<=1e-8
    if complete:need(job_association,"each terminal Job counted once")
    resources=(total+t["actual_parent_cpu_sample"]+2<=STAGE_CAPS[stage][0] and o["elapsed_wall_seconds"]<=STAGE_CAPS[stage][1])
    complete=bool(complete and resources and job_association and len(observed)==len(release["children"]) and all(c["complete"] for c in observed))
    return dict(result=v,release=release,children=observed,complete=complete,
                summary=dict(stage=stage,bundle=bundle,complete=complete,resources=resources,job_cpu_seconds=total,
                parent_cpu_sample=t["actual_parent_cpu_sample"],charged_parent_tail_cpu=2,whole_wall_seconds=o["elapsed_wall_seconds"],
                scope="exact retained child Job CPU; parent sample plus reserved tail, not measured parent exit CPU"))


# Numerical checks below consume saved small records only; never call the subject.
WEIGHT_RTOL = 2e-5
WEIGHT_ATOL = 1e-40
F32_U = 2.0 ** -24


def f32(x):
    y=struct.unpack("<f",struct.pack("<f",x))[0]
    need(math.isfinite(y),"finite independently rounded f32")
    return y


def word_float(x):
    integer(x,0,0xffffffff,"u32 trace word")
    v=struct.unpack("<f",struct.pack("<I",x))[0]
    need(math.isfinite(v),"finite original f32 trace operand")
    return v


def float_word(x): return struct.unpack("<I",struct.pack("<f",f32(x)))[0]


def rounded_add(a,b): return f32(a+b)


def sum_f32(values):
    total=0.0
    for x in values: total=rounded_add(total,x)
    return total


def close_weight(actual,expected):
    need(actual>=0 and expected>=0 and abs(actual-expected)<=WEIGHT_ATOL+WEIGHT_RTOL*abs(expected),
         "independent binary64 weight bound")


def weights64(e,f,exponent,sharpen,k):
    p=f32(exponent*f32(sharpen**(2-k)))
    excess=max(f32(e-f),0.)
    r=(excess/max(f,1.))/64.
    h=0. if excess==0 else r if p==1 else r*r if p==2 else math.exp(max(-80.,min(80.,p*math.log(r))))
    r=math.hypot(excess/max(f,1.),1.)/64.
    pw=math.exp(max(-80.,min(80.,p*math.log(r))))
    return h,pw


def support_indices():
    s=support_contract()["quad_sites_by_level"]
    return [sorted(y*LEVEL_SIZES[k][0]+x for x,y in points) for k,points in enumerate(s)]


def unpack_trace(raw):
    need(len(raw)%4==0 and len(raw)<=128*KIB,"bounded u32 TLV bytes")
    words=list(struct.unpack("<"+"I"*(len(raw)//4),raw))
    lengths={1:9,2:13,3:6,4:8,5:5,6:3,7:2,8:1};rows=[];at=0
    while at<len(words):
        need(at+2<=len(words),"complete TLV header")
        tag,n=words[at:at+2];at+=2
        need(tag in lengths and n==lengths[tag] and at+n<=len(words),"known exact TLV payload width")
        rows.append((tag,words[at:at+n]));at+=n
    return rows


def parse_trace(raw,header,arm,budget):
    indices=support_indices();rows=unpack_trace(raw);cursor=0
    frames=[];bands={};base={};resolved={};pre={};post={};events=[]
    def take(tag):
        nonlocal cursor
        need(cursor<len(rows) and rows[cursor][0]==tag,"exact TLV stage order")
        payload=rows[cursor][1];cursor+=1;return payload
    def seam(after_frame):
        while cursor<len(rows) and rows[cursor][0] in (7,8):
            tag=rows[cursor][0];events.append((after_frame,tag,take(tag)))
    for frame in range(5):
        r=take(1);need(r[0]==frame and r[1]<=frame and 1<=r[2]<=2,"original frame/chunk/prefix association")
        vals=[word_float(x) for x in r[3:]]
        need(r[3:6]==[float_word(2),float_word(2),float_word(1.4)] and all(v>0 for v in vals[3:]),"fixed gate/exponent/ramp and effective beta")
        frames.append(r)
        for k in range(3):
            for j in indices[k]:
                b=take(2);need(b[:3]==[frame,k,j] and b[8] in (0,1),"complete frame/band/site partition")
                e,f,h,pw,used=map(word_float,b[3:8]);need(e>=0 and f>=0,"nonnegative E/F")
                trace_partition(b,arm)
                he,pe=weights64(e,f,vals[1],vals[2],k);close_weight(h,he);close_weight(pw,pe)
                if he==0:need(b[5]==0,"HardFloor zero weight")
                for x in b[9:]:word_float(x)
                bands[(frame,k,j)]=b
        for j in indices[3]:
            b=take(3);need(b[:2]==[frame,j],"complete mean-base source population")
            for x in b[2:]:word_float(x)
            base[(frame,j)]=b
        seam(frame)
    for c in range(4):
        for k in range(4):
            for j in indices[k]:
                r=take(4);need(r[:3]==[c,k,j] and r[7] in (0,1),"complete resolved population")
                for x in r[3:7]:word_float(x)
                resolved[(c,k,j)]=r
        for j in indices[0]:
            r=take(5);need(r[:2]==[c,j],"complete pre-hull population")
            for x in r[2:]:word_float(x)
            pre[(c,j)]=r
        for j in indices[0]:
            r=take(6);need(r[:2]==[c,j],"complete post-hull population");word_float(r[2]);post[(c,j)]=r
    need(cursor==len(rows),"no surplus unclassified TLV records")
    groups=[]
    for f,r in enumerate(frames):
        if r[1]==0:groups.append([])
        need(groups and r[1]==len(groups[-1]),"contiguous actual canonical chunk ordinal")
        groups[-1].append(f)
    expected_events=[];merged=len(groups[0])
    if len(groups)>1:expected_events.append((groups[0][-1],8,[0]))
    for n,g in enumerate(groups[1:],1):
        expected_events.append((g[-1],7,[merged,len(g)]));merged+=len(g)
        if n<len(groups)-1:expected_events.append((g[-1],8,[len(g)]))
    exact(events,expected_events,"actual source move/absorb/reset grouping")
    need(len(groups)<=5,"finite canonical chunks")
    need(header["calls"]["absorb"]==len(groups)-1 and header["calls"]["reset"]==len(groups)-1,"header exact chunk calls")
    need(header["observer_records"]==len(rows) and header["placebo_records"]==0,"on observer actual record count")
    need(len(raw)==4*(8064+4*(len(groups)-1)+3*(len(groups)-1)),"full independent TLV extent")
    worst_weight=0.;affected=0
    for (frame,k,j),b in bands.items():
        if b[8]==0 and word_float(b[6])>0:affected+=1
    def grouped(values):
        sums=[sum_f32(values[f] for f in g) for g in groups]
        result=sums[0]
        for x in sums[1:]:result=rounded_add(result,x)
        return result
    for (c,k,j),r in resolved.items():
        weights=[0. if k==3 else word_float(bands[(f,k,j)][7]) for f in range(5)]
        coefficients=[word_float(base[(f,j)][2+c] if k==3 else bands[(f,k,j)][9+c]) for f in range(5)]
        num=grouped([f32(w*v) for w,v in zip(weights,coefficients)])
        den=grouped(weights);usum=grouped(coefficients)
        need(r[3:6]==[float_word(num),float_word(den),float_word(usum)],"exact canonical rounded accumulators")
        out=f32(num/den) if den>0 else f32(usum*f32(1/5))
        need(r[6]==float_word(out) and r[7]==int(den<=0),"exact normalization or true fallback")
    # Independently memoized backward recursion; no producer forward calls.
    cache={};f64_errors=[]
    def collapse(c,k,x,y):
        key=(c,k,x,y)
        if key in cache:return cache[key]
        j=y*LEVEL_SIZES[k][0]+x;l=word_float(resolved[(c,k,j)][6])
        if k==3:cache[key]=l;return l
        width,height=LEVEL_SIZES[k+1]
        def horizontal(py):
            q=x//2
            if x%2:return f32(.5*f32(collapse(c,k+1,q,py)+collapse(c,k+1,min(q+1,width-1),py)))
            a,b,d=[collapse(c,k+1,xx,py) for xx in (max(0,q-1),q,min(width-1,q+1))]
            return f32(f32(f32(.125*a)+f32(.75*b))+f32(.125*d))
        q=y//2
        if y%2:v=f32(.5*f32(horizontal(q)+horizontal(min(q+1,height-1))))
        else:
            a,b,d=[horizontal(yy) for yy in (max(0,q-1),q,min(height-1,q+1))]
            v=f32(f32(f32(.125*a)+f32(.75*b))+f32(.125*d))
        out=f32(v+l);cache[key]=out;return out
    influence=support_contract()["collapse"]
    for (c,j),r in pre.items():
        x,y=j%150,j//150;observed=word_float(r[2]);actual=collapse(c,0,x,y)
        need(float_word(actual)==r[2],"bit-exact independent f32 collapse")
        terms=[float(w)*word_float(resolved[(c,k,yy*LEVEL_SIZES[k][0]+xx)][6])
               for k,table in enumerate(influence[(x,y)]) for (xx,yy),w in table.items()]
        real=math.fsum(terms);bound=(64*F32_U/(1-64*F32_U))*math.fsum(abs(t) for t in terms)+2**-140
        need(abs(observed-real)<=bound,"independent binary64 dyadic collapse bound")
        f64_errors.append(abs(observed-real))
        lo,hi=map(word_float,r[3:5]);need(lo<=hi,"ordered observed hull")
        need(post[(c,j)][2]==float_word(min(hi,max(lo,observed))),"exact actual hull clamp")
    budget.check()
    return dict(frames=frames,bands=bands,base=base,resolved=resolved,pre=pre,post=post,
                summary=dict(complete_records=len(rows),original_f32_words=len(raw)//4,chunk_frames=groups,
                exact_support_counts=[len(x) for x in indices],subfloor_rows=affected,
                maximum_binary64_collapse_difference=max(f64_errors),weight_rtol=WEIGHT_RTOL,
                weight_atol=WEIGHT_ATOL,scope="saved E/F and beta are actual operands, not independently recomputed image/noise estimates"))


def header_check(header,case,raw):
    need(header["schema"]=="m194h-core-trace-v1" and header["format"]=="little-endian-u32-TLV-original-f32-bits"
         and header["format_version"]==1 and header["production"] is True,"actual trace format")
    exact(header["quad_sizes"],[list(x) for x in LEVEL_SIZES],"quad band sizes")
    exact(header["native_crop_offset"],list(ORIGIN_NATIVE),"trace native crop")
    exact(header["native_sites"],[list(x) for x in SITES_NATIVE],"fixed native sites")
    exact(header["cfa_plane_order"],["R","G1","G2","B"],"CFA plane order")
    exact(header["support_indices"],support_indices(),"full independent support sets")
    need(header["arm"]==case["arm"] and header["observation"]==case["observation"],"trace case association")
    calls=header["calls"];need(set(calls)=={"frames","bands","bases","resolved","pre_hull","post_hull","absorb","reset"},"closed trace counts")
    for k,expected in dict(frames=5,bands=15,bases=5,resolved=16,pre_hull=4,post_hull=4).items():
        need(type(calls[k]) is int and calls[k]==expected,"complete actual core calls")
    need(header["status"]=="COMPLETE_CORE_CALLS_UNVERIFIED","complete core trace disposition")
    integer(calls["absorb"],0,4,"finite absorbs");integer(calls["reset"],0,4,"finite resets")
    need(calls["absorb"]==calls["reset"],"canonical production reset count")
    integer(header["observer_records"],0,1000,"observer count");integer(header["placebo_records"],0,1000,"placebo count")
    need(type(header["word_count"]) is int and header["word_count"]*4==len(raw) and header["word_cap"]==32768,"exact trace binary extent")
    obs=case["observation"]
    if obs!="on":
        need(raw==b"" and header["observer_records"]==0,"canonical empty off/placebo payload")
        expected=752+calls["absorb"]+calls["reset"] if obs=="placebo" else 0
        need(header["placebo_records"]==expected,"actual placebo traversal count")


def red_output_from_trace(trace,site,wb):
    x,y=(site[i]-ORIGIN_NATIVE[i] for i in range(2))
    def sample(nx,ny):
        c,qx,qy=native_to_cfa((nx,ny));v=word_float(trace["post"][(c,qy*150+qx)][2])
        gain=wb[(0,1,1,2)[c]]
        return f32(f32(max(v,0.)*gain)/14848.)
    if x%2==y%2==0:rgb=sample(x,y)
    else:
        # Traverse signed MHC taps in the consumer's fixed order, preserving f32 rounding.
        offsets=((0,0,6.),(-1,-1,2.),(1,-1,2.),(-1,1,2.),(1,1,2.),
                 (-2,0,-1.5),(2,0,-1.5),(0,-2,-1.5),(0,2,-1.5))
        rgb=f32(sum_f32(f32(w*sample(x+dx,y+dy)) for dx,dy,w in offsets)*.125)
    code=int(f32(f32(min(1.,max(0.,rgb))*65535.)+.5))
    return code


def trace_partition(b,arm):
    e,f,pw=map(word_float,(b[3],b[4],b[6]))
    need(b[8] in (0,1),"typed trace classification word")
    above=above_floor(e,f)
    need(b[8]==int(above),"actual bit equals independent strict partition")
    wanted=b[5] if arm=="H" else b[6] if arm=="P" or above else 0
    need(b[7]==wanted,"exact actual used-weight intervention")
    check_partition(e,f,bool(b[8]),pw,pw if above else 0.)
    return above


def metadata_faults(trace,header,raw):
    rows=unpack_trace(raw);b=next(r[1] for r in rows if r[0]==2)
    trace_partition(b,"P0")
    mutant=list(b);mutant[8]^=1
    failures=[]
    support=[[[j%LEVEL_SIZES[k][0],j//LEVEL_SIZES[k][0]] for j in table] for k,table in enumerate(header["support_indices"])]
    bad=[[list(x) for x in table] for table in support]
    need(collapse_influence((96,48))[0][(96,48)]==1 and red_mhc_taps(SITES_NATIVE[0])[(0,96,48)]==1,
         "selected primary red has nonzero destroyed dependency")
    bad[0].remove([96,48])
    for name,call in (("flipped-actual-classification-word",lambda:trace_partition(mutant,"P0")),
                      ("missing-primary-red-nonzero-support",lambda:check_support(bad)),
                      ("double-actual-positive-P-weight",lambda:close_weight(word_float(b[6])*2,word_float(b[6])))):
        try:call()
        except ContractError as exc:failures.append(dict(id=name,rejected=True,reason=str(exc)))
        else:need(False,"independent actual-value destroyer did not reject")
    restored=list(mutant);restored[8]^=1;exact(restored,b,"restored whole actual band row")
    trace_partition(restored,"P0");check_support(support)
    pack=lambda row:struct.pack("<"+"I"*len(row),*row)
    return dict(actual_row=b[:9],faults=failures,restored_partition=True,restored_support=True,
                original_row_sha256=digest(pack(b)),mutated_row_sha256=digest(pack(mutant)),
                restored_row_sha256=digest(pack(restored)),original_trace_sha256=digest(raw))


OLD_PLANS = {
 1:dict(path="experiments/m194g-larger-pupil/production-matrix-1/case-01-plan.json",bytes=75482,sha256="49f445472b5ed3acc6d4204d06a18f26f2362a0e66ddaad8240fd10aa7900475"),
 0:dict(path="experiments/m194g-larger-pupil/production-matrix-1/case-00-plan.json",bytes=75476,sha256="67bf4d3a57b22d5815a16aac1274c3a34df7294185e3ed3e382812b9329ace31"),
 14:dict(path="experiments/m194g-larger-pupil/production-matrix-1/case-14-plan.json",bytes=75475,sha256="a63ad116c0a567f16724683dd3e0bb84fb50bdefdb6b2602bd957613ab6a01a7"),
 15:dict(path="experiments/m194g-larger-pupil/production-matrix-1/case-15-plan.json",bytes=75469,sha256="0a6d2e0369c0d5314c6e44e9b0b7e425773b7330341ec50c47554c05bc4d30ec")}
MATRIX=dict(path="experiments/m194g-larger-pupil/production-matrix-1/run-index.json",bytes=66801,
            sha256="03e7ffe9028cca5d56266603db09fbadd3f7f3cc19e95db609007a96914d55ca")
ENVIRONMENT=dict(RAYON_NUM_THREADS="2",STREHL_DEFECT="off",STREHL_FIX_CA="off",STREHL_FULLRES_GATHER="1",STREHL_PYRAMID_WORKERS="2")


def old_readers(files):
    # Reuse only the already admitted bounded decoder and target functions.
    # Never import the old executable, its main, its budget, or its private controls.
    source=files.read(OLD_READER,128*KIB)
    tree=ast.parse(source);names={"decode_tiff","target_array"}
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    need({node.name for node in selected}==names,"exact two-function old decoder closure")
    scope=dict(np=NP,struct=struct,ast=ast,need=need,digest=digest,exact=exact)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(ROOT/OLD_READER["path"]),"exec"),scope)
    return scope["decode_tiff"],scope["target_array"]


def expected_case(index):
    seed,arm,observation=expected_case_keys()[index]
    return dict(ordinal=index,seed=seed,arm=arm,observation=observation,
                output_directory=f"experiments/m194h-pedestal-causality/subject-1/case-{index:02}")


def grant_check(files,ref):
    g=files.json(ref,MIB)
    need(set(g)=={"schema","source_bindings","noise_admission","matrix_index","quality_verification","binary","commands","cases"}
         and g["schema"]=="m194h-pedestal-causality-release-v1","exact eight-key subject grant")
    exact(g["cases"],[expected_case(i) for i in range(12)],"fixed twelve release cases")
    need(same_ref(g["matrix_index"],MATRIX) and same_ref(g["quality_verification"],OLD_RESULT),"fixed old admitted results")
    sources(files,g["source_bindings"])
    for name in ("core-hook.rs","production-bridge.rs","component-controls.rs","preregister.md"):
        need((HERE/name).relative_to(ROOT).as_posix() in g["source_bindings"],"producer source grant closure")
    files.read(g["binary"],64*MIB,retain=False)
    need(type(g["commands"]) is list and len(g["commands"])==1,"one fixed case command")
    cmd=g["commands"][0]
    need(len(cmd)==6 and path_identity(cmd[0])==path_identity(g["binary"]["path"])
         and cmd[1:]==["--exact",CLI_TEST,"--ignored","--test-threads=1","--nocapture"],"fixed real consumer test command")
    previous=files.json(OLD_RESULT,512*KIB)
    need(previous["status"]=="PASS_INDEPENDENT_FIXED_DIAGNOSTICS_ONLY" and previous["error"] is None,"prior independent diagnostic disposition")
    matrix=files.json(MATRIX,128*KIB)
    need(len(matrix["entries"])==38,"unchanged archived matrix population")
    old={}
    for k,r in OLD_PLANS.items():
        need(same_ref(r,matrix["entries"][k]["plan"]),"old plan actual matrix association")
        old[k]=files.json(r,128*KIB)
    return g,matrix,old


def driver_controls(files,stage):
    ref=stage["result"].get("metadata_controls")
    if ref is None:return dict(complete=False,scope="no linked completed metadata-control receipt; attempts may exist")
    value=files.json(ref,16*KIB)
    ids=("typed-job-positive","wrong-total","negative-user","bool-active","combined-cpu-positive",
         "combined-cpu-overrun","json-finite-overflow","json-duplicate","terminal-overflow-preserves-prior","same-slot-restoration")
    errors=(None,"Job CPU components","typed Job accounting","typed Job accounting",None,
            "reserved stage CPU","nonfinite JSON","duplicate JSON key","terminal encoding capacity",None)
    need(value["schema"]=="m194h-driver-metadata-controls-v1","driver control schema")
    rows=value["rows"];need(type(rows) is list and len(rows)<=10,"driver metadata control prefix")
    for i,row in enumerate(rows):need(row==dict(id=ids[i],passed=True,error=errors[i]),"actual injected control disposition/reason")
    full=len(rows)==10 and value.get("status")=="PASS_METADATA_SEAMS_ONLY"
    if full:
        fixture=value["fixture"];need(same_ref(fixture["original"],fixture["restored"]),"actual publication restoration")
        raw=files.read(fixture["restored"],8*KIB)
        exact(strict(raw),dict(status="POSITIVE_METADATA_FIXTURE"),"actual restored slot contents")
        need(fixture["refused_bytes_sha256"]!=fixture["restored"]["sha256"],"distinct refused metadata contents")
    return dict(ref=ref,complete=full,count=len(rows),scope="injected Job/arithmetic and actual metadata publication; not independent OS commissioning")


def check_plan(value,case,grant_ref,grant,matrix,old):
    need(set(value)=={"schema","case","authority","original_consumer_plan","experiment","historical_endpoint"}
         and value["schema"]=="m194h-pedestal-plan-v1","closed case plan")
    exact(value["case"],case,"actual case plan identity")
    need(same_ref(value["authority"]["grant"],grant_ref),"case authority exact grant")
    exact(value["authority"]["environment"],ENVIRONMENT,"unset demosaic/restoration and fixed allowed environment")
    ordinal=0 if case["seed"] is None else 15 if case["arm"]=="H" else 14
    current=value["original_consumer_plan"];prior=old[1 if case["seed"] is None and case["arm"]!="H" else ordinal]
    need(set(current)==set(prior),"unchanged original consumer plan fields")
    for key in current:
        if key not in ("build","observer"):
            exact(current[key],prior[key],"original consumer plan unchanged at "+key)
    exact(current["observer"],dict(mode="count",excludes_planning_reads=True,excludes_raw_prologue=True),"same Source Count in every arm")
    need(current["build"]["bytes"]==grant["binary"]["bytes"] and current["build"]["sha256"]==grant["binary"]["sha256"],"actual built consumer binary")
    c=current["config"]
    need(c["space"]=="CameraLinear" and c["demosaic"]=="MHC" and c["exposure_stops"]==0 and c["auto_exposure"] is False
         and c["restoration"]=="unset" and current["normalization"]["second_black_subtraction"] is False,"exact final writer consumer")
    exact(current["geometry"]["canonical_native_offset"],[10,8],"native origin")
    exact(current["geometry"]["output_native"],[300,226],"native dimensions")
    exact(value["experiment"],dict(arm=case["arm"],observation=case["observation"],cutoff_only=case["arm"]=="P0",
          zero_condition="E<=F before actual accumulate_level; positive-excess P weights unchanged",frame_indices=list(FRAME_IDS)),"exact single intervention")
    endpoint=value["historical_endpoint"];entry=matrix["entries"][ordinal]
    need(endpoint["ordinal"]==ordinal and endpoint["required_identity"] is (case["seed"] is None or case["arm"]!="P0")
         and same_ref(endpoint["receipt"],entry["receipt"]) and same_ref(endpoint["tiff"],entry["tiff"]),"historical endpoint role")
    return current


def case_read(files,index,grant_ref,grant,matrix,old,decode,budget):
    case=expected_case(index);directory=ROOT/case["output_directory"]
    if not directory.exists():return dict(summary=dict(case=case,complete=False,status="UNVISITED")),None,None
    names={p.name for p in directory.iterdir()};need(names<=set(CASE_CAPS),"closed actual case artifact population")
    refs={name:files.actual(directory/name,CASE_CAPS[name],empty=name=="trace.bin") for name in sorted(names)}
    raw={name:files.read(r,CASE_CAPS[name],empty=name=="trace.bin",role_path=directory/name) for name,r in refs.items()}
    if "result.json" not in raw:return dict(summary=dict(case=case,complete=False,status="MISSING_CANONICAL",retained=refs)),None,None
    result=strict(raw["result.json"])
    need(result["schema"]=="m194h-pedestal-case-v1" and result["case"]==case,"actual canonical case identity")
    need(same_ref(result["authority"]["grant"],grant_ref),"canonical grant association")
    summary=dict(case=case,complete=False,status=result["status"],retained=refs)
    if result["status"]!="COMPLETE_CASE_UNVERIFIED" or result["science_complete"] is not True:
        err=encoded(result.get("error"));summary["error_evidence"]=dict(bytes=len(err),sha256=digest(err),scope="full error retained in exact canonical FileRef")
        return dict(summary=summary),None,None
    need({"plan.json","trace.bin","trace.json","output.tif"}<=names,"complete case retained files")
    need(same_ref(result["plan"],refs["plan.json"]) and same_ref(result["trace"],refs["trace.json"]),"canonical same actual plan/trace")
    plan=strict(raw["plan.json"]);original=check_plan(plan,case,grant_ref,grant,matrix,old)
    exact(result["authority"],plan["authority"],"whole plan/canonical authority")
    exact(result["historical_endpoint"],plan["historical_endpoint"],"whole endpoint association")
    need(result["inputs_unchanged"] is True and result["source_decode_counts"]==[1]*5 and result["source_hook_calls"]==5,"actual fixed Source Count witnesses")
    header=strict(raw["trace.json"])
    need(same_ref(header["binary"],refs["trace.bin"]),"trace exact binary evidence including empty")
    header_check(header,case,raw["trace.bin"])
    trace=parse_trace(raw["trace.bin"],header,case["arm"],budget) if case["observation"]=="on" else None
    pixels,proof=decode(raw["output.tif"],refs["output.tif"]["sha256"],budget)
    need(proof["shape"]==[226,300,3],"actual consumer TIFF shape")
    output=result["output"]
    need(output["bytes"]==refs["output.tif"]["bytes"] and output["sha256"]==refs["output.tif"]["sha256"]
         and output["pixel_sha256_le"]==proof["pixel_sha256"],"whole actual TIFF and independent pixel identity")
    need(output["width"]==300 and output["height"]==226 and output["channels"]==3,"canonical image dimensions")
    endpoint=plan["historical_endpoint"]
    eraw=files.json(endpoint["receipt"],128*KIB)
    exact(endpoint["output"],eraw["output"],"complete archived output metadata")
    if endpoint["required_identity"]:
        for key in ("bytes","sha256","pixel_sha256_le","width","height","channels","sample_type","software"):
            exact(output[key],endpoint["output"][key],"archived whole TIFF equality "+key)
    prediction=[]
    if trace is not None:
        for site in SITES_NATIVE:
            code=red_output_from_trace(trace,site,original["wb_f32"])
            actual=int(pixels[site[1]-8,site[0]-10,0])
            need(code==actual,"exact traced CFA/MHC/CameraLinear red consumer code")
            prediction.append(dict(native=list(site),predicted_u16=code,actual_u16=actual))
    summary.update(complete=True,source_count=[1]*5,source_hooks=5,trace_summary=trace["summary"] if trace else None,
                   observed_calls=header["calls"],observer_records=header["observer_records"],placebo_records=header["placebo_records"],
                   decoded=proof,consumer_prediction=prediction,archived_whole_identity=endpoint["required_identity"])
    return dict(summary=summary,header=header,raw_trace=raw["trace.bin"],original_plan=original),pixels,trace


def cross_arm(traces,cases):
    h,p,p0=(traces[i] for i in (1,4,7));need(all(x is not None for x in (h,p,p0)),"all three actual on traces")
    for other in (p,p0):
        exact(h["frames"],other["frames"],"same actual ordered frame/beta/config/chunk operands")
        need(h["base"]==other["base"],"same whole retained mean-base operands")
        for key,first in h["bands"].items():
            second=other["bands"][key]
            need(first[:7]+first[8:]==second[:7]+second[8:],"same E/F/H/P/classification/coefficient inputs; only used weight differs")
        for key,first in h["pre"].items():need(first[3:]==other["pre"][key][3:],"same retained all-input hull bounds")
    observer=[]
    for first in (0,3,6):
        refs=[cases[i]["summary"]["retained"]["output.tif"] for i in range(first,first+3)]
        need(len({(r["bytes"],r["sha256"]) for r in refs})==1,"actual whole output off/on/placebo identity")
        observer.append(dict(arm=MODES[first//3],off=refs[0],on=refs[1],placebo=refs[2],identical=True))
    primary=collapse_influence((96,48));partition=[]
    for k in range(3):
        for (x,y),coefficient in primary[k].items():
            j=y*LEVEL_SIZES[k][0]+x
            rows=[p["bands"][(f,k,j)] for f in FRAME_IDS]
            sub=[f for f,b in enumerate(rows) if b[8]==0]
            total=math.fsum(word_float(b[6]) for b in rows)
            removed=math.fsum(word_float(rows[f][6]) for f in sub)
            partition.append(dict(level=k,index=j,inverse_coefficient=[coefficient.numerator,coefficient.denominator],
                below_or_equal_frames=sub,pedestal_weight_total=total,removed_weight=removed,
                removed_fraction=removed/total,resolved_H=word_float(h["resolved"][(0,k,j)][6]),
                resolved_P=word_float(p["resolved"][(0,k,j)][6]),resolved_P0=word_float(p0["resolved"][(0,k,j)][6]),
                p0_mean_fallback=bool(p0["resolved"][(0,k,j)][7])))
    stages=[]
    for site in SITES_NATIVE:
        taps=red_mhc_taps(site)
        for arm,t in zip(MODES,(h,p,p0),strict=True):
            rows=[]
            for (plane,x,y),weight in taps.items():
                j=y*150+x;r=t["pre"][(plane,j)]
                rows.append(dict(plane=plane,quad=[x,y],signed_mhc_coefficient=[weight.numerator,weight.denominator],
                    pre=word_float(r[2]),lo=word_float(r[3]),hi=word_float(r[4]),post=word_float(t["post"][(plane,j)][2])))
            stages.append(dict(site=list(site),arm=arm,cfa_hull_operands=rows))
    return dict(observer_identity=observer,primary_inverse_support_partition=partition,
                primary_has_actual_removed_mass=any(r["removed_weight"]>0 for r in partition),
                selected_consumer_hull_and_signed_mhc=stages,
                independent_faults=metadata_faults(p0,cases[7]["header"],cases[7]["raw_trace"]))


def diagnostics(pixels,target,budget):
    # The fixed flat scene's common ideal is literal12000e * CFA factor * injected gain * WB.
    # The admitted target file is authenticated/decoded, but its textured scene is not a flat ideal.
    need(target.shape==(240,320),"common target decoder shape")
    factors=(.75*1.3333333730697632,1.,.6*1.6666666269302368)
    ideal=[12000*.25*x for x in factors]
    dn=14848/65535
    rows=[];site_rows=[]
    for index,image in enumerate(pixels):
        channels=[]
        for channel in range(3):
            window=image[104-8:136-8,104-10:216-10,channel]
            errors=[float(x)*dn-ideal[channel] for x in window.flat]
            need(len(errors)==3584 and all(math.isfinite(x) for x in errors),"fixed whole RGB window")
            channels.append(dict(channel=channel,count=len(errors),bias_dn=math.fsum(errors)/len(errors),
                mse_dn2=math.fsum(x*x for x in errors)/len(errors),maximum_absolute_error_dn=max(map(abs,errors)),
                absolute_error_above_10dn=sum(abs(x)>10 for x in errors)))
        rows.append(dict(case=index,window_native=[104,104,216,136],channels=channels))
        for site in SITES_NATIVE:
            code=int(image[site[1]-8,site[0]-10,0]);error=code*dn-ideal[0]
            site_rows.append(dict(case=index,native=list(site),red_code=code,red_dn=code*dn,ideal_red_dn=ideal[0],signed_error_dn=error,absolute_error_dn=abs(error)))
        budget.check()
    comparisons=[];paired_window=[]
    for left,right,label in ((0,3,"H-to-P"),(3,6,"P-to-P0"),(0,6,"H-to-P0")):
        for channel in range(3):
            left_values=pixels[left][96:128,94:206,channel].flat
            right_values=pixels[right][96:128,94:206,channel].flat
            movement=[abs(float(b)*dn-ideal[channel])-abs(float(a)*dn-ideal[channel])
                      for a,b in zip(left_values,right_values,strict=True)]
            need(len(movement)==3584,"full paired fixed-window population")
            paired_window.append(dict(comparison=label,channel=channel,count=len(movement),
                improvement_gt10dn=sum(v < -10 for v in movement),worsening_gt10dn=sum(v > 10 for v in movement),
                unchanged=sum(v==0 for v in movement),maximum_worsening_dn=max(movement),maximum_improvement_dn=-min(movement)))
        for site in SITES_NATIVE:
            a=next(r for r in site_rows if r["case"]==left and r["native"]==list(site))
            b=next(r for r in site_rows if r["case"]==right and r["native"]==list(site))
            comparisons.append(dict(comparison=label,native=list(site),movement_dn=b["red_dn"]-a["red_dn"],
                absolute_error_change_dn=b["absolute_error_dn"]-a["absolute_error_dn"]))
    return dict(flat_ideal_rgb_dn=ideal,fixed_window=rows,sites=site_rows,comparisons=comparisons,paired_window=paired_window,
        scope="one previously selected noisy realization and one noise-free null; no repeat variance, uncertainty interval or new quality acceptance threshold",
        failure_direction="MSE can improve by flattening real detail; this flat explanatory fixture supports a local mechanism only, not a texture or shipping-quality claim",
        authenticated_textured_target_decoder_reference=IDEAL,flat_ideal_source="original M194g literal flat12000e times fixed gain/CFA/WB; scalar.npy values are not this flat ideal")



def old_metric_anchors(files,diagnostic):
    prior=files.json(OLD_RESULT,512*KIB)
    score=files.json(prior["score"],512*KIB)
    ref=dict(score["scene_results"][0]);ref["path"]="experiments/m194g-larger-pupil/independent-quality-score-1/"+ref["path"]
    flat=files.json(ref,256*KIB)
    need(flat["scene"]=="flat","same pre-existing common flat readout")
    checks=[]
    def near(a,b,label):
        need(abs(a-b)<=1e-8,"original verified metric anchor: "+label)
    for channel,name in enumerate(("R","G","B")):
        sparse=[r for r in flat["sparse"] if r["seed"]==743 and r["region"]=="window" and r["channel"]==name]
        need(len(sparse)==1,"one fixed old sparse anchor")
        actual=next(r for r in diagnostic["paired_window"] if r["comparison"]=="H-to-P" and r["channel"]==channel)
        for oldkey,newkey in (("improvement_gt10_dn_count","improvement_gt10dn"),("worsening_gt10_dn_count","worsening_gt10dn")):
            need(sparse[0][oldkey]==actual[newkey],"exact old paired sparse window count")
        for index,mode in ((0,"hard-floor"),(3,"floor-pedestal-v1")):
            previous=[r for r in flat["individual_errors"] if r["seed"]==743 and r["region"]=="window" and r["channel"]==name and r["reference"]=="ideal" and r["mode"]==mode]
            need(len(previous)==1,"one fixed old individual anchor")
            current=diagnostic["fixed_window"][index]["channels"][channel]
            for key in ("bias_dn","mse_dn2"):near(current[key],previous[0][key],key)
        checks.append(dict(channel=name,improvement_gt10dn=actual["improvement_gt10dn"],worsening_gt10dn=actual["worsening_gt10dn"]))
    red=next(r for r in flat["sparse"] if r["seed"]==743 and r["region"]=="window" and r["channel"]=="R")
    for role,site in (("maximum_worsening_site",SITES_NATIVE[0]),("before_worst_site",SITES_NATIVE[1])):
        old=red[role];need(old["native_xy"]==list(site),"fixed original selected-site discovery association")
        for index,prefix in ((0,"before"),(3,"after")):
            current=next(r for r in diagnostic["sites"] if r["case"]==index and r["native"]==list(site))
            near(current["red_dn"],old[prefix+"_dn"],"selected red DN")
            near(current["signed_error_dn"],old[prefix+"_signed_error_dn"],"selected signed error")
            near(current["ideal_red_dn"],old["target_dn"],"same common ideal")
    return dict(prior_independent_result=OLD_RESULT,score=prior["score"],flat_readout=ref,
                exact_sparse_counts=checks,selected_sites_match=True,scalar_tolerance_dn_or_dn2=1e-8,
                scope="fixed previously verified H/P endpoints and same common flat ideal; no new reference selection")


def numpy_source_observation(budget):
    path=Path(NP.__file__);before=path.stat();identity=object_identity(before)
    need(path.is_absolute() and stat.S_ISREG(before.st_mode) and not getattr(before,"st_file_attributes",0)&0x400
         and 0<before.st_size<=256*KIB,"bounded ordinary NumPy source observation")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());handle_identity=object_identity(opened)
        need(shared_identity(opened)==shared_identity(before),"NumPy source shared open identity")
        raw=stream.read(256*KIB+1)
        need(object_identity(os.fstat(stream.fileno()))==handle_identity,"NumPy source final handle")
    need(object_identity(path.stat())==identity and len(raw)==before.st_size,"stable NumPy source observation")
    budget.read_bytes+=len(raw);budget.check()
    return dict(numpy=NP.__version__,python=sys.version,isolated=bool(sys.flags.isolated),
        module_source=dict(path=str(path),bytes=len(raw),sha256=digest(raw)),
        scope="observed imported NumPy initializer/version; no complete runtime/cache/DLL or execution-provenance claim")

def inventory(files,roots):
    rows=[];total=0
    for root,cap in roots:
        if not root.exists():continue
        # os.walk includes hidden/system names; reject links before descending.
        for directory,dirs,names in os.walk(root,followlinks=False):
            path_identity(directory)
            for name in dirs:path_identity(str(Path(directory)/name))
            for name in names:
                p=Path(directory)/name;path_identity(str(p));need(len(p.relative_to(ROOT).as_posix())<=512,"finite inventory path width");s=p.stat()
                need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,"complete owned file inventory")
                total+=s.st_size;need(total<=160*MIB,"bounded all-stage physical inventory")
                rows.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=s.st_size))
                need(len(rows)<=256,"finite artifact count")
                files.budget.check()
        need(sum(r["bytes"] for r in rows if path_identity(r["path"]).is_relative_to(root))<=cap,"stage physical extent cap")
    return dict(files=len(rows),bytes=total,entries=rows,scope="all owned retained files including hidden/system; build scratch excluded and separately declared")


def main():
    global NP
    parser=argparse.ArgumentParser()
    for key in ("release","release-sha256","source-sha256","output"):parser.add_argument("--"+key,required=True)
    args=parser.parse_args();budget=Budget();files=Files(budget);out=None;final=None
    try:
        self_ref=files.actual(SELF,128*KIB);need(self_ref["sha256"]==args.source_sha256,"released independent source")
        release_ref=files.actual(args.release,MIB);need(release_ref["sha256"]==args.release_sha256,"external checker release hash")
        release=files.json(release_ref,MIB)
        need(set(release)=={"schema","source_bindings","render","subject_grant","command"}
             and release["schema"]=="m194h-independent-check-release-v1","closed five-key checker release")
        command=[args.release_sha256 if v=="ACTUAL_RELEASE_SHA256" else args.source_sha256 if v=="ACTUAL_SOURCE_SHA256" else v for v in release["command"]]
        need(sys.orig_argv==command and command[1:3]==["-I","-B"] and path_identity(command[3])==SELF,"actual isolated checker argv")
        source_summary=sources(files,release["source_bindings"])
        own=SELF.relative_to(ROOT).as_posix();need(same_ref(self_ref,dict(path=own,**release["source_bindings"][own])),"bound checker source identity")
        for name in ("independent-verification-design.md","independent-checker-source-review.md"):
            need((HERE/name).relative_to(ROOT).as_posix() in release["source_bindings"],"independent source/protocol review closure")
        out=Output(args.output)
        out.phase("source-and-release",dict(release=release_ref,source=self_ref,sources=source_summary))
        grant,matrix,old=grant_check(files,release["subject_grant"])
        render=stage_bundle(files,release["render"],"render")
        need(same_ref(render["release"]["subject_grant"],release["subject_grant"]),"stage exact science grant")
        prerequisite=render["release"]["prerequisites"]
        need(set(prerequisite)=={"build","components"},"both original stage prerequisites")
        build=stage_bundle(files,prerequisite["build"],"build")
        components=stage_bundle(files,prerequisite["components"],"components")
        need(components["release"]["prerequisites"].get("build")==prerequisite["build"],"same actual build prerequisite")
        stages=(build,components,render)
        control=[driver_controls(files,stage) for stage in stages]
        out.phase("owned-stages",dict(stages=[s["summary"] for s in stages],metadata_controls=control))
        component_log=components["children"][0]["log"] if components["children"] else b""
        markers=[component_log.count(("M194H_COMPONENT_PASS "+name).encode()) for name in COMPONENT_IDS]
        component_complete=(components["complete"] and markers==[1]*7 and
            b"M194H_COMPONENT_COMPLETE 26-merges 130-frame-folds plus-one-rejected-entry" in component_log and
            b"test result: ok. 1 passed; 0 failed; 0 ignored;" in component_log)
        out.phase("actual-component-controls",dict(complete=component_complete,marker_counts=markers,
                  ids=list(COMPONENT_IDS),scope="actual compiled private component outputs; no checker rerun"))
        # Existing admitted data interfaces; import one numerical library only after authority.
        import numpy as np
        NP=np
        runtime_observation=numpy_source_observation(budget)
        out.phase("ordinary-numerical-library",runtime_observation)
        decode,target_reader=old_readers(files)
        target=target_reader(files.read(IDEAL,MIB),budget)
        archive={}
        for arm,ref in ARCHIVED_TIFFS.items():
            archive[arm],proof=decode(files.read(ref,512*KIB),ref["sha256"],budget)
            need(proof["shape"]==[226,300,3],"archived endpoint decoder shape")
        cases=[];pixels=[];traces=[]
        for i in range(12):
            c,image,trace=case_read(files,i,release["subject_grant"],grant,matrix,old,decode,budget)
            cases.append(c);pixels.append(image);traces.append(trace)
            out.phase("actual-case-"+str(i),c["summary"])
        full_science=all(c["summary"]["complete"] for c in cases)
        check_case_population([(c["summary"]["case"]["seed"],c["summary"]["case"]["arm"],c["summary"]["case"]["observation"]) for c in cases],full_science)
        science=None
        if full_science:
            for i in range(12):
                case=expected_case(i)
                if case["seed"] is None or case["arm"]!="P0":
                    expected=archive["noise-free" if case["seed"] is None else case["arm"]]
                    need(NP.array_equal(pixels[i],expected),"independent archived whole decoded endpoint")
            science=dict(trace_consumer=cross_arm(traces,cases),diagnostics=diagnostics(pixels,target,budget))
            science["original_metric_anchors"]=old_metric_anchors(files,science["diagnostics"])
            out.phase("independent-consumer-science",science)
        files.finish()
        inv=inventory(files,[(HERE/"build-1",128*MIB),(HERE/"components-1",2*MIB),(SUBJECT,16*MIB)])
        complete=bool(full_science and all(s["complete"] for s in stages) and all(c["complete"] for c in control) and component_complete)
        budget.check()
        final=dict(schema=SCHEMA,status="PASS_INDEPENDENT_SAVED_CONSUMER_CHECK_ONLY" if complete else "VERIFIED_INCOMPLETE_SAVED_PREFIX",
            independent_complete=complete,subject_complete=complete,verified_science_complete=full_science,quality_go=False,
            release=release_ref,source=self_ref,stages=[s["summary"] for s in stages],cases=[c["summary"] for c in cases],
            science=science,phases=out.phases,inventory=inv,own_sample=budget.receipt(),publication_allowance=PUBLICATION,
            limits=LIMITS,numerical_runtime=runtime_observation,error=None,scope="fixed explanatory consumer experiment; no render/RAW/model/source numerical execution; whole checker exit/wall and OS memory require independent outer")
        out.write("result.json",final,MIB)
        sys.stdout.buffer.write(encoded(final));return 0 if complete else 1
    except BaseException as exc:
        full=traceback.format_exc().encode("utf-8");error=dict(type=type(exc).__name__,full_bytes=len(full),full_sha256=digest(full),suffix=full[-4096:].decode("utf-8","replace"))
        if len(encoded(error))>8*KIB:error.pop("suffix")
        final=dict(schema=SCHEMA,status="INCOMPLETE_INDEPENDENT_CHECK",independent_complete=False,subject_complete=False,
            quality_go=False,error=error,phases=out.phases if out else [],own_sample=budget.receipt(),limits=LIMITS)
        if out and not (out.root/"result.json").exists():
            try:out.write("result.json",final,MIB)
            except Exception:pass
        sys.stderr.buffer.write(encoded(error));sys.stdout.buffer.write(encoded(final));return 1


if __name__=="__main__":
    raise SystemExit(main())
