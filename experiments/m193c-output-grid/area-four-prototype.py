"""Source-only AREA4 representation. No image loading or numerical dependency import."""
import hashlib

FACTOR = 4
CENTRE_Q8 = 384
METHOD = "m193c-area4-native-centres-v1"
CONTROL_IDS = ("area4-half-ties", "repeated-block-null", "native-rotation-positive",
               "native-two-pixel-map-destroyer", "centre-offset-destroyer",
               "native-rotation-restored", "rotation-observer-null")
QUALIFIER = dict(coordinate_gauge="native pixel centres; q_native=4*q_coarse+384",
    coordinate_lattice_step_q8=4, inherited_quantization_guard_q8=1,
    guard_status="UNQUALIFIED_FOR_COARSE_LATTICE",
    scope="Diagnostic direct fit only; no support, overlap, placement or quality admission")


def area4(np, rgb):
    if rgb.dtype != np.dtype("uint16") or rgb.ndim != 3 or rgb.shape[2] != 3 or not rgb.flags.c_contiguous:
        raise ValueError("AREA4 requires contiguous RGB u16")
    height,width,_ = rgb.shape
    if height <= 0 or width <= 0 or height%4 or width%4:
        raise ValueError("AREA4 exact divisible dimensions")
    # At most16*65535; accumulate exactly, then round once, ties to even.
    total = rgb.reshape(height//4,4,width//4,4,3).sum(axis=(1,3),dtype=np.uint32)
    quotient,remainder = total >> 4,total & 15
    rounded = quotient + ((remainder > 8) | ((remainder == 8) & ((quotient & 1) == 1)))
    return rounded.astype(np.uint16)


def lifted(np, reference, coarse_feature, *, omit_centre=False):
    q = coarse_feature.coordinates_q8
    if q.dtype != np.dtype("int64") or q.ndim != 2 or q.shape[1] != 2:
        raise ValueError("coarse Q8 shape/dtype")
    return reference.FeatureSet(coordinates_q8=q*4+(0 if omit_centre else CENTRE_Q8),
        descriptors=coarse_feature.descriptors,keys=coarse_feature.keys)


def representation(np, rgb):
    coarse = area4(np,rgb)
    receipt = dict(method=METHOD,native_shape=list(rgb.shape),coarse_shape=list(coarse.shape),
        coarse_rgb_sha256_u16_le=hashlib.sha256(coarse.astype("<u2",copy=False).tobytes()).hexdigest(),
        factor=4,centre_q8=384,key_coordinate_gauge="coarse Q8; unchanged detector keys")
    return coarse,receipt


def extract_coarse(np, reference, coarse, receipt):
    feature = reference.extract_features(coarse)
    receipt["coarse_coordinates_q8"] = feature.coordinates_q8.tolist()
    native = lifted(np,reference,feature)
    receipt["native_coordinates_q8"] = native.coordinates_q8.tolist()
    return native,receipt
