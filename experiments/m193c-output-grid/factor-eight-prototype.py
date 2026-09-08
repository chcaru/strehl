"""SOURCE PROPOSAL ONLY: exact AREA8 representation and native-coordinate evidence.

No CLI, image loading, dependency import, fitting or execution on import.
The future released runner supplies its pinned NumPy and frozen reference.
This file has not been imported or numerically executed before source review.
"""
from collections import defaultdict
from fractions import Fraction
import hashlib
import math

METHOD = "m193c-area8-native-centres-v1"
FACTOR = 8
CENTRE_Q8 = 896  # (8-1)/2 native pixels * 256
Q32 = 1 << 32
CONTROL_IDS = ("area8-half-ties", "repeated-block-null", "native-rotation-positive",
               "native-two-pixel-map-destroyer", "centre-offset-destroyer",
               "native-rotation-restored", "rotation-observer-null")


def area8(np, rgb):
    """Uniform nonoverlapping 8x8 mean, rounded once to nearest-even u16."""
    if rgb.dtype != np.dtype("uint16") or rgb.ndim != 3 or rgb.shape[2] != 3 or not rgb.flags.c_contiguous:
        raise ValueError("AREA8 requires contiguous RGB u16")
    height, width, _ = rgb.shape
    if height <= 0 or width <= 0 or height % 8 or width % 8:
        raise ValueError("AREA8 exact divisible dimensions")
    # Maximum sum is 64*65535 < 2**32. Reshape is a view of contiguous input.
    total = rgb.reshape(height//8,8,width//8,8,3).sum(axis=(1,3), dtype=np.uint32)
    quotient, remainder = total >> 6, total & 63
    rounded = quotient + ((remainder > 32) | ((remainder == 32) & ((quotient & 1) == 1)))
    return rounded.astype(np.uint16)


def lifted(np, reference, coarse_feature, *, omit_centre=False):
    """Only omit_centre=True is the declared private active defect."""
    q = coarse_feature.coordinates_q8
    if q.dtype != np.dtype("int64") or q.ndim != 2 or q.shape[1] != 2:
        raise ValueError("coarse Q8 shape/dtype")
    coordinates = q*8 + (0 if omit_centre else CENTRE_Q8)
    # Actual detector keys stay in their original coarse gauge. A common
    # positive affine coordinate lift preserves their lexicographic ordering.
    return reference.FeatureSet(coordinates_q8=coordinates,
                                descriptors=coarse_feature.descriptors, keys=coarse_feature.keys)


def representation(np, rgb):
    coarse = area8(np, rgb)
    receipt = dict(method=METHOD, native_shape=list(rgb.shape), coarse_shape=list(coarse.shape),
                   coarse_rgb_sha256_u16_le=hashlib.sha256(coarse.astype("<u2", copy=False).tobytes()).hexdigest(),
                   factor=8, centre_q8=896, key_coordinate_gauge="coarse Q8; unchanged detector keys")
    return coarse, receipt


def extract_coarse(np, reference, coarse, receipt):
    # The caller releases its sole native RGB before entering this function.
    feature = reference.extract_features(coarse)
    receipt["coarse_coordinates_q8"] = feature.coordinates_q8.tolist()
    native = lifted(np, reference, feature)
    receipt["native_coordinates_q8"] = native.coordinates_q8.tolist()
    return native, receipt


def rotation_truth():
    """Ref 3072x2304; source is exact native np.rot90(k=1), 2304x3072."""
    return dict(a=0, b=Q32, tx=3071*Q32, ty=0)


def corner_errors(transform):
    """Independent literal oracle, whole source rectangle, native pixel centres."""
    if set(transform) != {"a", "b", "tx", "ty"} or any(type(v) is not int for v in transform.values()):
        raise ValueError("actual Q32 transform schema")
    a,b,tx,ty = (Fraction(transform[k],Q32) for k in ("a","b","tx","ty"))
    errors=[]
    for x,y in ((0,0),(2303,0),(0,3071),(2303,3071)):
        dx = a*x-b*y+tx-(3071-y)
        dy = b*x+a*y+ty-x
        errors.append(dict(source=[x,y], expected=[3071-y,x],
                           squared_error_numerator=(dx*dx+dy*dy).numerator,
                           squared_error_denominator=(dx*dx+dy*dy).denominator,
                           error_native_px=math.hypot(float(dx),float(dy))))
    return errors


def literal_corner_pass(transform):
    return all(row["squared_error_numerator"] <= row["squared_error_denominator"] for row in corner_errors(transform))


def site_evidence(landmarks):
    """Descriptive exact endpoint grouping; never filters/re-splits matches."""
    groups=defaultdict(list)
    sets={side:{split:set() for split in ("calibration","holdout")} for side in ("reference_q8","source_q8")}
    for ordinal,row in enumerate(landmarks):
        split=row["split"]
        if split != ("holdout" if ordinal%2 else "calibration"):
            raise ValueError("unchanged alternating match split")
        key=tuple(row["reference_q8"]+row["source_q8"])
        groups[key].append(ordinal)
        for side in sets:
            sets[side][split].add(tuple(row[side]))
    sides={}
    for side, parts in sets.items():
        points=parts["calibration"]|parts["holdout"]
        sides[side]=dict(unique_total=len(points),calibration_unique=len(parts["calibration"]),
                         holdout_unique=len(parts["holdout"]),
                         exact_locations_shared_between_splits=sorted(parts["calibration"]&parts["holdout"]),
                         bbox_q8=None if not points else [min(p[0] for p in points),min(p[1] for p in points),
                                                        max(p[0] for p in points),max(p[1] for p in points)])
    return dict(scope="descriptive exact coordinate groups; no independence or coverage acceptance claim",
                descriptor_match_count=len(landmarks),exact_joint_groups=len(groups),sides=sides,
                repeated_joint_groups=[dict(reference_q8=list(k[:2]),source_q8=list(k[2:]),ordinals=ids,
                                            split_membership=sorted({landmarks[i]["split"] for i in ids}))
                                       for k,ids in sorted(groups.items()) if len(ids)>1])
