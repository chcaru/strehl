"""Commission the actual independent reader/oracles before product TIFF reads."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import sys
import time
import traceback

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("independent_reader", HERE / "independent-reader.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def edit_tag(raw, target, *, value=None, typ=None, count=None, new_tag=None):
    raw = bytearray(raw)
    endian = "<" if raw[:2] == b"II" else ">"
    ifd = struct.unpack_from(endian + "I", raw, 4)[0]
    n = struct.unpack_from(endian + "H", raw, ifd)[0]
    for i in range(n):
        at = ifd + 2 + 12*i
        tag, oldtype, oldcount = struct.unpack_from(endian + "HHI", raw, at)
        if tag == target:
            if new_tag is not None:
                struct.pack_into(endian + "H", raw, at, new_tag)
            if typ is not None:
                struct.pack_into(endian + "H", raw, at + 2, typ)
            if count is not None:
                struct.pack_into(endian + "I", raw, at + 4, count)
            if value is not None:
                actualtype = oldtype if typ is None else typ
                fmt = "H" if actualtype == 3 else "I"
                struct.pack_into(endian + fmt, raw, at + 8, value)
            return bytes(raw)
    raise ValueError("missing commissioning tag " + str(target))


def add_tag(raw, tag, typ, count, value):
    raw = bytearray(raw)
    endian = "<" if raw[:2] == b"II" else ">"
    old = struct.unpack_from(endian + "I", raw, 4)[0]
    n = struct.unpack_from(endian + "H", raw, old)[0]
    entries = [bytes(raw[old+2+12*i:old+14+12*i]) for i in range(n)]
    packed = struct.pack(endian + ("H" if typ == 3 and count == 1 else "I"), value).ljust(4, b"\0")
    entries.append(struct.pack(endian + "HHI", tag, typ, count) + packed)
    entries.sort(key=lambda x: struct.unpack_from(endian + "H", x)[0])
    new = len(raw)
    raw += struct.pack(endian + "H", len(entries)) + b"".join(entries) + struct.pack(endian + "I", 0)
    struct.pack_into(endian + "I", raw, 4, new)
    return bytes(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    files = out / "files"
    files.mkdir()
    snapshot = out / "source-snapshot"
    snapshot.mkdir()
    sources = [Path(__file__), HERE / "independent-reader.py", HERE / "independent-reader-preregister.md", HERE / "preregister.md"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    for p in sources:
        shutil.copyfile(p, snapshot / p.name)
    result = dict(schema="m194f-independent-reader-controls-v1", status="RUNNING", fixture_only=True,
                  started_utc=datetime.now(timezone.utc).isoformat(), orig_argv=sys.orig_argv,
                  executable=sys.executable, python=sys.version, platform=platform.platform(),
                  xoptions=sys._xoptions, numpy=np.__version__, tifffile=tifffile.__version__,
                  thread_environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                  source_before=before, cases=[])
    start, cpu = time.perf_counter(), time.process_time()

    def case(name, operation, must_refuse=False):
        try:
            detail = operation()
            passed = not must_refuse
            record = dict(name=name, passed=passed, expected_refusal=must_refuse, detail=detail)
        except R.Refusal as error:
            record = dict(name=name, passed=must_refuse, expected_refusal=must_refuse, refusal=str(error))
        except Exception as error:
            record = dict(name=name, passed=False, expected_refusal=must_refuse,
                          unexpected=repr(error), traceback=traceback.format_exc())
        result["cases"].append(record)
        print(json.dumps(record, allow_nan=False), flush=True)

    def write(name, pixels, kind, endian="<", rows=7, orientation=None):
        path = files / (name + ".tiff")
        extra = [] if orientation is None else [(274, "H", 1, orientation, False)]
        tifffile.imwrite(path, pixels, photometric="rgb" if kind == "rgb" else "minisblack",
                         metadata=None, description=R.DESCRIPTION if kind == "rgb" else None,
                         software=R.SOFTWARE if kind == "rgb" else False,
                         resolution=(1, 1), resolutionunit="NONE", compression=None,
                         rowsperstrip=rows, byteorder=endian, extratags=extra)
        return path

    y, x = np.mgrid[:32, :48]
    constant = R.quantize(R.oracle("constant", x+6, y+10))
    affine = R.quantize(R.oracle("affine", x+6, y+10))
    below, seen, ranks = R.rank_oracle()
    def valid(name, pixels, kind, **kwargs):
        path = write(name, pixels, kind, **kwargs)
        decoded, evidence = R.read_tiff(path, kind, pixels.shape, sha(path))
        R.require(np.array_equal(decoded, pixels), "own parser payload mismatch")
        R.require(np.array_equal(decoded, tifffile.imread(path)), "independent tifffile cross-read mismatch")
        if kind == "rgb":
            evidence["oracle"] = R.coordinate_check(decoded, "constant" if "constant" in name else "affine")
        else:
            evidence["oracle"] = R.rank_check(decoded, below, seen)
        return evidence

    # Constant first: this instrument must reject false structure on its null.
    case("constant-rgb-little-endian-multistrip", lambda: valid("constant", constant, "rgb"))
    case("affine-rgb-big-endian-explicit-orientation", lambda: valid("affine-big", affine, "rgb", endian=">", orientation=1))
    case("affine-rgb-single-strip", lambda: valid("affine-single", affine, "rgb", rows=32))
    case("rank-gray-big-endian-multistrip", lambda: valid("rank-big", ranks, "gray", endian=">", rows=3))
    case("rank-raw-oracle-predeclared", lambda: R.require(
        below[0].tolist() == [0,0,1,3,3,3,4,5]*2 and seen[0].tolist() == [5]*16 and
        ranks[0].tolist() == [0,0,400,800,800,800,400,0]*2, "predeclared independent ranks"))
    sentinel = ranks.copy()
    sentinel[3, 5] = 65535
    sentinel_seen = seen.copy()
    sentinel_seen[3, 5] = 0
    def sentinel_valid():
        path = write("sentinel-rechosen", sentinel, "gray", rows=4)
        pixels, evidence = R.read_tiff(path, "gray", (8,16), sha(path))
        evidence["oracle"] = R.rank_check(pixels, below, sentinel_seen, 3*16+5)
        R.require(int(pixels[0,0]) == 0, "reached-zero companion")
        return evidence
    case("sentinel-rechosen-valid", sentinel_valid)
    base = (files / "affine-single.tiff").read_bytes()
    def broken(name, raw):
        path = files / (name + ".tiff")
        path.write_bytes(raw)
        R.read_tiff(path, "rgb", (32,48,3), sha(path))
    mutations = {
        "orientation8": add_tag(base,274,3,1,8),
        "icc": add_tag(base,34675,4,1,0),
        "transfer-table": add_tag(base,301,3,1,0),
        "unknown-tag": add_tag(base,65000,3,1,1),
        "duplicate-width": add_tag(base,256,4,1,48),
        "sample-float": add_tag(base,339,3,1,3),
        "description": base.replace(b"NO colour matrix", b"XX colour matrix"),
        "software": base.replace(b"strehl 0.0.0", b"strehl 0.0.1"),
        "photometric": edit_tag(base,262,value=1),
        "compression": edit_tag(base,259,value=5),
        "planar": edit_tag(base,284,value=2),
        "predictor": add_tag(base,317,3,1,2),
        "bits": edit_tag(base,258,count=1,value=8),
        "width": edit_tag(base,256,value=47),
        "strip-offset": edit_tag(base,273,value=len(base)+100),
        "strip-bytecount": edit_tag(base,279,value=3),
        "truncated": base[:-1],
        "appended": base+b"X",
        "ifd-at-header": base[:4]+struct.pack("<I",0)+base[8:],
        "wrong-magic": base[:2]+struct.pack("<H",43)+base[4:],
    }
    second_ifd = bytearray(base)
    ifd = struct.unpack_from("<I", base, 4)[0]
    count = struct.unpack_from("<H", base, ifd)[0]
    struct.pack_into("<I", second_ifd, ifd+2+count*12, ifd)
    mutations["extra-ifd"] = bytes(second_ifd)
    multi = bytearray((files / "constant.tiff").read_bytes())
    mifd = struct.unpack_from("<I", multi, 4)[0]
    for i in range(struct.unpack_from("<H", multi, mifd)[0]):
        at = mifd+2+12*i
        if struct.unpack_from("<H", multi, at)[0] == 273:
            ptr = struct.unpack_from("<I", multi, at+8)[0]
            multi[ptr+4:ptr+8] = multi[ptr:ptr+4]
    mutations["overlapping-strips"] = bytes(multi)
    for name, raw in mutations.items():
        case("reject-"+name, lambda name=name,raw=raw: broken(name,raw), True)
    case("wrong-external-sha", lambda: R.read_tiff(files/"affine-single.tiff", "rgb",(32,48,3),"0"*64), True)
    case("wrong-caller-shape", lambda: R.read_tiff(files/"affine-single.tiff", "rgb",(32,47,3)), True)
    case("oversize-before-parse", lambda: broken("oversize",base+b"x"*R.LIMIT), True)

    yy, xx = np.mgrid[14:18,14:34]
    expected = R.oracle("affine",xx+6,yy+10)
    wrong = {
        "omit-crop":R.oracle("affine",xx,yy),
        "double-crop":R.oracle("affine",xx+12,yy+20),
        "half-x":R.oracle("affine",xx+6.5,yy+10),
        "half-y":R.oracle("affine",xx+6,yy+10.5),
        "swap-offsets":R.oracle("affine",xx+10,yy+6),
        "transpose":R.oracle("affine",yy+10,xx+6),
        "reflect-x":R.oracle("affine",63-(xx+6),yy+10),
        "reflect-y":R.oracle("affine",xx+6,47-(yy+10)),
        "swap-red-blue":expected[...,[2,1,0]],
        "omit-wb":expected/np.array([float(np.float32(4/3)),1,float(np.float32(5/3))]),
        "second-black":expected-512,
    }
    parity = expected.copy()
    parity[0,0,1] = 2700
    wrong["concrete-rggb-grbg"] = parity
    for name, value in wrong.items():
        case("oracle-destroyer-"+name, lambda value=value:R.coordinate_check(affine,"affine",value),True)
    corrupt = affine.copy()
    corrupt[14,14,0] += 100
    def pixel_corrupt():
        path=write("rehashed-pixel",corrupt,"rgb")
        pixels,_=R.read_tiff(path,"rgb",(32,48,3),sha(path))
        R.coordinate_check(pixels,"affine")
    case("rehashed-valid-payload-wrong-value",pixel_corrupt,True)
    mutated_dn = R.oracle("affine",x+6,y+10)
    mutated_dn[16,23,1] += 64
    mutation = R.quantize(mutated_dn)
    case("green-plus64-valid",lambda:R.mutation_check(affine,mutation))
    case("green-plus64-noop-refused",lambda:R.mutation_check(affine,affine),True)
    case("green-plus64-clipped-refused",lambda:R.mutation_check(affine,np.full_like(affine,65535)),True)
    case("half-up-versus-even-power",lambda:R.require(
        int(R.quantize((2.5/65535)*R.RANGE))==3 and int(np.rint(2.5))==2,"quantizer tie power"))
    rank_faults=[]
    wrong_b=np.tile([0,1,3,3,3,4,5,5],(8,2)).astype(np.uint32)
    rank_faults.append(("less-equal",wrong_b,seen))
    for name,values in (("red-luma",[700]*5),("blue-luma",[900]*5),("drop-duplicate",[100,200,400,500])):
        b,s,_=R.rank_oracle(values)
        rank_faults.append((name,b,s))
    for name,b,s in rank_faults:
        code=np.floor((1-2*np.abs(b.astype(float)/s-.5))*1000+.5).astype(np.uint16)
        case("rank-count-destroyer-"+name,lambda code=code,b=b,s=s:R.rank_check(code,b,s),True)
    scaled=np.floor(ranks.astype(float)*65535/1000+.5).astype(np.uint16)
    case("rank-65535-scale",lambda:R.rank_check(scaled,below,seen),True)
    case("sentinel-omitted",lambda:R.rank_check(ranks,below,sentinel_seen,53),True)
    moved=sentinel.copy(); moved[3,5]=800; moved[3,6]=65535
    case("sentinel-moved",lambda:R.rank_check(moved,below,sentinel_seen,53),True)
    lost_zero=sentinel.copy(); lost_zero[0,0]=65535
    case("reached-zero-corrupt",lambda:R.rank_check(lost_zero,below,sentinel_seen,53),True)
    case("genuine-confidence-valid",lambda:R.genuine_confidence_check(ranks,(8,16)))
    case("genuine-confidence-unseen",lambda:R.genuine_confidence_check(sentinel,(8,16)),True)
    bad_scale=ranks.copy();bad_scale[0,0]=1000
    case("genuine-confidence-wrong-scale",lambda:R.genuine_confidence_check(bad_scale,(8,16)),True)
    result.update(source_after={str(p.relative_to(ROOT)):sha(p) for p in sources},
                  wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,
                  ended_utc=datetime.now(timezone.utc).isoformat())
    result["source_unchanged"] = result["source_before"] == result["source_after"]
    result["passed"] = sum(c["passed"] for c in result["cases"])
    result["count"] = len(result["cases"])
    result["status"] = "PASS_READER_INSTRUMENT_ONLY" if result["passed"]==result["count"] and result["source_unchanged"] else "FAIL_READER_INSTRUMENT"
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],passed=result["passed"],count=result["count"],result_sha256=sha(out/"result.json"))))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
