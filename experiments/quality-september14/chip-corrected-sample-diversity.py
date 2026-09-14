"""Same eight frames/sites/alias bases, nominal vs local source translations."""
from pathlib import Path
import hashlib
import importlib.util
import json
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    started = time.process_time()
    previous = load("same_phase_operator",HERE/"chip-local-sample-diversity.py")
    # Retain the existing model's commissioning, with unchanged periodicity.
    for aliases in previous.ALIASES.values():
        assert previous.svd(np.zeros((4,2)),aliases)["rank"] == 1
        assert abs(previous.svd([[0,0],[1,0],[0,1],[1,1]],aliases)["condition"]-1)<1e-12
    axes = dict(x=np.array([[0,0],[.5,0]],dtype=np.float64),
                y=np.array([[0,0],[0,.5]],dtype=np.float64))
    for aliases in axes.values():
        assert previous.svd(np.zeros((4,2)),aliases)["rank"]==1
        assert abs(previous.svd([[0,0],[1,0],[0,1],[1,1]],aliases)["condition"]-1)<1e-12
    loader = load("same_map_bits",ROOT/"experiments/M-PHASE0-PHASE/src/clib.py")
    map_path = HERE/"chip-baseline-1/chip.warpmap.txt"
    correction_path = HERE/"local-green-translation-1/result.json"
    prior_path = HERE/"chip-local-sample-diversity-1.json"
    hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (map_path,correction_path,prior_path)}
    warp = loader.parse_warpmap(str(map_path))
    correction = json.loads(correction_path.read_text())
    prior = json.loads(prior_path.read_text())
    assert warp["reference_index"]==149 and correction["source_map_sha256"]==hashes[str(map_path)]
    frames = list(range(146,154))
    deltas = {r["frame"]:complex(*r["delta_source_native"]) for r in correction["frames"]}
    assert deltas[149]==0
    assert all(not r["at_translation_bound"] for r in correction["frames"] if r["frame"] in frames)
    centre_native = complex(*warp["plane"])
    sites = {}
    for name,old_site in prior["sites"].items():
        p = complex(*old_site["reference_active_native"])
        arms = {}
        for arm in ("nominal-eight","corrected-eight"):
            rows = []
            for index in frames:
                a,b_plane = warp["placements"][index]
                delta = deltas[index] if arm=="corrected-eight" else 0j
                # delta is SOURCE native, so add delta/2 to plane b before mapping.
                b_corrected = b_plane+delta/2
                mapped = centre_native+a*(p-centre_native)+2*b_corrected
                offsets = {}
                for channel in previous.ALIASES:
                    nearest = previous.nearest_same_channel(mapped,channel)
                    offset = (nearest-mapped)/a
                    pulled_back = centre_native+(nearest-centre_native-2*b_corrected)/a
                    assert abs(pulled_back-p-offset)<1e-9
                    offsets[channel] = previous.xy(offset)
                rows.append(dict(frame=index,mapped_native=previous.xy(mapped),
                    mapped_displacement_native=previous.xy(mapped-p),reference_sample_offsets_native=offsets))
            conditions = {channel:previous.svd([r["reference_sample_offsets_native"][channel] for r in rows],aliases)
                          for channel,aliases in previous.ALIASES.items()}
            axial = {channel:{axis:previous.svd([r["reference_sample_offsets_native"][channel] for r in rows],aliases)
                              for axis,aliases in axes.items()} for channel in ("R","B")}
            displacements = np.array([r["mapped_displacement_native"] for r in rows])
            arms[arm] = dict(alias_svd=conditions,rb_axis_alias_svd=axial,frames=rows,
                mapped_displacement_min_native=displacements.min(axis=0).tolist(),
                mapped_displacement_max_native=displacements.max(axis=0).tolist(),
                mapped_displacement_span_native=np.ptp(displacements,axis=0).tolist())
        sites[name] = dict(reference_active_native=previous.xy(p),arms=arms)
    elapsed = time.process_time()-started
    assert elapsed<60
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())
    result = dict(status="SAME_EIGHT_CORRECTED_PHASE_GEOMETRY",frames=frames,reference=149,
        source_hashes=hashes,sites=sites,cpu_seconds=elapsed,
        correction="SOURCE native delta added to2*b_plane; a unchanged; nearest same-colour offsets divided by a",
        alias_bases={k:v.tolist() for k,v in previous.ALIASES.items()},rb_axis_alias_bases={k:v.tolist() for k,v in axes.items()},
        axis_interpretation="Two-column x/y alias subproblems of period2 R/B; not separate green-axis recovery claims",
        caveats="Same nominal local-translation alias approximation as prior diagnostic, not a full affine inversion. Local guide fits may absorb blur/PSF changes; green-derived nuisance fits are not geometry truth or chromatic calibration. No depth-of-field, noise, solver or image-quality conclusion follows from rank alone. Original maps and correction file are read-only.")
    out = HERE/"chip-corrected-sample-diversity-1.json"
    with out.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write("\n")
    summary = {site:{arm:dict(full={k:v["condition"] for k,v in r["alias_svd"].items()},
        rb_axes={k:{ax:v["condition"] for ax,v in vv.items()} for k,vv in r["rb_axis_alias_svd"].items()},
        displacement_span=r["mapped_displacement_span_native"]) for arm,r in entry["arms"].items()}
        for site,entry in sites.items()}
    print(json.dumps(dict(sites=summary,cpu_seconds=elapsed)))


if __name__=="__main__":
    main()
