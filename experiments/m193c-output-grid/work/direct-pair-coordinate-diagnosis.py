"""Saved JSON only; independent exploratory coordinate summaries, no subject imports.

Choices fixed before execution: all eight >=24-match failures; Q8/256 native
centres; edge distances 64/128/256; residual summaries 2/8/32/128 pixels (not
acceptance bars). Gross unfit coordinate alternatives and a calibration-only
median of complex slopes over source baselines >=512 pixels, followed by a
coordinatewise median intercept. This is deliberately not the frozen maximum
consensus estimator. It cannot independently commission or replace that fit.
"""
import hashlib
import json
import math
import pathlib
import statistics
import time

HERE = pathlib.Path(__file__).resolve().parent
INPUT = HERE.parent / "direct-pair-1" / "worker"
OUTPUT = HERE / "direct-pair-coordinate-diagnosis.json"
WIDTH, HEIGHT = 7032, 4688
IDS = ("pair-1-2", "pair-3-4", "pair-4-5", "pair-4-6", "pair-5-6", "pair-5-7", "pair-6-7", "pair-7-8")
sources = []


def read(path):
    raw = path.read_bytes()
    assert len(raw) <= 800000
    sources.append(dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
    return json.loads(raw)


def pct(values):
    ordered = sorted(values)
    return {name: ordered[round(q * (len(ordered) - 1))] for name, q in
            (("min", 0), ("q25", .25), ("median", .5), ("q75", .75), ("max", 1))}


def edge(z):
    return min(z.real, z.imag, WIDTH - 1 - z.real, HEIGHT - 1 - z.imag)


def counts(values):
    return {str(radius): sum(v <= radius for v in values) for radius in (2, 8, 32, 128)}


def median_complex(values):
    return complex(statistics.median(z.real for z in values), statistics.median(z.imag for z in values))


def bbox(points):
    return [min(z.real for z in points), min(z.imag for z in points),
            max(z.real for z in points), max(z.imag for z in points)] if points else None


def spatial(points):
    return dict(bbox=bbox(points), edge_counts={str(r): sum(edge(z) <= r for z in points) for r in (64, 128, 256)},
                grid_4x4=[[sum(min(3, int(z.real * 4 / WIDTH)) == x and min(3, int(z.imag * 4 / HEIGHT)) == y for z in points)
                           for x in range(4)] for y in range(4)], unique_exact=len(set(points)))


def clusters(ref, src):
    # Connected components of <=2 px in BOTH endpoint coordinate spaces.
    parent = list(range(len(ref)))
    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i
    for i in range(len(ref)):
        for j in range(i):
            if abs(ref[i]-ref[j]) <= 2 and abs(src[i]-src[j]) <= 2:
                parent[find(i)] = find(j)
    return sorted([sum(find(i) == root for i in range(len(ref))) for root in {find(i) for i in range(len(ref))}], reverse=True)


def robust(ref, src):
    rr, ss = ref[::2], src[::2]
    slopes = [(rr[i]-rr[j])/(ss[i]-ss[j]) for i in range(len(ss)) for j in range(i) if abs(ss[i]-ss[j]) >= 512]
    assert slopes
    slope = median_complex(slopes)
    intercept = median_complex([r-slope*s for r,s in zip(rr,ss)])
    errors = [abs(r-slope*s-intercept) for r,s in zip(ref,src)]
    return dict(method="calibration-long-baseline-complex-slope-median", source_min_baseline=512,
                slope_count=len(slopes), a=slope.real, b=slope.imag,
                scale=abs(slope), angle_degrees=math.degrees(math.atan2(slope.imag,slope.real)),
                tx=intercept.real, ty=intercept.imag,
                calibration=dict(residual=pct(errors[::2]), counts=counts(errors[::2])),
                holdout=dict(residual=pct(errors[1::2]), counts=counts(errors[1::2])))


def pair(name):
    value = read(INPUT / (name + ".json"))
    rows = value["outcome"]["landmarks"]
    assert value["outcome"]["status"] == "REGISTRATION_REFUSED" and len(rows) >= 24
    assert "no majority landmark consensus" in value["outcome"]["error"]["message"]
    assert all(r["split"] == ("holdout" if i%2 else "calibration") for i,r in enumerate(rows))
    ref = [complex(*r["reference_q8"])/256 for r in rows]
    src = [complex(*r["source_q8"])/256 for r in rows]
    assert all(0 <= z.real < WIDTH and 0 <= z.imag < HEIGHT for z in ref+src)
    distance = [abs(r-s) for r,s in zip(ref,src)]
    alternatives = dict(identity=lambda z:z, xy_swap=lambda z:complex(z.imag,z.real),
                        x_reflect=lambda z:complex(WIDTH-1-z.real,z.imag),
                        y_reflect=lambda z:complex(z.real,HEIGHT-1-z.imag),
                        halve_about_origin=lambda z:z/2, double_about_origin=lambda z:2*z)
    identity_ids = [i for i,d in enumerate(distance) if d <= 2]
    return dict(pair=value["pair"], total=len(rows), calibration=len(ref[::2]), holdout=len(ref[1::2]),
                frozen_required_calibration=max(12, math.ceil(len(ref[::2])/2)),
                identity=dict(displacement=pct(distance), counts=counts(distance),
                              calibration_count=sum(distance[i] <= 2 for i in range(0,len(distance),2)),
                              holdout_count=sum(distance[i] <= 2 for i in range(1,len(distance),2)),
                              indices=identity_ids, reference_spatial=spatial([ref[i] for i in identity_ids]) if identity_ids else None),
                displacement_x=pct([(r-s).real for r,s in zip(ref,src)]), displacement_y=pct([(r-s).imag for r,s in zip(ref,src)]),
                gross_unfit_median_errors={k:statistics.median(abs(r-f(s)) for r,s in zip(ref,src)) for k,f in alternatives.items()},
                reference_spatial=spatial(ref), source_spatial=spatial(src),
                correspondence_cluster_sizes=clusters(ref,src), calibration_cluster_sizes=clusters(ref[::2],src[::2]),
                independent_model=robust(ref,src))


def main():
    started = time.perf_counter()
    rows = [pair(name) for name in IDS]
    features = []
    for index in range(9):
        value = read(INPUT / f"feature-{index}.json")
        points = [complex(*q)/256 for q in value["coordinates_q8"]]
        features.append(dict(local=index, count=len(points), spatial=spatial(points)))
    result = dict(schema="m193c-saved-coordinate-diagnosis-v1", status="EXPLORATORY_SAVED_COORDINATES_ONLY",
                  gauge="source native centres to reference native centres; Q8 divided by 256; no placements admitted",
                  image_or_subject_calls=0, source=dict(path=str(pathlib.Path(__file__)),
                  sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()),
                  inputs=sources, pairs=rows, features=features, elapsed_seconds=time.perf_counter()-started)
    raw = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
    assert len(raw) + pathlib.Path(__file__).stat().st_size < 96*1024
    with OUTPUT.open("xb") as stream:
        stream.write(raw)
    print(json.dumps(dict(output=str(OUTPUT), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          elapsed_seconds=result["elapsed_seconds"])))
    for row in rows:
        model=row["independent_model"]
        print(row["pair"]["id"], "n", row["total"], "identity", row["identity"]["counts"],
              "edge256",row["reference_spatial"]["edge_counts"]["256"], "clusters",len(row["correspondence_cluster_sizes"]),
              "model", round(model["scale"],6), round(model["angle_degrees"],3),
              "cal", model["calibration"]["counts"], "hold",model["holdout"]["counts"])


if __name__ == "__main__":
    main()
