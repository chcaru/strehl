"""Independent actual TIFF/batch-statistic check; never issues a quality GO."""
import time
START_CPU, START_WALL = time.process_time(), time.monotonic()
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import traceback
import weakref

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DESIGN = HERE / "independent-quality-result-check-design.md"
SEEDS = (701, 709, 719, 727, 733, 739, 743, 751)
MODES = ("hard-floor", "floor-pedestal-v1")
CHANNELS = "RGB"
SCORE_SHA = "7477f1553ac53dc87d554cee04117c536f7e5d3476b97ce9fde8f5d3b42b95df"
DN = 14848.0 / 65535.0
np = None


class Refusal(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique(pairs):
    out = {}
    for k, v in pairs:
        need(k not in out, "duplicate JSON key")
        out[k] = v
    return out


def json_bytes(raw):
    def bad(value):
        raise Refusal("nonfinite JSON token " + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=bad)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def binding(path):
    h, n = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            h.update(block); n += len(block)
    return dict(sha256=h.hexdigest(), bytes=n)


def exact(a, b, label):
    need(canonical(a) == canonical(b), label)


class Budget:
    def __init__(self):
        self.owners, self.peak, self.output, self.decodes = {}, 0, 0, 0

    def check(self):
        need(time.process_time() - START_CPU <= 120, "CPU budget")
        need(time.monotonic() - START_WALL <= 240, "wall budget")
        self.owners = {k: v for k, v in self.owners.items() if v[0]() is not None}
        live = sum(v[1] for v in self.owners.values())
        self.peak = max(self.peak, live)
        need(live <= 32 << 20, "named ndarray budget")
        need(self.output <= 32 << 20, "output budget")
        need(self.decodes <= 96, "decode budget")

    def watch(self, *arrays):
        for a in arrays:
            if not isinstance(a, np.ndarray):
                continue
            root = a
            while isinstance(root.base, np.ndarray):
                root = root.base
            self.owners[id(root)] = (weakref.ref(root), root.nbytes)
        self.check()
        return arrays[0] if len(arrays) == 1 else arrays

    def receipt(self):
        self.check()
        return dict(cpu_seconds=time.process_time()-START_CPU, wall_seconds=time.monotonic()-START_WALL,
                    peak_named_ndarray_bytes=self.peak, output_bytes=self.output, tiff_decodes=self.decodes,
                    scope="live registered backing ndarrays; no repeat image volume; not process RSS")


class Files:
    def __init__(self, budget):
        self.budget, self.seen = budget, {}

    def path(self, ref, base=ROOT):
        need(type(ref) is dict and set(ref) in ({"path", "sha256", "bytes"},
                                               {"path", "sha256", "bytes", "shape", "dtype"}), "FileRef keys")
        p = ref["path"]
        need(type(p) is str and p and "\\" not in p and not Path(p).is_absolute()
             and all(v not in ("", ".", "..") for v in p.split("/")), "relative reference path")
        resolved = (base / p).resolve(strict=True)
        need(resolved.is_relative_to(ROOT) and resolved.is_file(), "reference containment")
        need(type(ref["bytes"]) is int and ref["bytes"] > 0 and type(ref["sha256"]) is str
             and len(ref["sha256"]) == 64 and all(c in "0123456789abcdef" for c in ref["sha256"]), "reference types")
        return resolved

    def track(self, path, wanted):
        key = path.relative_to(ROOT).as_posix()
        if key in self.seen:
            exact(self.seen[key], wanted, "repeated input binding")
        exact(binding(path), wanted, "actual input bytes")
        self.seen[key] = wanted
        self.budget.check()

    def raw(self, ref, base=ROOT, cap=4 << 20):
        path = self.path(ref, base)
        need(ref["bytes"] <= cap, "bounded input extent")
        with path.open("rb") as f:
            raw = f.read(cap + 1)
        wanted = {k: ref[k] for k in ("sha256", "bytes")}
        exact(dict(sha256=digest(raw), bytes=len(raw)), wanted, "actual input bytes")
        key = path.relative_to(ROOT).as_posix()
        if key in self.seen:
            exact(self.seen[key], wanted, "repeated input binding")
        self.seen[key] = wanted
        self.budget.check()
        return raw

    def json(self, ref, base=ROOT):
        return json_bytes(self.raw(ref, base))

    def map(self, values):
        need(type(values) is dict and values, "empty input/source map")
        for name, item in values.items():
            self.track(self.path(dict(path=name, **item)), item)

    def finish(self):
        for name, item in self.seen.items():
            exact(binding(ROOT / name), item, "input changed at finalization")
            self.budget.check()


class Store:
    def __init__(self, path, budget):
        self.root, self.budget, self.files = path.resolve(), budget, {}
        need(self.root.is_relative_to(ROOT), "output containment")
        self.root.mkdir(parents=True, exist_ok=False)

    def raw(self, name, raw):
        self.budget.output += len(raw); self.budget.check()
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            need(f.write(raw) == len(raw), "short output write")
            f.flush(); os.fsync(f.fileno())
        ref = dict(path=name, sha256=digest(raw), bytes=len(raw))
        self.files[name] = ref
        self.budget.check()
        return ref

    def json(self, name, value):
        raw = canonical(value)
        need(len(raw) <= 4 << 20, "bounded result JSON")
        return self.raw(name, raw)

    def finish(self):
        for name, ref in self.files.items():
            exact(binding(self.root/name), {k: ref[k] for k in ("sha256", "bytes")}, "output changed at finalization")
            self.budget.check()


def decode_tiff(raw, expected_sha, budget):
    """Independent classic TIFF parser; no TIFF package or prior parser."""
    budget.decodes += 1; budget.check()
    need(len(raw) <= 1 << 20 and digest(raw) == expected_sha, "TIFF bytes/hash")
    need(len(raw) >= 8 and raw[:2] in (b"II", b"MM"), "TIFF byte order")
    endian = "<" if raw[:2] == b"II" else ">"
    def unpack(fmt, at):
        n = struct.calcsize(endian+fmt)
        need(type(at) is int and 0 <= at <= len(raw)-n, "TIFF truncated field")
        return struct.unpack_from(endian+fmt, raw, at)
    magic, ifd = unpack("HI", 2)
    need(magic == 42 and ifd >= 8, "classic TIFF header")
    count, = unpack("H", ifd)
    need(1 <= count <= 64, "TIFF IFD count")
    need(ifd+2+12*count+4 <= len(raw), "TIFF truncated directory")
    need(unpack("I", ifd+2+12*count)[0] == 0, "TIFF multiple IFD")
    ranges = [(0, 8), (ifd, ifd+2+12*count+4)]
    tags, widths = {}, {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1}
    for i in range(count):
        tag, kind, n = unpack("HHI", ifd+2+i*12)
        need(tag not in tags and kind in widths and 0 < n <= 1 << 16, "TIFF tag type/duplicate")
        size = widths[kind]*n
        at = ifd+2+i*12+8 if size <= 4 else unpack("I", ifd+2+i*12+8)[0]
        need(at <= len(raw)-size, "TIFF truncated tag")
        if size > 4:
            ranges.append((at, at+size))
        if kind in (3, 4):
            vals = list(unpack(("H" if kind == 3 else "I")*n, at))
        elif kind == 2:
            need(raw[at+size-1] == 0, "TIFF string termination")
            vals = raw[at:at+size-1].decode("ascii", "strict")
        else:
            vals = raw[at:at+size].hex()
        tags[tag] = vals
    def scalar(tag, default=None):
        vals = tags.get(tag, [default])
        need(type(vals) is list and len(vals) == 1 and type(vals[0]) is int, "TIFF scalar tag")
        return vals[0]
    w, h = scalar(256), scalar(257)
    need(1 <= w <= 320 and 1 <= h <= 240, "TIFF dimension bound")
    need(tags.get(258) == [16, 16, 16] and tags.get(339) == [1, 1, 1], "TIFF unsigned16 samples")
    need(scalar(259) == 1 and scalar(262) == 2 and scalar(277) == 3
         and scalar(274, 1) == 1 and scalar(284, 1) == 1 and scalar(317, 1) == 1,
         "TIFF RGB storage/interpretation")
    need(338 not in tags and 34675 not in tags, "TIFF extra channels/ICC")
    need(tags.get(305) == "strehl 0.0.0", "TIFF software")
    offsets, lengths, rows = tags.get(273), tags.get(279), scalar(278)
    need(type(offsets) is list and type(lengths) is list and rows > 0
         and len(offsets) == len(lengths) == (h+rows-1)//rows, "TIFF strip population")
    for i, (at, size) in enumerate(zip(offsets, lengths, strict=True)):
        need(size == min(rows, h-i*rows)*w*6 and 0 <= at <= len(raw)-size, "TIFF strip extent")
        ranges.append((at, at+size))
    ordered = sorted(ranges)
    need(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), "TIFF overlapping ranges")
    # Allocate only after the complete metadata and all strip extents are checked.
    output = budget.watch(np.empty((h, w, 3), dtype="<u2"))
    for i, (at, size) in enumerate(zip(offsets, lengths, strict=True)):
        block = np.frombuffer(raw, dtype=endian+"u2", count=size//2, offset=at)
        budget.watch(block)
        output[i*rows:min(h, (i+1)*rows)] = block.reshape(-1, w, 3)
    budget.check()
    return output, dict(pixel_sha256=digest(output.tobytes(order="C")), shape=list(output.shape),
                        endian=endian, strips=len(offsets))


def private_tiff(codes, endian="<", rows=2, changed=None):
    """Tiny independent format fixtures, not authority or image-generation inputs."""
    h, w, _ = codes.shape
    lengths = [min(rows, h-y)*w*6 for y in range(0, h, rows)]
    tags = {256:(4,[w]), 257:(4,[h]), 258:(3,[16]*3), 259:(3,[1]), 262:(3,[2]),
            273:(4,[0]*len(lengths)), 277:(3,[3]), 278:(4,[rows]), 279:(4,lengths),
            305:(2,b"strehl 0.0.0\0"), 339:(3,[1]*3)}
    if changed:
        tags.update(changed)
    extra_start = 8+2+12*len(tags)+4
    encoded = {}
    for tag, (kind, value) in tags.items():
        encoded[tag] = value if kind == 2 else struct.pack(endian+("H" if kind == 3 else "I")*len(value), *value)
    pixel_start = extra_start + sum(len(v) for v in encoded.values() if len(v) > 4)
    offs, cursor = [], pixel_start
    for n in lengths:
        offs.append(cursor); cursor += n
    if not changed or 273 not in changed:
        encoded[273] = struct.pack(endian+"I"*len(offs), *offs)
    header = (b"II" if endian == "<" else b"MM") + struct.pack(endian+"HI", 42, 8)
    directory, extra = bytearray(struct.pack(endian+"H", len(tags))), bytearray()
    for tag in sorted(tags):
        kind, values = tags[tag]; raw = encoded[tag]
        directory += struct.pack(endian+"HHI", tag, kind, len(values))
        if len(raw) <= 4:
            directory += raw.ljust(4, b"\0")
        else:
            directory += struct.pack(endian+"I", extra_start+len(extra)); extra += raw
    directory += struct.pack(endian+"I", 0)
    return header+directory+extra+codes.astype(endian+"u2").tobytes(order="C")


def target_array(raw, budget):
    need(raw[:6] == b"\x93NUMPY" and raw[6:8] in (b"\x01\x00", b"\x02\x00"), "target NPY version")
    pos = 10 if raw[6] == 1 else 12
    size = struct.unpack_from("<H" if pos == 10 else "<I", raw, 8)[0]
    need(size <= 4096 and pos+size <= len(raw), "target NPY header extent")
    header = ast.literal_eval(raw[pos:pos+size].decode("latin1"))
    exact(header, {"descr":"<f8", "fortran_order":False, "shape":(240,320)}, "target NPY layout")
    need(len(raw) == pos+size+240*320*8, "target NPY payload extent")
    a = budget.watch(np.frombuffer(raw, dtype="<f8", offset=pos+size).reshape(240,320))
    need(np.isfinite(a).all() and (a >= 0).all(), "target finite nonnegative")
    return a


def regions(shape, origin, budget):
    h, w = shape; ox, oy = origin
    x, y = np.arange(w)[None,:]+ox, np.arange(h)[:,None]+oy
    z = x-.15*y-142
    window = (x >= 104)&(x < 216)&(y >= 104)&(y < 136)
    masks = {"whole":np.ones(shape, bool), "window":window, "boundary":window&(abs(z) <= 8),
             "surface-background":window&(z < -8), "surface-foreground":window&(z > 8),
             "endpoint-background":window&(z < -(.575+6*math.sqrt(1.0225)+2)),
             "endpoint-foreground":window&(z > .575+2)}
    budget.watch(x,y,z,*masks.values())
    need(all(m.any() for m in masks.values()), "empty original region")
    need(104-ox >= 74 and ox+w-216 >= 74 and 104-oy >= 74 and oy+h-136 >= 74, "original window support")
    return masks


def errors(a, b, mask, budget):
    d = budget.watch(np.subtract(a[mask], b[mask]))
    need(len(d)>0 and np.isfinite(d).all(), "finite nonempty error population")
    squared = float(np.dot(d,d)/len(d))
    return dict(bias_dn=float(np.mean(d)), mse_dn2=squared, rmse_dn=math.sqrt(squared), sites=len(d))


def mse(a, b, mask, budget):
    return errors(a,b,mask,budget)["mse_dn2"]


def sample_stats(values):
    n = len(values); mean = math.fsum(values)/n
    sd = math.sqrt(math.fsum((v-mean)**2 for v in values)/(n-1))
    return dict(values=values, mean=mean, sample_sd=sd, standard_error=sd/math.sqrt(n))


def phase_difference(actual, wanted):
    return math.atan2(math.sin(actual-wanted), math.cos(actual-wanted))


def centered_finish(anchor, s, q, count, budget):
    correction = budget.watch(np.square(s)/count)
    q -= correction; q /= count-1
    need(float(q.min()) >= -1e-8, "negative batch variance")
    s /= count; s += anchor
    return s, q


def sparse(a, b, target, mask, origin, budget):
    ids = budget.watch(np.flatnonzero(mask))
    av, bv, tv = (budget.watch(v.ravel()[ids]) for v in (a,b,target))
    ea, eb = budget.watch(av-tv, bv-tv)
    aa, ab = budget.watch(abs(ea), abs(eb))
    move = budget.watch(ab-aa)
    def site(i):
        y,x = divmod(int(ids[i]), a.shape[1])
        return dict(native_xy=[x+origin[0], y+origin[1]], before_dn=float(av[i]), after_dn=float(bv[i]),
                    target_dn=float(tv[i]), before_signed_error_dn=float(ea[i]), after_signed_error_dn=float(eb[i]),
                    absolute_error_movement_dn=float(move[i]))
    k = math.ceil(.999*len(ids))-1
    return dict(sites=len(ids), nearest_rank_index=k,
                before_maximum_absolute_error_dn=float(aa.max()), after_maximum_absolute_error_dn=float(ab.max()),
                before_p999_absolute_error_dn=float(np.partition(aa,k)[k]), after_p999_absolute_error_dn=float(np.partition(ab,k)[k]),
                before_worst_site=site(int(aa.argmax())), after_worst_site=site(int(ab.argmax())),
                maximum_worsening_site=site(int(move.argmax())), worsening_gt10_dn_count=int((move>10).sum()),
                improvement_gt10_dn_count=int((move < -10).sum()))


def fit_waves(value, mask, origin, frequencies, budget):
    yy,xx = np.nonzero(mask); xx = xx+origin[0]; yy = yy+origin[1]
    columns = [np.ones(len(xx))]
    for fx,fy in frequencies:
        phase = 2*math.pi*(fx*xx+fy*yy)
        columns.extend((np.cos(phase), np.sin(phase)))
    matrix = budget.watch(np.column_stack(columns))
    vals = budget.watch(value[mask])
    coefficients, _, rank, singular = np.linalg.lstsq(matrix, vals, rcond=None)
    budget.watch(xx,yy,*columns,coefficients,singular)
    need(rank == 5 and singular[0]/singular[-1] <= 1e6, "wave rank/condition")
    residual = budget.watch(vals-matrix@coefficients)
    waves=[]
    for k in (1,3):
        real, imag = float(coefficients[k]), -float(coefficients[k+1])
        amp = math.hypot(real,imag)
        waves.append(dict(real_dn=real, imaginary_dn=imag, amplitude_dn=amp,
                          phase_radians=None if amp <= 1e-8 else math.atan2(imag,real)))
    return dict(sites=len(vals), condition=float(singular[0]/singular[-1]), intercept_dn=float(coefficients[0]),
                residual_rms_dn=math.sqrt(float(np.dot(residual,residual)/len(vals))), waves=waves)


class Comparisons:
    def __init__(self):
        self.count, self.failures, self.ties, self.largest = 0, [], [], {}

    def close(self, actual, wanted, label, atol=1e-7, rtol=1e-10):
        self.count += 1
        if type(wanted) is dict:
            if type(actual) is not dict or set(actual) != set(wanted):
                self.failures.append(dict(label=label, reason="keys")); return
            for k in wanted:
                self.close(actual[k],wanted[k],label+"/"+k,atol,rtol)
        elif type(wanted) is list:
            if type(actual) is not list or len(actual) != len(wanted):
                self.failures.append(dict(label=label, reason="list")); return
            for i,(a,b) in enumerate(zip(actual,wanted,strict=True)):
                self.close(a,b,label+"/"+str(i),atol,rtol)
        elif type(wanted) in (int,float) and type(actual) in (int,float):
            err=abs(actual-wanted)
            group=label.split("/")[0]
            if err > self.largest.get(group,{}).get("absolute",-1):
                self.largest[group]=dict(absolute=err,label=label,actual=actual,reported=wanted)
            if not math.isfinite(actual) or not math.isfinite(wanted) or err > atol+rtol*abs(wanted):
                self.failures.append(dict(label=label,actual=actual,reported=wanted,error=err))
        elif type(actual) is not type(wanted) or actual != wanted:
            self.failures.append(dict(label=label,actual=actual,reported=wanted))

    def sparse(self, actual, wanted, a, b, target, mask, origin, label, allow_mean_tie=False):
        wanted = dict(wanted)
        for key in ("scene","seed","channel","region","population"):
            wanted.pop(key,None)
        for key in ("before_worst_site","after_worst_site","maximum_worsening_site"):
            expected = dict(wanted[key]); observed = actual[key]
            if observed["native_xy"] != expected["native_xy"]:
                x,y = expected["native_xy"]; ix,iy=x-origin[0],y-origin[1]
                need(0 <= iy < a.shape[0] and 0 <= ix < a.shape[1] and mask[iy,ix], "reported sparse coordinate outside mask")
                av,bv,tv=map(float,(a[iy,ix],b[iy,ix],target[iy,ix]))
                candidate=dict(native_xy=[x,y],before_dn=av,after_dn=bv,target_dn=tv,
                               before_signed_error_dn=av-tv,after_signed_error_dn=bv-tv,
                               absolute_error_movement_dn=abs(bv-tv)-abs(av-tv))
                which = "before_signed_error_dn" if key=="before_worst_site" else "after_signed_error_dn"
                delta=(abs(candidate[which])-abs(observed[which])) if key!="maximum_worsening_site" else candidate["absolute_error_movement_dn"]-observed["absolute_error_movement_dn"]
                if allow_mean_tie and abs(delta) <= 1e-8:
                    self.ties.append(dict(label=label+"/"+key,independent=observed["native_xy"],reported=[x,y],maximum_difference_dn=delta))
                    self.close(candidate,expected,label+"/"+key,1e-8,0)
                    wanted[key]=observed
        for key in ("sites","nearest_rank_index","worsening_gt10_dn_count","improvement_gt10_dn_count"):
            self.close(actual[key],wanted[key],label+"/"+key,0,0)
        self.close(actual,wanted,label,1e-8,0)


def private_controls(budget, store, checks):
    initial_decodes=budget.decodes
    def passed(name, condition, details=None):
        checks.append(dict(id=name,passed=bool(condition),details=details))
        need(condition, "private control failed: "+name)
    def refuses(name, call, message):
        error=None
        try: call()
        except Refusal as exc: error=str(exc)
        passed(name,error is not None and message in error,dict(error=error,boundary=message))
    codes=budget.watch(np.arange(5*7*3,dtype="<u2").reshape(5,7,3)*13)
    for order in ("<",">"):
        raw=private_tiff(codes,order)
        store.raw("private/tiff-"+("le" if order=="<" else "be")+".tif",raw)
        decoded,proof=decode_tiff(raw,digest(raw),budget)
        passed("tiff-valid-"+order,np.array_equal(decoded,codes) and proof["strips"]==3,proof)
    raw=private_tiff(codes)
    for name,mutant,boundary in (
        ("sample-format",private_tiff(codes,changed={339:(3,[2]*3)}),"unsigned16"),
        ("strip-overlap",private_tiff(codes,changed={273:(4,[8]*3)}),"overlapping"),
        ("truncated",raw[:-1],"strip extent"),
        ("huge-dimension",private_tiff(codes,changed={256:(4,[1000000])}),"dimension bound")):
        store.raw("private/tiff-"+name+".tif",mutant)
        refuses("tiff-refuses-"+name,lambda m=mutant:decode_tiff(m,digest(m),budget),boundary)
    refuses("tiff-wrong-external-hash",lambda:decode_tiff(raw,"0"*64,budget),"bytes/hash")
    changed=codes.copy(); changed[2,3,1]+=1; budget.watch(changed)
    mutant=private_tiff(changed); decoded,proof=decode_tiff(mutant,digest(mutant),budget)
    store.raw("private/tiff-changed-green.tif",mutant)
    passed("tiff-green-code-live",proof["pixel_sha256"]!=digest(codes.tobytes()) and int(decoded[2,3,1])-int(codes[2,3,1])==1)
    restored,_=decode_tiff(raw,digest(raw),budget)
    passed("tiff-restored",np.array_equal(restored,codes))
    offsets=(-7,-5,-3,-1,1,3,5,7)
    plane=budget.watch(np.arange(35,dtype=float).reshape(5,7)*3+3000)
    def batch(scale):
        anchor=budget.watch(plane+scale*offsets[0]); s=budget.watch(np.zeros_like(plane)); q=budget.watch(np.zeros_like(plane))
        for d in offsets:
            diff=budget.watch(plane+scale*d-anchor); s+=diff; q+=diff*diff
        return centered_finish(anchor,s,q,8,budget)
    mean,var=batch(1); cm,cv=batch(.5); _,constant=batch(0)
    passed("batch-temporal-24",np.all(var==24) and np.array_equal(mean,plane))
    passed("batch-half-6-ratio-quarter",np.all(cv==6) and np.all(cv/var==.25))
    passed("constant-structured-temporal-zero",np.all(constant==0) and float(np.var(plane,ddof=1))>24)
    passed("spatial-axis-live-fault",abs(float(np.var(plane,ddof=1))-24)>1)
    error_mask=budget.watch(np.ones(plane.shape,bool))
    differences=[]; error_rows=[]
    for offset in offsets:
        before=budget.watch(plane+offset); after=budget.watch(plane+.5*offset)
        first=errors(before,plane,error_mask,budget); second=errors(after,plane,error_mask,budget)
        differences.append(second["mse_dn2"]-first["mse_dn2"])
        error_rows.append(dict(offset=offset,before=first,after=second))
    stats=sample_stats(differences)
    passed("paired-mse-literal",differences==[-.75*d*d for d in offsets]
           and all(r["before"]==dict(bias_dn=float(r["offset"]),mse_dn2=float(r["offset"]**2),
                                     rmse_dn=float(abs(r["offset"])),sites=35)
                   and r["after"]==dict(bias_dn=.5*r["offset"],mse_dn2=.25*r["offset"]**2,
                                         rmse_dn=.5*abs(r["offset"]),sites=35) for r in error_rows)
           and stats["mean"]==-15.75 and abs(stats["standard_error"]-math.sqrt(27))<1e-12,
           dict(actual_errors=error_rows,paired=stats))
    # Synthetic native coordinates deliberately keep the outside-W impulse.
    shape=(32,120); origin=(100,104)
    base=budget.watch(np.full(shape,3000.)); after=budget.watch(base.copy()); truth=budget.watch(base.copy())
    mask=budget.watch(np.ones(shape,bool)); window=budget.watch(np.zeros(shape,bool)); window[:,4:116]=True
    after[0,0]+=64; after[4,9]-=64
    s=sparse(base,after,truth,mask,origin,budget); sw=sparse(base,after,truth,window,origin,budget)
    passed("sparse-tie-native-and-outside-window",s["maximum_worsening_site"]["native_xy"]==[100,104]
           and s["worsening_gt10_dn_count"]==2 and sw["worsening_gt10_dn_count"]==1
           and s["after_maximum_absolute_error_dn"]==64,dict(whole=s,window=sw))
    null=sparse(base,base,truth,mask,origin,budget)
    passed("sparse-restored",null["after_maximum_absolute_error_dn"]==0 and null["worsening_gt10_dn_count"]==0)
    yy,xx=np.indices(shape); xx+=origin[0]; yy+=origin[1]; budget.watch(xx,yy)
    frequencies=((.045,.095),(.17,.01))
    signal=budget.watch(3000+40*np.cos(2*math.pi*(.045*xx+.095*yy)+.31)+25*np.cos(2*math.pi*(.17*xx+.01*yy)-.47))
    flat=fit_waves(base,mask,origin,frequencies,budget)
    passed("wave-flat-first",max(v["amplitude_dn"] for v in flat["waves"])<=1e-7 and flat["residual_rms_dn"]<=1e-7,flat)
    wave=fit_waves(signal,mask,origin,frequencies,budget)
    passed("wave-two-literal",abs(wave["waves"][0]["amplitude_dn"]-40)<1e-7
           and abs(wave["waves"][1]["amplitude_dn"]-25)<1e-7 and wave["residual_rms_dn"]<1e-7,wave)
    half=budget.watch(3000+(signal-3000)*.5)
    fault=fit_waves(half,mask,origin,frequencies,budget)
    passed("wave-amplitude-live",abs(fault["waves"][0]["amplitude_dn"]-wave["waves"][0]["amplitude_dn"])>1
           and mse(half,signal,mask,budget)>1,fault)
    wrong=fit_waves(signal,mask,(0,0),frequencies,budget)
    passed("wave-native-offset-live",abs(wrong["waves"][0]["real_dn"]-wave["waves"][0]["real_dn"])>1,wrong)
    again=fit_waves(signal,mask,origin,frequencies,budget)
    passed("wave-restored",canonical(again)==canonical(wave)
           and abs(phase_difference(math.pi,-math.pi))<1e-12)
    need(len(checks)==21 and budget.decodes-initial_decodes==9,"complete finite private population")
    return checks


def expected_population():
    rows=[]
    for si,scene in enumerate(("flat","textured")):
        for ti,seed in enumerate((None,)+SEEDS):
            modes=MODES if (si*9+ti)%2==0 else MODES[::-1]
            for mode in modes:
                rows.append(dict(ordinal=len(rows),scene=scene,noise_enabled=seed is not None,seed=seed,
                                 admission=mode,subset="all-five",original_indices=list(range(5))))
    for idx in (0,4):
        rows.append(dict(ordinal=len(rows),scene="textured",noise_enabled=False,seed=None,
                         admission="hard-floor",subset="endpoint-"+str(idx),original_indices=[idx]))
    return rows


def table(rows, keys):
    out={}
    for row in rows:
        key=tuple(row[k] for k in keys)
        need(key not in out,"duplicate reported metric row")
        out[key]=row
    return out


def run_check(score, score_path, files, budget, store, comparisons, actual_result):
    exact(score["status"],"COMPLETE_FIXED_QUALITY_DIAGNOSTICS","complete original score")
    need(score["error"] is None and score["finalization_errors"]==[],"original score failure")
    exact(score["sources_before"],score["sources_after"],"score sources invariant")
    exact(score["inputs_before"],score["inputs_after"],"score inputs invariant")
    files.map(score["sources_before"]); files.map(score["inputs_before"])
    for name,wanted in score["sources_before"].items():
        files.track(score_path.parent/"sources"/name,wanted)
    matrix=files.json(score["matrix"])
    need(matrix["status"]=="COMPLETE_38_RGB_OUTPUTS_UNSCORED" and matrix["error"] is None
         and matrix["finalization_errors"]==[],"complete original matrix")
    rows=matrix["entries"]; expected=expected_population()
    need(len(rows)==len(score["entries"])==38 and len(score["decode_reads"])==108,"original fixed populations")
    for row,wanted in zip(rows,expected,strict=True):
        exact({k:row[k] for k in wanted},wanted,"independent ordered state population")
    geometry=score["geometry"]; origin=geometry["canonical_native_offset"]
    width,height=geometry["output_native"]
    crop=geometry["crop_quad"]
    exact(origin,[2*crop["x"],2*crop["y"]],"native crop origin")
    exact([width,height],[2*crop["width"],2*crop["height"]],"native crop size")
    exact(geometry["full_native"],[320,240],"native full geometry")
    fixture=files.json(score["fixture"])
    raw=files.raw(score["scalar"]); scalar=target_array(raw,budget)
    crop_scalar=scalar[origin[1]:origin[1]+height,origin[0]:origin[0]+width]
    need(crop_scalar.shape==(height,width),"target actual crop")
    factors=np.array([.75*1.3333333730697632,1.,.6*1.6666666269302368])*.25
    budget.watch(factors)
    masks=regions((height,width),origin,budget)
    checked={}; identities=set(); decoded={}; genuine_reads=[]
    actual_result.update(scene_results=[],genuine_decode_reads=genuine_reads,distinct_actual_tiffs=0,
                         original_masks={k:int(v.sum()) for k,v in masks.items()})
    for row,ref in zip(rows,score["entries"],strict=True):
        item=files.json(ref,score_path.parent)
        exact(item["row"],row,"checked entry to actual matrix")
        plan=files.json(row["plan"]); receipt=files.json(row["receipt"])
        exact(item["plan"],plan,"actual saved plan"); exact(item["receipt"],receipt,"actual saved receipt")
        exact(receipt["plan_sha256"],row["plan"]["sha256"],"actual receipt plan digest")
        exact(receipt["plan"],plan,"actual recomputed plan")
        for key in ("canonical_native_offset","output_native","crop_quad","full_native","level_sizes"):
            exact(item["geometry"][key],geometry[key],"common actual geometry")
        p=files.path(row["tiff"]); st=p.stat(); identity=(st.st_dev,st.st_ino)
        need(st.st_ino and identity not in identities,"actual TIFF physical alias"); identities.add(identity)
        exact({k:receipt["output"][k] for k in ("sha256","bytes")},
              {k:row["tiff"][k] for k in ("sha256","bytes")},"receipt TIFF reference")
        exact(receipt["output"]["pixel_sha256_le"],item["decoded"]["pixel_sha256"],"prior independent pixel association")
        checked[row["ordinal"]]=item["decoded"]["pixel_sha256"]
    def load(row,phase):
        raw=files.raw(row["tiff"],cap=1<<20)
        codes,proof=decode_tiff(raw,row["tiff"]["sha256"],budget)
        exact(proof["shape"],[height,width,3],"independent TIFF shape")
        exact(proof["pixel_sha256"],checked[row["ordinal"]],"independent TIFF pixel hash")
        decoded[row["ordinal"]]=proof
        actual_result["distinct_actual_tiffs"]=len(decoded)
        genuine_reads.append(dict(ordinal=row["ordinal"],phase=phase,proof=proof))
        value=budget.watch(codes.astype("<f8")); value*=DN
        return value
    outputs=actual_result["scene_results"]
    for scene_index,scene in enumerate(("flat","textured")):
        report=files.json(score["scene_results"][scene_index],score_path.parent)
        exact(report["scene"],scene,"readout scene order"); exact(report["repeat_seeds"],list(SEEDS),"all eight report seeds")
        exact(report["region_sites"],{k:int(v.sum()) for k,v in masks.items()},"independent region counts")
        temporal=table(report["temporal"],("mode","channel","reference","region"))
        pmse=table(report["paired_mse"],("channel","reference","region"))
        pvar=table(report["paired_variance"],("channel","region"))
        sparse_rows=table(report["sparse"],("population","seed","channel","region"))
        wave_rows=table(report["noise_off_waves"],("mode","channel","region"))
        individual_rows=table(report["individual_errors"],("seed","channel","reference","region","mode"))
        states={(r["seed"],r["admission"]):r for r in rows if r["scene"]==scene and r["subset"]=="all-five"}
        off=[load(states[(None,mode)],"noise-off") for mode in MODES]
        ideal=budget.watch(np.empty((height,width,3),dtype="<f8"))
        for ch in range(3):
            ideal[:,:,ch]=(12000. if scene=="flat" else crop_scalar)*factors[ch]
        references=[("ideal",ideal,tuple(masks))]
        endpoints=[]; endpoint=None
        if scene=="textured":
            for index,region in ((0,"endpoint-background"),(4,"endpoint-foreground")):
                r=next(v for v in rows if v["subset"]=="endpoint-"+str(index))
                endpoint=load(r,"endpoint"); endpoints.append(endpoint)
                references.append(("endpoint-"+str(index),endpoint,(region,)))
        expected_individual=[(seed,name,ref_name,region,mode) for seed in (None,)+SEEDS for name in CHANNELS
                             for ref_name,_,region_names in references for region in region_names for mode in MODES]
        need(len(expected_individual)==(378 if scene=="flat" else 486),"fixed individual error population")
        exact(list(individual_rows),expected_individual,"complete ordered reported individual error keys")
        result=dict(scene=scene,individual_errors=[],temporal=[],paired_mse=[],variance=[],sparse=[],waves=[],nuisance=[],decoded_ordinals=[])
        def individual(pair,seed):
            calculated={}
            for ch,name in enumerate(CHANNELS):
                for ref_name,reference,region_names in references:
                    for region in region_names:
                        for mi,mode in enumerate(MODES):
                            actual=dict(scene=scene,seed=seed,channel=name,reference=ref_name,region=region,mode=mode,
                                        **errors(pair[mi][:,:,ch],reference[:,:,ch],masks[region],budget))
                            key=(seed,name,ref_name,region,mode)
                            comparisons.close(actual,individual_rows[key],scene+"/individual-errors/"+str(key))
                            result["individual_errors"].append(actual)
                            calculated[(mode,name,ref_name,region)]=actual
            return calculated
        def tails(a,b,population,seed):
            for ch,name in enumerate(CHANNELS):
                for region in ("whole","window"):
                    actual=sparse(a[:,:,ch],b[:,:,ch],ideal[:,:,ch],masks[region],origin,budget)
                    wanted=sparse_rows[(population,seed,name,region)]
                    comparisons.sparse(actual,wanted,a[:,:,ch],b[:,:,ch],ideal[:,:,ch],masks[region],origin,
                                       scene+"/sparse/"+str((population,seed,name,region)),
                                       allow_mean_tie=population=="eight-repeat-mean")
                    result["sparse"].append(dict(population=population,seed=seed,channel=name,region=region,**actual))
        tails(*off,"individual",None)
        individual(off,None)
        anchors, sums, squares=[],[],[]
        per_seed={}; nuisance={}
        for seed in SEEDS:
            pair=[load(states[(seed,mode)],"batch") for mode in MODES]
            if seed==SEEDS[0]:
                anchors=[budget.watch(v.copy()) for v in pair]
                sums=[budget.watch(np.zeros_like(v)) for v in pair]
                squares=[budget.watch(np.zeros_like(v)) for v in pair]
            for mode_index in range(2):
                d=budget.watch(pair[mode_index]-anchors[mode_index]); sums[mode_index]+=d; squares[mode_index]+=d*d
            tails(*pair,"individual",seed)
            individual_values=individual(pair,seed)
            for ref_name,reference,region_names in references:
                for ch,name in enumerate(CHANNELS):
                    for region in region_names:
                        values=[individual_values[(mode,name,ref_name,region)]["mse_dn2"] for mode in MODES]
                        per_seed.setdefault((name,ref_name,region),[]).append(values[1]-values[0])
            for ch,name in enumerate(CHANNELS):
                for region in ("whole","window"):
                    values=[mse(pair[i][:,:,ch],off[i][:,:,ch],masks[region],budget) for i in range(2)]
                    nuisance.setdefault((name,region),[]).append(values[1]-values[0])
            del pair,d
        means,variances=[],[]
        for i in range(2):
            mean,variance=centered_finish(anchors[i],sums[i],squares[i],8,budget)
            means.append(mean); variances.append(variance)
        del anchors,sums,squares
        tails(*means,"eight-repeat-mean",None)
        for key,values in per_seed.items():
            stats=sample_stats(values)
            comparisons.close(stats,pmse[key]["candidate_minus_baseline"],scene+"/paired-mse/"+str(key))
            result["paired_mse"].append(dict(channel=key[0],reference=key[1],region=key[2],**stats))
        for key,values in nuisance.items():
            result["nuisance"].append(dict(channel=key[0],region=key[1],reference="own-noise-off",**sample_stats(values)))
        actual_individual=table(result["individual_errors"],("seed","channel","reference","region","mode"))
        for mi,mode in enumerate(MODES):
            all_refs=references+[("own-noise-off",off[mi],tuple(masks))]
            for ref_name,reference,region_names in all_refs:
                for ch,name in enumerate(CHANNELS):
                    for region in region_names:
                        mask=masks[region]
                        v=float(np.mean(variances[mi][:,:,ch][mask]))
                        mean_mse=mse(means[mi][:,:,ch],reference[:,:,ch],mask,budget)
                        bias=float(np.mean((means[mi][:,:,ch]-reference[:,:,ch])[mask]))
                        wanted=temporal[(mode,name,ref_name,region)]
                        if ref_name=="own-noise-off":
                            record=dict(bias_dn=bias,mse_dn2=mean_mse,rmse_dn=math.sqrt(mean_mse),sites=int(mask.sum()))
                        else:
                            repeat_mse=math.fsum(actual_individual[(seed,name,ref_name,region,mode)]["mse_dn2"] for seed in SEEDS)/8
                            record=dict(temporal_variance_dn2=v,mean_image_mse_dn2=mean_mse,mean_image_bias_dn=bias,
                                        mean_repeat_mse_dn2=repeat_mse,unbiased_squared_bias_dn2=mean_mse-v/8,
                                        arithmetic_residual_dn2=repeat_mse-(mean_mse+7*v/8))
                        comparisons.close(record,{k:wanted[k] for k in record},scene+"/temporal/"+str((mode,name,ref_name,region)))
                        result["temporal"].append(dict(mode=mode,channel=name,reference=ref_name,region=region,**record,
                                                      decomposition_scope="arithmetic consistency only; not independent evidence"
                                                      if ref_name!="own-noise-off" else "mode-specific nuisance reference; not fidelity truth"))
        deletion={}
        for seed in SEEDS:
            pair=[load(states[(seed,mode)],"delete-one") for mode in MODES]
            for ch,name in enumerate(CHANNELS):
                for region,mask in masks.items():
                    values=[]
                    for mi in range(2):
                        delta=budget.watch(pair[mi][:,:,ch]-means[mi][:,:,ch])
                        kept=budget.watch((7*variances[mi][:,:,ch]-(8/7)*delta*delta)/6)
                        values.append(float(np.mean(kept[mask])))
                    deletion.setdefault((name,region),[]).append(values)
            del pair,delta,kept
        for ch,name in enumerate(CHANNELS):
            for region,mask in masks.items():
                values=[float(np.mean(v[:,:,ch][mask])) for v in variances]
                actual=dict(baseline_variance_dn2=values[0],candidate_variance_dn2=values[1],
                            candidate_minus_baseline_dn2=values[1]-values[0],
                            candidate_over_baseline=None if values[0]==0 else values[1]/values[0])
                for mi,label in ((0,"baseline_delete_one"),(1,"candidate_delete_one"),(2,"paired_delete_one")):
                    series=[v[mi] if mi<2 else v[1]-v[0] for v in deletion[(name,region)]]
                    summary=sample_stats(series)
                    summary["jackknife_standard_error"]=math.sqrt(7/8*math.fsum((v-summary["mean"])**2 for v in series))
                    actual[label]=summary
                wanted=pvar[(name,region)]
                comparisons.close(actual,{k:wanted[k] for k in actual},scene+"/variance/"+name+"/"+region)
                result["variance"].append(dict(channel=name,region=region,**actual))
        if scene=="textured":
            for region,field in (("surface-background","background"),("surface-foreground","foreground")):
                frequencies=[v["frequency"] for v in fixture["scene"][field]["waves"]]
                for ch,name in enumerate(CHANNELS):
                    target_fit=fit_waves(ideal[:,:,ch],masks[region],origin,frequencies,budget)
                    for mi,mode in enumerate(MODES):
                        observed=fit_waves(off[mi][:,:,ch],masks[region],origin,frequencies,budget)
                        wanted=wave_rows[(mode,name,region)]
                        # Phase needs its separate tighter absolute tolerance.
                        for label,got in (("observed",observed),("target",target_fit)):
                            values={**got,"waves":[{k:v for k,v in w.items() if k!="phase_radians"} for w in got["waves"]]}
                            expected_values={**wanted[label],"waves":[{k:v for k,v in w.items() if k!="phase_radians"} for w in wanted[label]["waves"]]}
                            comparisons.close(values,expected_values,scene+"/waves/"+str((mode,name,region,label)),1e-7,1e-10)
                            for j,wave in enumerate(got["waves"]):
                                actual_phase=wave["phase_radians"]; wanted_phase=wanted[label]["waves"][j]["phase_radians"]
                                if actual_phase is None or wanted_phase is None:
                                    comparisons.close(actual_phase,wanted_phase,scene+"/wave-phase/"+str((mode,name,region,label,j)),0,0)
                                else:
                                    comparisons.close(phase_difference(actual_phase,wanted_phase),0.,
                                                      scene+"/wave-phase/"+str((mode,name,region,label,j)),1e-9,0)
                        differences=[]
                        for j,(a,b) in enumerate(zip(observed["waves"],target_fit["waves"],strict=True)):
                            re=a["real_dn"]-b["real_dn"]; im=a["imaginary_dn"]-b["imaginary_dn"]
                            difference=dict(real_error_dn=re,imaginary_error_dn=im,complex_error_dn=math.hypot(re,im),
                                            amplitude_difference_dn=a["amplitude_dn"]-b["amplitude_dn"],
                                            phase_error_radians=None if a["phase_radians"] is None or b["phase_radians"] is None
                                            else phase_difference(a["phase_radians"],b["phase_radians"]))
                            comparisons.close({k:v for k,v in difference.items() if k!="phase_error_radians"},
                                              {k:v for k,v in wanted["differences"][j].items() if k!="phase_error_radians"},
                                              scene+"/wave-difference/"+str((mode,name,region,j)),1e-7,1e-10)
                            if difference["phase_error_radians"] is not None and wanted["differences"][j]["phase_error_radians"] is not None:
                                comparisons.close(phase_difference(difference["phase_error_radians"],wanted["differences"][j]["phase_error_radians"]),0.,
                                                  scene+"/wave-phase-difference/"+str((mode,name,region,j)),1e-9,0)
                            else:
                                comparisons.close(difference["phase_error_radians"],wanted["differences"][j]["phase_error_radians"],
                                                  scene+"/wave-phase-difference/"+str((mode,name,region,j)),0,0)
                            differences.append(difference)
                        result["waves"].append(dict(mode=mode,channel=name,region=region,observed=observed,target=target_fit,
                                                   differences=differences,
                                                   full_signal_mse_dn2=mse(off[mi][:,:,ch],ideal[:,:,ch],masks[region],budget)))
                        signal_mse=mse(off[mi][:,:,ch],ideal[:,:,ch],masks[region],budget)
                        signal_error=dict(mse_dn2=signal_mse,rmse_dn=math.sqrt(signal_mse),sites=int(masks[region].sum()),
                                          bias_dn=float(np.mean((off[mi][:,:,ch]-ideal[:,:,ch])[masks[region]])))
                        comparisons.close(signal_error,wanted["full_signal_error"],scene+"/wave-full-signal/"+str((mode,name,region)))
        result["decoded_ordinals"]=[r["ordinal"] for r in rows if r["scene"]==scene]
        exact([(v["seed"],v["channel"],v["reference"],v["region"],v["mode"]) for v in result["individual_errors"]],
              expected_individual,"complete actual individual error keys")
        outputs.append(store.json(scene+"-independent.json",result))
        del means,variances,off,ideal,endpoints,references,result,mean,variance,all_refs,reference,endpoint
    need(set(decoded)==set(range(38)) and len(genuine_reads)==70,"independent complete actual TIFF population")
    return actual_result


def main():
    parser=argparse.ArgumentParser()
    for name in ("release","score"):
        parser.add_argument("--"+name,type=Path,required=True)
        parser.add_argument("--"+name+"-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(); budget=Budget(); files=Files(budget)
    for p in (args.release,args.score,args.output):
        need(p.is_absolute(),"absolute external/output path")
    need(args.score_sha256==SCORE_SHA,"registered actual score pin")
    release_ref=dict(path=args.release.resolve().relative_to(ROOT).as_posix(),**binding(args.release))
    exact(release_ref["sha256"],args.release_sha256,"external release hash")
    release=files.json(release_ref)
    need(set(release)==set(("schema","scope","source_bindings","inputs","commands")),"release keys")
    exact(release["schema"],"m194g-numerical-execution-release-v1","release schema")
    exact(release["scope"],"independent-quality-result-check","release scope")
    own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    need(set(release["source_bindings"])=={own},"independent source closure")
    files.map(release["source_bindings"])
    for ref in release["inputs"]:
        files.track(files.path(ref),{k:ref[k] for k in ("sha256","bytes")})
    score_ref=dict(path=args.score.resolve().relative_to(ROOT).as_posix(),**binding(args.score))
    exact(score_ref["sha256"],args.score_sha256,"external score hash")
    design_ref=dict(path=DESIGN.relative_to(ROOT).as_posix(),**binding(DESIGN))
    need(score_ref in release["inputs"] and design_ref in release["inputs"],"required released inputs")
    choices=[]
    for command in release["commands"]:
        need(type(command) is list and all(type(v) is str for v in command)
             and command.count("ACTUAL_EXECUTION_RELEASE_SHA256")==1,"release exact command syntax")
        choices.append([args.release_sha256 if v=="ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in command])
    need(list(sys.orig_argv) in choices,"actual invocation released")
    for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        os.environ[key]="2"
    global np
    import numpy as np
    store=Store(args.output,budget); comparisons=Comparisons()
    result=dict(schema="m194g-independent-quality-result-check-v1",status="UNCOMMISSIONED_INDEPENDENT_RESULT_CHECK",
                scope="fixed38 independent decoder/batch statistics; no quality GO",invocation=list(sys.orig_argv),
                execution_release=release_ref,score=score_ref,sources_before=release["source_bindings"],sources_after=None,
                inputs_before=None,inputs_after=None,private_controls=[],actual=None,comparisons=None,work=None,
                runtime=dict(python=sys.version,executable=sys.executable,numpy=np.__version__,
                             platform_system=platform.system(),platform_machine=platform.machine(),
                             thread_environment={k:os.environ[k] for k in
                              ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS")}),
                error=None,finalization_errors=[])
    try:
        store.raw("source/"+Path(__file__).name,Path(__file__).read_bytes())
        store.raw("source/"+DESIGN.name,DESIGN.read_bytes())
        private_controls(budget,store,result["private_controls"])
        score=files.json(score_ref)
        result["actual"]={}
        run_check(score,args.score,files,budget,store,comparisons,result["actual"])
        need(budget.decodes==79,"complete79 actual/private decode attempts")
        need(not comparisons.failures,"independent metric comparison mismatch")
        result["status"]="PASS_INDEPENDENT_FIXED_DIAGNOSTICS_ONLY"
    except Exception:
        result["error"]=traceback.format_exc()
    result["comparisons"]=dict(count=comparisons.count,failures=comparisons.failures,numerical_coordinate_ties=comparisons.ties,
                                largest_absolute_differences=comparisons.largest)
    result["inputs_before"]=dict(files.seen)
    try:
        for _ in range(2):
            files.finish(); store.finish()
            result["sources_after"]={name:binding(ROOT/name) for name in release["source_bindings"]}
            exact(result["sources_after"],result["sources_before"],"final source closure")
            result["inputs_after"]=dict(files.seen); result["work"]=budget.receipt()
            store.json("result.json",result)
        files.finish(); store.finish(); budget.check()
    except Exception:
        result["status"]="UNCOMMISSIONED_INDEPENDENT_RESULT_CHECK"
        result["finalization_errors"].append(traceback.format_exc())
        try:
            raw=canonical(result); budget.output+=len(raw)
            with (store.root/"result.json").open("wb") as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
        except Exception as exc:
            print("terminal persistence failed: "+repr(exc),file=sys.stderr)
    print(json.dumps(dict(status=result["status"],private=len(result["private_controls"]),comparisons=comparisons.count,
                          mismatches=len(comparisons.failures),error=result["error"],finalization_errors=result["finalization_errors"])),flush=True)
    return 0 if result["status"]=="PASS_INDEPENDENT_FIXED_DIAGNOSTICS_ONLY" else 1


if __name__=="__main__":
    raise SystemExit(main())
