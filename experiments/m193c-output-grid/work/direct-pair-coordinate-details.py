"""Follow-up selected after first saved-coordinate summary; JSON only, no subjects.

Retain exact physical-endpoint duplication/split collisions and fixed 4x4
coverage counts. These are descriptive counts, not independent significance
tests or a replacement for the frozen match digest population.
"""
import collections
import hashlib
import json
import math
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
DIRECT = BASE.parent / "direct-pair-1" / "worker"
IDS = ("pair-1-2", "pair-3-4", "pair-4-5", "pair-4-6", "pair-5-6", "pair-5-7", "pair-6-7", "pair-7-8")
inputs = []


def read(path):
    raw = path.read_bytes()
    assert len(raw) < 800000
    inputs.append(dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
    return json.loads(raw)


def distance(p, q):
    return math.hypot(p[0]-q[0], p[1]-q[1])/256


def main():
    result = []
    for name in IDS:
        value = read(DIRECT / (name + ".json"))
        rows = value["outcome"]["landmarks"]
        joint, side_groups = collections.defaultdict(list), {side: collections.defaultdict(list) for side in ("source_q8", "reference_q8")}
        for i, row in enumerate(rows):
            joint[tuple(row["reference_q8"]+row["source_q8"])].append(i)
            for side in side_groups:
                side_groups[side][tuple(row[side])].append(i)
        repeated = []
        for key, ids in joint.items():
            if len(ids) > 1:
                repeated.append(dict(reference_q8=list(key[:2]), source_q8=list(key[2:]), ids=ids,
                                     splits=[rows[i]["split"] for i in ids],
                                     displacement_px=distance(key[:2],key[2:])))
        contradictory = []
        for side, groups in side_groups.items():
            other = "reference_q8" if side == "source_q8" else "source_q8"
            for key, ids in groups.items():
                diameter = max(distance(rows[i][other],rows[j][other]) for i in ids for j in ids)
                if diameter > 4:
                    contradictory.append(dict(fixed_side=side, fixed_q8=list(key), ids=ids,
                                              other_q8=[rows[i][other] for i in ids], other_diameter_px=diameter))
        result.append(dict(pair=value["pair"], repeated_exact_correspondences=repeated,
                           exact_groups_crossing_split=sum(len(set(g["splits"])) == 2 for g in repeated),
                           incompatible_same_point_groups=contradictory,
                           upper_half_reference=sum(r["reference_q8"][1] < 2344*256 for r in rows),
                           lower_quarter_reference=sum(r["reference_q8"][1] >= 3516*256 for r in rows),
                           total=len(rows)))
    features=[]
    for index in range(9):
        value=read(DIRECT/f"feature-{index}.json")
        pts=value["coordinates_q8"]
        features.append(dict(local=index,total=len(pts), unique_locations=len(set(map(tuple,pts))),
                             upper_half=sum(p[1] < 2344*256 for p in pts),
                             lower_quarter=sum(p[1] >= 3516*256 for p in pts)))
    receipt=dict(schema="m193c-saved-coordinate-details-v1", status="POST_SUMMARY_DESCRIPTIVE_ONLY",
                 source=dict(path=str(pathlib.Path(__file__)), sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()),
                 inputs=inputs, pairs=result, features=features, image_or_subject_calls=0)
    raw=(json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    assert len(raw)<24000
    output=BASE/"direct-pair-coordinate-details.json"
    with output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps(dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
    for row in result:
        print(row["pair"]["id"],"crosssplit",row["exact_groups_crossing_split"],"incompatible",row["incompatible_same_point_groups"],
              "upperhalf",row["upper_half_reference"],"lowerquarter",row["lower_quarter_reference"],"total",row["total"])
    print("feature_regions",features)


if __name__=="__main__":
    main()
