"""Prospective same-channel sampling diversity from one saved f64 map only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAP = HERE / "chip-baseline-1/chip.warpmap.txt"
ALIASES = {"R": np.array([[0,0],[.5,0],[0,.5],[.5,.5]], dtype=np.float64),
           "B": np.array([[0,0],[.5,0],[0,.5],[.5,.5]], dtype=np.float64),
           "G": np.array([[0,0],[.5,.5]], dtype=np.float64)}


def svd(offsets, aliases):
    matrix = np.exp(2j*np.pi*(np.asarray(offsets, dtype=np.float64) @ aliases.T))/np.sqrt(len(offsets))
    values = np.linalg.svd(matrix, compute_uv=False)
    tolerance = values[0]*max(matrix.shape)*np.finfo(np.float64).eps
    rank = int(np.count_nonzero(values > tolerance))
    return dict(singular_values=values.tolist(), rank=rank,
                condition=float(values[0]/values[-1]) if rank == len(aliases) else None)


def xy(z):
    return [float(z.real), float(z.imag)]


def nearest_same_channel(s, channel):
    if channel in ("R", "B"):
        shift = 0 if channel == "R" else 1
        return complex(shift+2*np.round((s.real-shift)/2), shift+2*np.round((s.imag-shift)/2))
    left, top = int(np.floor(s.real)), int(np.floor(s.imag))
    candidates = [complex(x,y) for y in (top,top+1) for x in (left,left+1) if (x+y)%2 == 1]
    return min(candidates, key=lambda p: (abs(p-s), p.real, p.imag))


def main():
    started = time.process_time()
    # Commission first, before reading map: duplicate samples must fail rank;
    # four independent native-pixel parity offsets give orthogonal alias columns.
    controls = {}
    ideal = [[0,0],[1,0],[0,1],[1,1]]
    for channel, aliases in ALIASES.items():
        duplicate = svd(np.zeros((4,2)), aliases)
        orthogonal = svd(ideal, aliases)
        assert duplicate["rank"] == 1 and duplicate["condition"] is None
        assert orthogonal["rank"] == len(aliases)
        assert abs(orthogonal["condition"]-1) < 1e-12
        assert np.max(np.abs(np.array(orthogonal["singular_values"])-1)) < 1e-12
        controls[channel] = dict(duplicate_zero=duplicate, four_parities=orthogonal)
    spec = importlib.util.spec_from_file_location("chip_map_bits", ROOT / "experiments/M-PHASE0-PHASE/src/clib.py")
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    before = hashlib.sha256(MAP.read_bytes()).hexdigest()
    warp = loader.parse_warpmap(str(MAP))  # f64 hex bit patterns, not decimal aids
    assert warp["reference_index"] == 149 and warp["plane"] == (3516,2344)
    frames = list(range(143,156))
    assert all(warp["placements"][i] is not None for i in frames)
    # Corners are first/last pixel centres; centre is their geometric midpoint.
    points = dict(centre=complex(1527.5,1299.5), top_left=complex(1336,1108),
                  top_right=complex(1719,1108), bottom_left=complex(1336,1491),
                  bottom_right=complex(1719,1491))
    centre_native = complex(*warp["plane"])
    sites = {}
    for name, p in points.items():
        rows = []
        for index in frames:
            a, b = warp["placements"][index]
            sx, sy = loader.apply_at(a,b,p.real/2,p.imag/2,warp["plane"][0]/2,warp["plane"][1]/2)
            mapped = 2*complex(sx,sy)
            assert abs(mapped-(a*(p-centre_native)+2*b+centre_native)) < 1e-9
            if index == 149:
                assert abs(mapped-p) < 1e-9
            samples = {}
            for channel in ALIASES:
                sample = nearest_same_channel(mapped,channel)
                offset = (sample-mapped)/a
                pulled_back = centre_native+(sample-centre_native-2*b)/a
                assert abs(pulled_back-p-offset) < 1e-9
                samples[channel] = dict(nearest_source_native=xy(sample), reference_offset_native=xy(offset))
            rows.append(dict(frame=index,mapped_native=xy(mapped),mapped_displacement_native=xy(mapped-p),samples=samples))
        sites[name] = dict(reference_active_native=xy(p),frames=rows)
    groups = []
    for first,last in ((147,151),(145,153),(143,155)):
        by_site = {}
        for name, site in sites.items():
            selected = [r for r in site["frames"] if first <= r["frame"] <= last]
            by_site[name] = {channel:svd([r["samples"][channel]["reference_offset_native"] for r in selected], aliases)
                             for channel,aliases in ALIASES.items()}
        groups.append(dict(first=first,last=last,count=last-first+1,sites=by_site))
    limits = []
    radius = abs(points["top_left"]-points["centre"])
    for index in frames:
        a,_ = warp["placements"][index]
        # Similarity is affine exactly; treating it as translation is the approximation.
        limits.append(dict(frame=index,scale=float(abs(a)),rotation_radians=float(np.angle(a)),
            map_displacement_change_centre_to_corner_native=float(abs(a-1)*radius),
            inverse_reference_lattice_basis_change_per_two_native=float(2*abs(1/a-1))))
    assert hashlib.sha256(MAP.read_bytes()).hexdigest() == before
    elapsed = time.process_time()-started
    assert elapsed < 60
    result = dict(status="PROSPECTIVE_MAP_DIVERSITY_ONLY",map=str(MAP),map_sha256=before,
        source_map_units="plane pixels; 1 plane=2 active native pixels; bit-pattern f64 parsing",
        roi_active_native_xywh=[1336,1108,384,384],reference=149,
        sites_convention="first/last pixel-centre corners and their geometric midpoint",
        alias_columns_cycles_per_reference_native={k:v.tolist() for k,v in ALIASES.items()},
        matrix="exp(2*pi*i*offset.dot(alias))/sqrt(frame_count), offset=(nearest same-channel source site-mapped point)/a",
        controls=controls,groups=groups,sites=sites,local_translation_limits=limits,cpu_seconds=elapsed,
        limits="Local nominal-lattice alias conditioning, not a full affine sampling inversion. No PSF, within-DOF claim, geometric truth, calibrated noise or recoverable-detail claim. Nearest-site choices account for period2 R/B and odd-parity green; clib.site_phases is not used.")
    out = HERE / "chip-local-sample-diversity-1.json"
    with out.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(groups=[dict(first=g["first"],last=g["last"],centre=g["sites"]["centre"]) for g in groups],
        max_centre_to_corner_displacement_change_native=max(v["map_displacement_change_centre_to_corner_native"] for v in limits),
        cpu_seconds=elapsed,bytes=out.stat().st_size)))


if __name__ == "__main__":
    main()
