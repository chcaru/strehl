"""M102 -- shared library for the calibrated simulator.

Contains the DNG writer (so a synthetic stack enters the pipeline through the
*same* decode path a real capture does) and the measured rig constants, each
carrying the SYNTHESIS fact number that established it.

EVERY CONSTANT IN THIS FILE IS CITED. A simulator built on invented numbers is
a random number generator with good manners; the citations are what make it
falsifiable against the corpus rather than against taste.
"""
import os
import struct
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_EXP, "M92-null-averaging", "src"),
           os.path.join(_EXP, "m57-shape-metric", "src"),
           os.path.join(_EXP, "m41-r3-kill", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ROOT = r"D:\personal\macro"
DARKS = r"D:\macro-dark-frames"
OUT = os.path.join(os.path.dirname(_HERE), "out")
WORK = r"C:\dev\strehl-out\M102"

# ---------------------------------------------------------------- rig constants
# Sensor geometry. AGENTS.md rig section: "Pixel pitch 5.12 um. RGGB.
# Black level 512, white level 15360." The white level is corroborated in
# code at crates/strehl-core/src/noise.rs:418 -- "Measured, M1: rawler
# reports 15360 for the A7C II, not 16383."
PITCH_UM = 5.12
BLACK = 512
WHITE = 15360
CFA_RGGB = (0, 1, 1, 2)

# Wavelength. NOT independently measured by this project -- it is DERIVED
# here by inverting fact 12's own extinction point. Fact 12 states the
# diffraction cutoff `pitch/(lambda*N_eff)` reaches Nyquist at N_eff = 18.6.
# Solving 0.5 = 5.12/(lambda*18.6) gives lambda = 0.5505 um. Using 0.55
# reproduces fact 12's extinction to three digits, which is the agreement
# fact 12 itself claims. Recorded as a derived quantity, not a measured one.
LAMBDA_UM = 0.55

# Optics. Fact 27: bellows factor B = (1 + m/p), measured 2.41-3.06.
# Fact 12: at m = 2.0 the rig sits at N_eff 16.8, and 16.8 = 5.6 * 3.0,
# so the m = 2.0 configuration is B = 3.0, i.e. p = 1.0.
MAG = 2.0
PUPIL_P = 1.0
N_MARKED = 5.6

# Fact 144 (MEASURED): best-frame MTF at 0.25 cyc/px, by marked aperture.
# This is the realism target the diffraction model must reproduce.
MTF_AT_QUARTER = {4.0: 0.598, 5.6: 0.447, 8.0: 0.242, 11.0: 0.046, 16.0: 0.0}

# Fact 27 (MEASURED): the green-quincunx knee at f/11.
F_SIG_F11 = 0.2762

# Breathing. Fact 1177 (MEASURED): bee-3-cpl drifts 232.7 px raw over 299
# frames on a smooth monotonic track. Fact 1254 (MEASURED): that is 232.7 px
# over a 4226 px half-diagonal, and irradiance falls as 1/m^2, predicting a
# 1.1132 brightness ratio against 1.1091 measured.
DRIFT_PX = 232.7
HALF_DIAG_PX = 4226.0
PHOTOMETRIC_RATIO = 1.1091          # fact 1254, MEASURED
PHOTOMETRIC_PREDICTED = 1.1132      # fact 1254, DERIVED from geometry

# Fact 1263 (MEASURED): 25.247% of bee-3-cpl pixels have a disconnected
# competitive set, mean gap 29.12 frames. A realism target, not an input.
DISCONNECTED_FRAC = 0.25247
MEAN_GAP_FRAMES = 29.12


def scale_track(n_frames, drift_px=DRIFT_PX, half_diag=HALF_DIAG_PX):
    """Per-frame magnification relative to frame 0.

    Fact 1177 measured the track as smooth and monotonic, so this is linear
    in frame index rather than a random walk. Total radial displacement at
    the half-diagonal is `drift_px`, hence a fractional scale change of
    `drift_px / half_diag` accumulated across the stack.
    """
    t = np.arange(n_frames, dtype=np.float64) / max(n_frames - 1, 1)
    return 1.0 + (drift_px / half_diag) * t


def photometric_track(scale):
    """Irradiance ratio per frame. Fact 1254: irradiance falls as 1/m^2.

    Returned relative to frame 0, so frame 0 is 1.0 and later frames are
    dimmer -- the direction fact 1254 measured (0.2284 -> 0.2059).
    """
    return (scale[0] / scale) ** 2


def n_eff(marked=N_MARKED, mag=MAG, p=PUPIL_P):
    """Effective f-number. Fact 27: N_eff = N_marked * (1 + m/p)."""
    return marked * (1.0 + mag / p)


def diffraction_cutoff_cyc_px(neff, pitch=PITCH_UM, lam=LAMBDA_UM):
    """Fact 12's cutoff, `pitch/(lambda*N_eff)`, in cycles per pixel."""
    return pitch / (lam * neff)


def diffraction_mtf(f_cyc_px, neff):
    """Incoherent circular-aperture MTF. Standard analytic form."""
    fc = diffraction_cutoff_cyc_px(neff)
    s = np.clip(np.asarray(f_cyc_px, dtype=np.float64) / fc, 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(s) - s * np.sqrt(np.maximum(
        1.0 - s * s, 0.0)))


# ------------------------------------------------------------------ DNG writer
# TIFF type codes
_BYTE, _ASCII, _SHORT, _LONG, _RATIONAL = 1, 2, 3, 4, 5
_SRATIONAL = 10
_SIZE = {_BYTE: 1, _ASCII: 1, _SHORT: 2, _LONG: 4, _RATIONAL: 8,
         _SRATIONAL: 8}


def _pack(typ, values):
    if typ == _ASCII:
        b = values.encode("ascii") + b"\0"
        return b, len(b)
    out = b""
    for v in values:
        if typ == _BYTE:
            out += struct.pack("<B", int(v))
        elif typ == _SHORT:
            out += struct.pack("<H", int(v))
        elif typ == _LONG:
            out += struct.pack("<I", int(v))
        elif typ == _RATIONAL:
            out += struct.pack("<II", int(v[0]), int(v[1]))
        elif typ == _SRATIONAL:
            out += struct.pack("<ii", int(v[0]), int(v[1]))
    return out, len(values)


class _IFD:
    def __init__(self):
        self.entries = []

    def add(self, tag, typ, values):
        blob, count = _pack(typ, values)
        self.entries.append([tag, typ, count, blob])

    def size(self):
        return 2 + 12 * len(self.entries) + 4

    def serialise(self, base, next_ifd=0, heap_at=None):
        """Return (ifd_bytes, heap_bytes).

        `base` is this IFD's file offset; `heap_at` is where the heap will
        actually be written. They are NOT the same when another IFD is
        interleaved between the two, which is exactly the layout used here --
        getting this wrong makes every inline tag correct and every
        heap-resident tag garbage, which is a very convincing kind of wrong.
        """
        self.entries.sort(key=lambda e: e[0])
        heap_off = base + self.size() if heap_at is None else heap_at
        head = struct.pack("<H", len(self.entries))
        heap = b""
        for tag, typ, count, blob in self.entries:
            if len(blob) <= 4:
                val = blob + b"\0" * (4 - len(blob))
            else:
                val = struct.pack("<I", heap_off + len(heap))
                heap += blob
                if len(heap) % 2:
                    heap += b"\0"
            head += struct.pack("<HHI", tag, typ, count) + val
        head += struct.pack("<I", next_ifd)
        return head, heap


def write_dng(path, cfa, iso, black=BLACK, white=WHITE,
              fnumber=N_MARKED, exposure_s=1.0 / 200.0, description=None):
    """Write an uncompressed CFA DNG that `rawler` can decode.

    `cfa` is a (h, w) uint16 array already in sensor DN, black offset
    included. The layout is IFD0-as-raw: NewSubfileType 0, PhotometricInter-
    pretation 32803. This is the layout the spike in S1 verified against the
    shipped decoder rather than the one the spec prefers.
    """
    cfa = np.ascontiguousarray(cfa.astype("<u2"))
    h, w = cfa.shape

    exif = _IFD()
    exif.add(33434, _RATIONAL, [(1, int(round(1.0 / exposure_s)))])
    exif.add(33437, _RATIONAL, [(int(round(fnumber * 10)), 10)])
    exif.add(34855, _SHORT, [int(iso)])
    exif.add(37386, _RATIONAL, [(90, 1)])

    ifd0 = _IFD()
    ifd0.add(254, _LONG, [0])
    if description is not None:
        ifd0.add(270, _ASCII, str(description))
    ifd0.add(256, _LONG, [w])
    ifd0.add(257, _LONG, [h])
    ifd0.add(258, _SHORT, [16])
    ifd0.add(259, _SHORT, [1])
    ifd0.add(262, _SHORT, [32803])
    ifd0.add(271, _ASCII, "SONY")
    ifd0.add(272, _ASCII, "ILCE-7CM2")
    ifd0.add(277, _SHORT, [1])
    ifd0.add(278, _LONG, [h])
    ifd0.add(279, _LONG, [w * h * 2])
    ifd0.add(284, _SHORT, [1])
    ifd0.add(33421, _SHORT, [2, 2])
    ifd0.add(33422, _BYTE, list(CFA_RGGB))
    ifd0.add(50706, _BYTE, [1, 4, 0, 0])
    ifd0.add(50707, _BYTE, [1, 1, 0, 0])
    ifd0.add(50708, _ASCII, "SONY ILCE-7CM2")
    ifd0.add(50710, _BYTE, [0, 1, 2])
    ifd0.add(50711, _SHORT, [1])
    ifd0.add(50713, _SHORT, [1, 1])
    ifd0.add(50714, _RATIONAL, [(int(black), 1)])
    ifd0.add(50717, _LONG, [int(white)])
    ifd0.add(50718, _RATIONAL, [(0, 1), (0, 1)])
    ifd0.add(50719, _LONG, [w, h])
    ifd0.add(50829, _LONG, [0, 0, h, w])
    ifd0.add(50778, _SHORT, [21])
    # A plausible D65 colour matrix. Colour fidelity is explicitly out of
    # scope for this simulator (see the report's "where this simulator lies").
    cm = [(6500, 10000), (-2000, 10000), (-600, 10000),
          (-4000, 10000), (11000, 10000), (3000, 10000),
          (-500, 10000), (1200, 10000), (6000, 10000)]
    ifd0.add(50721, _SRATIONAL, cm)

    # Deterministic layout. Add both offset tags with placeholders FIRST so
    # the entry count -- and therefore every offset -- is final before any
    # offset is computed. Re-serialising after adding a tag would move the
    # heap out from under the offsets already written into it.
    ifd0.add(34665, _LONG, [0])
    ifd0.add(273, _LONG, [0])
    ifd0.add(50728, _RATIONAL, [(1000, 2100), (1000, 1000), (1000, 1500)])

    base0 = 8
    exif_off = base0 + ifd0.size()
    e_head, e_heap = exif.serialise(exif_off)
    ifd0_heap_off = exif_off + len(e_head) + len(e_heap)
    _, i_heap = ifd0.serialise(base0, heap_at=ifd0_heap_off)
    strip_off = ifd0_heap_off + len(i_heap)

    for e in ifd0.entries:
        if e[0] == 34665:
            e[3] = struct.pack("<I", exif_off)
        elif e[0] == 273:
            e[3] = struct.pack("<I", strip_off)
    i_head, i_heap2 = ifd0.serialise(base0, heap_at=ifd0_heap_off)
    assert len(i_heap2) == len(i_heap), "heap moved after patching offsets"

    with open(path, "wb") as fh:
        fh.write(b"II" + struct.pack("<HI", 42, base0))
        fh.write(i_head)
        fh.write(e_head)
        fh.write(e_heap)
        fh.write(i_heap2)
        assert fh.tell() == strip_off, (fh.tell(), strip_off)
        fh.write(cfa.tobytes())
    return path
