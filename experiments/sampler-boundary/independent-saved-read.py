"""Saved-bit interpretation only; never imports or runs the sampler/controller.
Run only after root releases exact saved evidence. Independent source prep.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time

START = time.monotonic()
CPU = time.process_time()
READ_CAP = 128 << 20
TOTAL_CAP = 768 << 20
OUTPUT_CAP = 8 << 20
READS = []
TOTAL = 0
GROUPS = dict(support=6, boundary=126, null=18, nonfinite=36, tiny=48,
              unchecked=60, **{"unchecked-tiny":20, "constructor":4,
              "lanczos-commission":18, "cubic-limiter":6, "gather":2})
KERNELS = [("nearest", .5), ("bilinear", 1), ("catmull-rom", 2),
           ("clamped-catmull-rom", 2), ("lanczos2", 2), ("lanczos3", 3)]
SIZES = [(1,1),(1,7),(7,1),(2,2),(3,3),(4,4),(5,5),(6,6)]
BOUNDARY_NAMES = ["low-corner","low-x","low-y","interior-quarter","interior-half",
 "last-integer","high-x-quarter","high-x-half","high-y-quarter","high-y-half",
 "high-corner-quarter","high-corner-half","exact-upper-corner","just-low-x",
 "just-low-y","just-high-x","just-high-y","distant-low-x","distant-low-y",
 "distant-high-x","distant-high-y"]
UNCHECKED_NAMES = ["high-x-quarter","high-y-quarter","endpoint-x","endpoint-y",
 "endpoint-corner","far-high-x","far-high-y","far-high-corner","far-low-corner",
 "interior-quarter"]
FAILURES = []

def bound():
    if time.process_time()-CPU > 10 or time.monotonic()-START > 15:
        raise RuntimeError("prospective saved-read time cap exceeded")

def read(path):
    global TOTAL
    bound()
    p = Path(path).resolve(strict=True)
    n = p.stat().st_size
    if not (0 <= n <= READ_CAP and TOTAL+n <= TOTAL_CAP):
        raise RuntimeError("prospective saved-read byte cap")
    raw = p.read_bytes()
    if len(raw) != n:
        raise RuntimeError("saved file changed while reading")
    TOTAL += n
    READS.append(dict(path=str(p),bytes=n,sha256=hashlib.sha256(raw).hexdigest()))
    bound()
    return raw

def need(condition, message):
    if not condition:
        FAILURES.append(message)

def f32(value):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError("invalid saved f32 word")
    return struct.unpack(">f",struct.pack(">I",value))[0]

def f64(value):
    if type(value) is not int or not 0 <= value < 2**64:
        raise ValueError("invalid saved f64 word")
    return struct.unpack(">d",struct.pack(">Q",value))[0]

def finite(v):
    return v is not None and math.isfinite(v)

def same_coordinate(actual, expected):
    return math.isnan(actual) if math.isnan(expected) else actual == expected

def truth(x,y):
    return 1000+8*x+16*y

def record(kernel,group,site,x=0.,y=0.,w=128,h=96,effective=None):
    return dict(id=kernel+"-"+group+"-"+site, kernel=kernel, group=group,
                x=x,y=y,w=w,h=h,effective=effective)

def population():
    rows=[]
    for name,support in KERNELS:
        rows.append(record(name,"support","literal"))
        low=support-.5
        highx=127.5-support
        highy=95.5-support
        ux=126 if name=="nearest" else 127-support
        uy=94 if name=="nearest" else 95-support
        lx,ly=(127,95) if name=="nearest" else (ux,uy)
        points=[(low,low),(low,20.25),(20.25,low),(20.25,20.25),(20.5,20.5),
          (lx,ly),(ux+.25,20.25),(ux+.5,20.25),(20.25,uy+.25),
          (20.25,uy+.5),(ux+.25,uy+.25),(ux+.5,uy+.5),(highx,highy),
          (low-.25,20.25),(20.25,low-.25),(highx+.25,20.25),
          (20.25,highy+.25),(-50,20.25),(20.25,-50),(178,20.25),(20.25,146)]
        rows += [record(name,"boundary",site,x,y)
                 for site,(x,y) in zip(BOUNDARY_NAMES,points)]
        rows += [record(name,"null",site,x,y) for site,x,y in
                 [("low",low,low),("interior",20.25,20.25),("upper",highx,highy)]]
        for label,value in [("nan",float("nan")),("positive-infinity",float("inf")),
                            ("negative-infinity",-float("inf"))]:
            rows += [record(name,"nonfinite",label+"-x",value,20.25),
                     record(name,"nonfinite",label+"-y",20.25,value)]
        rows += [record(name,"tiny",str(w)+"x"+str(h),(w-1)/2,(h-1)/2,w,h)
                 for w,h in SIZES]
        ex,ey=(127,95) if name=="nearest" else (128-support,96-support)
        points=[(ex-.75,20.25),(20.25,ey-.75),(ex,20),(20,ey),(ex,ey),
                (178,20),(20,146),(178,146),(-50,-50),(20.25,20.25)]
        rows += [record(name,"unchecked",site,x,y)
                 for site,(x,y) in zip(UNCHECKED_NAMES,points)]
    for index,(name,_) in enumerate(KERNELS):
        if index==0:
            continue
        shapes=[(1,7,0),(7,1,0)]
        if index>=2:
            shapes += [(2,7,1),(7,2,1)]
        if index==5:
            shapes += [(4,7,2),(7,4,2)]
        rows += [record(name,"unchecked-tiny",str(w)+"x"+str(h),w+50,h+50,w,h,eff)
                 for w,h,eff in shapes]
    for site in ["empty-both","empty-width","empty-height","short-data"]:
        rows.append(dict(id="plane-constructor-"+site,group="constructor",kernel="none",
                         x=0,y=0,w=128,h=96))
    for name in ["lanczos2","lanczos3"]:
        for phase,label in [(.25,"quarter"),(.5,"half")]:
            for axis,dx,dy in [("x",7,0),("y",0,5),("corner",7,5)]:
                rows.append(record(name,"lanczos-commission",axis+"-"+label,
                                   20+dx+phase,20+dy+phase))
        for site,x,y in [("wrong-translation",20.25,20.25),("wrong-phase",20.5,20.25),
                         ("restored",20.25,20.25)]:
            rows.append(record(name,"lanczos-commission",site,x,y))
    for site,x,y in [("below",62.5,20.25),("inside",63.5,20.25),("above",64.5,20.25),
                    ("affine-low",1.5,1.5),("affine-interior",20.25,20.5),
                    ("affine-upper",125.5,93.5)]:
        rows.append(record("clamped-catmull-rom","cubic-limiter",site,x,y))
    for site in ["requested-map","opposite-direction-rejected"]:
        rows.append(record("bilinear","gather",site))
    return rows

def transcript(raw):
    records=collections.defaultdict(list)
    order=[]
    for physical in raw.decode("utf-8",errors="strict").splitlines():
        for label in ["BEGIN","ROW","GATHER","SUMMARY"]:
            prefix="SAMPLER_BOUNDARY_"+label+" "
            if physical.startswith(prefix):
                obj=json.loads(physical[len(prefix):],parse_constant=lambda s:
                               (_ for _ in ()).throw(ValueError("non-JSON number")))
                records[label].append(obj)
                order.append(label)
                break
    need(order==["BEGIN"]+["ROW"]*344+["GATHER","SUMMARY"],"complete ordered transcript")
    need(len(records["BEGIN"])==len(records["GATHER"])==len(records["SUMMARY"])==1,
         "unique begin/gather/summary")
    return records

def scalar_review(records):
    rows=records["ROW"]
    expected=population()
    need(len(expected)==344,"independent population size")
    need(dict(collections.Counter(r["group"] for r in expected))==GROUPS,
         "independent group arithmetic")
    need(len(rows)==344,"actual row population")
    need(len({r["id"] for r in rows})==344,"unique actual row IDs")
    summary=records["SUMMARY"][0]
    need(summary["rows"]==344 and summary["groups"]==GROUPS and
         summary["population_complete"] is True,"saved population summary")
    dispositions=collections.Counter()
    observed_failures=[]
    independent_predicates=0
    reported_booleans=[]
    for ordinal,(row,e) in enumerate(zip(rows,expected)):
        bound()
        ident=e["id"]
        for key in ("id","group","kernel"):
            need(row[key]==e[key],ident+" fixed "+key)
        need(row["ordinal"]==ordinal,ident+" ordinal")
        x,y=f64(row["x_f64_bits"]),f64(row["y_f64_bits"])
        need(same_coordinate(x,e["x"]) and same_coordinate(y,e["y"]),ident+" coordinate")
        a,b=f32(row["actual_f32_bits"]),f32(row["oracle_f32_bits"])
        literal=f64(row["oracle_f64_bits"]) if row["oracle_f64_bits"] is not None else None
        need(type(row["passed"]) is bool and type(row["exercised"]) is bool,
             ident+" typed disposition")
        kind=row["actual_kind"]
        need((kind=="finite" and finite(a)) or (kind=="nonfinite" and a is not None and
              not math.isfinite(a)) or (kind in ("refused","panic","true","false") and a is None),
             ident+" actual kind agrees with raw bits")
        group=e["group"]
        expected_api = {
            "support":"metadata-or-consumer", "constructor":"metadata-or-consumer",
            "gather":"metadata-or-consumer",
            "unchecked-tiny":"sample-endpoint-and-far-high",
            "cubic-limiter":"sample_checked-raw-and-limited",
        }.get(group)
        if group=="lanczos-commission":
            expected_api="sample_checked-destroyer" if "wrong-" in ident else "sample_checked-pair"
        if expected_api is not None:
            need(row["api"]==expected_api,ident+" API")
        expected_kind=None
        predicted=None
        tol=row["tolerance_code_units"]
        derived_literal=None
        oracle=row["oracle_kind"]
        if group in ("boundary","tiny","unchecked","null","nonfinite"):
            support=dict(KERNELS)[e["kernel"]]
            checked=group!="unchecked"
            covered=(math.isfinite(x) and math.isfinite(y) and
                     support-.5<=x<=e["w"]-.5-support and
                     support-.5<=y<=e["h"]-.5-support)
            need(row["api"]==("sample_checked" if checked else "sample"),ident+" API")
            if checked and not covered:
                expected_kind="refused"
                predicted=kind=="refused"
                need(tol==0,ident+" refusal tolerance")
            elif group=="null":
                expected_kind="literal"
                derived_literal=-4321.25
                need(tol==(1/32 if e["kernel"].startswith("lanczos") else 0),ident+" null tolerance")
            else:
                rx,ry=x,y
                if not checked:
                    low=max(0,support-1)
                    ex=e["w"]-1 if e["kernel"]=="nearest" else e["w"]-support
                    ey=e["h"]-1 if e["kernel"]=="nearest" else e["h"]-support
                    rx=min(max(x,low),ex)
                    ry=min(max(y,low),ey)
                if e["kernel"]=="nearest":
                    expected_kind="literal"
                    derived_literal=truth(math.floor(rx+.5),math.floor(ry+.5))
                    need(tol==0,ident+" nearest tolerance")
                elif not e["kernel"].startswith("lanczos") or (float(rx).is_integer() and float(ry).is_integer()):
                    expected_kind="literal"
                    derived_literal=truth(rx,ry)
                    need(tol==1/32,ident+" literal tolerance")
                else:
                    expected_kind="translated-stencil"
                    need(tol==1/32,ident+" pair tolerance")
        elif group=="unchecked-tiny":
            expected_kind="effective-fallback-endpoint"
            decrement=2 if e["effective"]==2 else 1
            ex,ey=e["w"]-decrement,e["h"]-decrement
            derived_literal=truth(ex,ey)
            need(tol==(0 if e["effective"]==0 else 1/32),ident+" fallback tolerance")
            old=None if e["effective"]==0 else truth(ex-1,ey-1)
            predicted=(finite(a) and finite(b) and abs(a-derived_literal)<=tol and
                       abs(b-derived_literal)<=tol and row["actual_f32_bits"]==row["oracle_f32_bits"]
                       and (old is None or (abs(a-old)>.25 and abs(b-old)>.25)))
        elif group=="lanczos-commission":
            if "wrong-" in ident:
                expected_kind="must-differ"
                predicted=finite(a) and finite(b) and abs(a-b)>.25
                need(tol==.25,ident+" destroyer threshold")
                if ident.endswith("wrong-translation"):
                    need(literal==12288,ident+" reported changed-input population")
            else:
                expected_kind="translated-stencil"
                need(tol==1/32,ident+" paired tolerance")
        elif group=="cubic-limiter":
            tap_values=[truth(ix,iy) for iy in range(math.floor(y)-1,math.floor(y)+3)
                        for ix in range(math.floor(x)-1,math.floor(x)+3)]
            if "affine-" in ident:
                expected_kind="in-hull-bit-identity"
                predicted=(finite(a) and finite(b) and min(tap_values)<=b<=max(tap_values)
                           and row["actual_f32_bits"]==row["oracle_f32_bits"])
            else:
                expected_kind="literal-support-hull"
                step=[0 if ix<64 else 100 for ix in range(math.floor(x)-1,math.floor(x)+3)]
                site=ident.rsplit("-",1)[1]
                derived_literal={"below":0,"inside":50,"above":100}[site]
                branch=(finite(b) and (b<min(step) if site=="below" else
                        b>max(step) if site=="above" else min(step)<=b<=max(step)))
                need(row["exercised"]==branch,ident+" reconstructed limiter exercise")
                predicted=(finite(a) and a==derived_literal and min(step)<=a<=max(step)
                           and (site!="inside" or row["actual_f32_bits"]==row["oracle_f32_bits"]))
            need(tol==0,ident+" cubic exact tolerance")
        else:
            expected_kind="true"
            predicted=kind=="true"
            reported_booleans.append(ident)
            need(tol==0,ident+" boolean tolerance")
        need(oracle==expected_kind,ident+" oracle role")
        if derived_literal is not None:
            need(literal==derived_literal,ident+" independent literal")
        if predicted is None and expected_kind=="literal":
            predicted=finite(a) and abs(a-derived_literal)<=tol
        if predicted is None and expected_kind=="translated-stencil":
            predicted=finite(a) and finite(b) and abs(a-b)<=tol
        if predicted is not None:
            need(row["passed"]==(row["exercised"] and predicted),ident+" saved operand predicate")
            independent_predicates+=1
        dispositions[(group,kind,row["passed"])]+=1
        if not row["passed"]:
            observed_failures.append(dict(id=ident,kind=kind,exercised=row["exercised"],
              actual=a if finite(a) else None,oracle=literal,
              paired=b if finite(b) else None,x="nonfinite" if not math.isfinite(x) else x,
              y="nonfinite" if not math.isfinite(y) else y))
    actual_failed=sum(not row["passed"] for row in rows)
    need(summary["failed"]==actual_failed and summary["passed"]==344-actual_failed,
         "actual failure summary")
    return dict(rows=len(rows),failed=actual_failed,passed=344-actual_failed,
                saved_operand_predicates=independent_predicates,
                source_bound_reported_boolean_rows=reported_booleans,
                dispositions=[dict(group=k[0],actual_kind=k[1],passed=k[2],count=v)
                              for k,v in sorted(dispositions.items())],
                failed_rows=observed_failures)

def gather_review(records):
    g=records["GATHER"][0]
    need(g["width"]==128 and g["height"]==96 and g["sampler"]=="bilinear","gather geometry")
    need(g["map"]=="source=(reference.x+0.25,reference.y+0.25)","gather map")
    hx=g["row_major_f32_bits_hex"]
    masks=[g["mask_nibble_lsb_first_hex"],g["expected_mask_nibble_lsb_first_hex"]]
    need(len(hx)==12288*8 and all(len(m)==3072 for m in masks),"full operands extent")
    masks=[[bool(int(m[i//4],16)&(1<<(i%4))) for i in range(12288)] for m in masks]
    values=[f32(int(hx[i:i+8],16)) for i in range(0,len(hx),8)]
    partitions={}
    mismatches=collections.Counter()
    selected=[]
    for i,a in enumerate(values):
        if i%128==0:
            bound()
        y,x=divmod(i,128)
        valid=x in range(1,127) and y in range(1,95)
        if not valid:
            label="refused-border"
        elif x==126 and y==94:
            label="accepted-final-corner"
        elif x==126:
            label="accepted-final-column-without-corner"
        elif y==94:
            label="accepted-final-row-without-corner"
        else:
            label="accepted-interior"
        p=partitions.setdefault(label,dict(count=0,mask_mismatches=0,value_mismatches=0,
              refusal_nan_mismatches=0,wrong_direction_value_mismatches=0,
              finite_residuals={}))
        p["count"]+=1
        for masknum,m in enumerate(masks):
            if m[i]!=valid:
                mismatches["actual_mask" if masknum==0 else "saved_expected_mask"]+=1
        p["mask_mismatches"]+=masks[0][i]!=valid
        if valid:
            # Literal intercept independently incorporates .25*(8+16), avoiding
            # the author's floating-coordinate admission path and census.
            residual=a-(1006+8*x+16*y)
            wrong_residual=a-(994+8*x+16*y)
            bad=not finite(a) or abs(residual)>1/32
            wrong=not finite(a) or abs(wrong_residual)>1/32
            p["value_mismatches"]+=bad
            p["wrong_direction_value_mismatches"]+=wrong
            if math.isfinite(residual):
                key=format(residual,".17g")
                p["finite_residuals"][key]=p["finite_residuals"].get(key,0)+1
            mismatches["values"]+=bad
            mismatches["wrong_direction_values"]+=wrong
        else:
            p["refusal_nan_mismatches"]+=not math.isnan(a)
            mismatches["refusal_non_nan"]+=not math.isnan(a)
        if (x,y) in [(0,0),(1,1),(125,93),(126,1),(1,94),(126,94),(127,95)]:
            selected.append(dict(x=x,y=y,bits=int(hx[i*8:(i+1)*8],16),
                                 finite_value=a if finite(a) else None,covered=masks[0][i]))
    reconstructed=dict(expected_count=sum(p["count"] for k,p in partitions.items()
                                          if k!="refused-border"),
                       observed_count=sum(masks[0]),
                       mask_mismatches=mismatches["actual_mask"],
                       value_mismatches=mismatches["values"],
                       refusal_nan_mismatches=mismatches["refusal_non_nan"],
                       wrong_direction_mask_mismatches=mismatches["actual_mask"],
                       wrong_direction_value_mismatches=mismatches["wrong_direction_values"])
    residuals=[abs(float(r)) for k,p in partitions.items() for r in p["finite_residuals"]]
    reconstructed["max_abs_error"]=max(residuals,default=0.)
    for k,v in reconstructed.items():
        need(g[k]==v,"gather independent "+k)
    need(mismatches["saved_expected_mask"]==0,"saved expected mask equals independent integer mask")
    completed=(g["status"]=="ok" and g["returned_count"]==reconstructed["expected_count"]
               and reconstructed["observed_count"]==reconstructed["expected_count"]
               and mismatches["actual_mask"]==mismatches["refusal_non_nan"]==0)
    good=completed and mismatches["values"]==0
    destroyer=completed and mismatches["wrong_direction_values"]>0
    rows={r["id"]:r for r in records["ROW"]}
    need(rows["bilinear-gather-requested-map"]["passed"]==good,"gather positive full predicate")
    need(rows["bilinear-gather-opposite-direction-rejected"]["passed"]==destroyer,
         "gather direction full predicate")
    return dict(reconstructed=reconstructed,complete_consumer_population=completed,
                positive_coordinate_predicate=good,direction_destroyer=destroyer,
                partitions=partitions,selected_exact_words=selected)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("scalar","gather"))
    parser.add_argument("raw_log")
    parser.add_argument("output")
    args=parser.parse_args()
    source_raw=read(__file__)
    raw=read(args.raw_log)
    records=transcript(raw)
    data=scalar_review(records) if args.mode=="scalar" else gather_review(records)
    bound()
    if time.process_time()-CPU+1>10 or time.monotonic()-START+2>15:
        raise RuntimeError("saved-read final publication reserve unavailable")
    result=dict(schema="sampler-independent-saved-read-v1",mode=args.mode,
       invocation=sys.orig_argv,source=dict(path=str(Path(__file__).resolve()),
         sha256=hashlib.sha256(source_raw).hexdigest()),
       reads=READS,actual_read_bytes=TOTAL,review=data,failures=FAILURES,
       process_cpu_seconds=time.process_time()-CPU,active_wall_seconds=time.monotonic()-START,
       interpretation_complete=not FAILURES)
    encoded=(json.dumps(result,indent=2,allow_nan=False)+"\n").encode()
    if len(encoded)>OUTPUT_CAP:
        raise RuntimeError("review output cap")
    output=Path(args.output)
    with output.open("xb") as f:
        f.write(encoded)
    bound()
    print(json.dumps(dict(output=str(output.resolve()),bytes=len(encoded),
          sha256=hashlib.sha256(encoded).hexdigest(),failures=FAILURES,
          process_cpu_seconds=result["process_cpu_seconds"],
          active_wall_seconds=result["active_wall_seconds"])))
    return 0 if not FAILURES else 1

if __name__=="__main__":
    raise SystemExit(main())
