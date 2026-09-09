"""Fixed two-RAW inspection; root launches bounded children. No decoder on import."""
from pathlib import Path
import argparse
import importlib.util
import struct
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "experiments/native-background-stroke"
spec = importlib.util.spec_from_file_location("held_background_inspect", OLD / "inspect.py")
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
binding, save, read, array_save = old.binding, old.save, old.read, old.array_save
sampler, SECONDARY = old.sampler, old.SECONDARY
INDICES = (0, 104)
RAW_ROI = (6000, 0, 704, 512)
CONTEXT = (6282, 114, 256, 256)
TARGET = (6310, 164, 196, 160)
PHASES = {"G1": (1, 0), "G2": (0, 1)}

def input_path(index):
    assert index in INDICES
    return old.input_path(index, ".ARW")

def source_bindings():
    return [binding(p) for p in (Path(__file__), OLD/"inspect.py", OLD/"sampler.py", sampler.CLIB_PATH,
        HERE/"charter.md", HERE/"view-1/receipt.json", old.MAP, old.PRODUCT/"run-1/plan.json",
        SECONDARY, old.SECONDARY_SOURCE)]

def fixed():
    assert binding(old.MAP)["sha256"] == old.MAP_SHA
    warp = sampler.clib.parse_warpmap(str(old.MAP))
    assert warp["frames"] == warp["placed_count"] == 105 and not warp["refusals"]
    assert warp["plane"] == (3516, 2344) and warp["reference_index"] == 52
    ox, oy, rw, rh = RAW_ROI
    x, y, w, h = CONTEXT
    tx, ty, tw, th = TARGET
    assert x <= tx and y <= ty and tx+tw <= x+w and ty+th <= y+h
    bounds = []
    for index in INDICES:
        a, b = warp["placements"][index]
        for gauge in ("sensor", "scene"):
            pts = [(float(px),float(py)) for py in (y,y+h-1) for px in (x,x+w-1)]
            if gauge == "scene":
                pts = [tuple(2*v for v in sampler.clib.apply_at(a,b,px/2,py/2,1758,1172)) for px,py in pts]
            # A two-native-pixel margin also covers either green-phase bilinear support.
            assert all(ox+2 <= px <= ox+rw-2 and oy+2 <= py <= oy+rh-2 for px,py in pts)
            bounds.append({"index":index,"gauge":gauge,"context_corners_source_native":pts})
    return bounds

def primary(index, out):
    import rawpy
    fixed()
    path, metadata = input_path(index)
    x, y, w, h = RAW_ROI
    with rawpy.imread(str(path)) as raw:
        patch = raw.raw_image_visible[y:y+h,x:x+w].copy()  # COPY inside LibRaw lifetime.
        pattern = raw.raw_pattern.copy().tolist()
        description = bytes(raw.color_desc).decode("ascii").rstrip("\0")
        assert pattern == [[0,1],[3,2]] and description == "RGBG"
        decoder = {"name":"rawpy/LibRaw","rawpy":rawpy.__version__,"libraw":list(rawpy.libraw_version),
            "visible_shape":list(raw.raw_image_visible.shape),"raw_pattern":pattern,"color_desc":description,
            "black_level_per_channel":list(raw.black_level_per_channel),"white_level":raw.white_level,
            "sizes":{k:int(getattr(raw.sizes,k)) for k in ("raw_height","raw_width","height","width","top_margin","left_margin")}}
    assert patch.shape == (h,w) and patch.dtype == np.uint16
    input_path(index)
    save(out/f"primary-{index}.json", {"index":index,"sources":source_bindings(),"raw_input":binding(path),
        "original_metadata":metadata,"raw_roi_xywh":RAW_ROI,"decoder":decoder,
        "raw":array_save(out/f"raw-{index}.npy",patch)})

def analyze(out):
    bounds = fixed()
    checked, comparisons = [], []
    for index in INDICES:
        receipt = read(out/f"primary-{index}.json")
        assert receipt["index"] == index and receipt["sources"] == source_bindings()
        path, _ = input_path(index)
        assert receipt["raw_input"] == binding(path) and receipt["raw"] == binding(out/f"raw-{index}.npy")
        patch = np.load(out/f"raw-{index}.npy",allow_pickle=False)
        assert patch.dtype == np.uint16 and patch.shape == (512,704)
        secondary = out/"secondary"/f"rawler-frame-{index}.bin"
        blob = secondary.read_bytes()
        assert len(blob) == 720912 and struct.unpack("<4I",blob[:16]) == (0,6000,512,704)
        other = np.frombuffer(blob,dtype="<u2",offset=16).reshape(patch.shape)
        phases = [{"phase_xy":[dx,dy],"different_sensels":int(np.count_nonzero(patch[dy::2,dx::2] != other[dy::2,dx::2])),
            "primary_u16_sha256":old.array_hash(patch[dy::2,dx::2]),"secondary_u16_sha256":old.array_hash(other[dy::2,dx::2])}
            for dy in range(2) for dx in range(2)]
        comparisons.append({"index":index,"primary":receipt["raw"],"secondary":binding(secondary),"phases":phases,
            "different_sensels":int(np.count_nonzero(patch != other)),"clipped_native_white":int(np.count_nonzero(patch>=15360))})
        checked.append((index,receipt,patch))
    save(out/"decode-comparison.json", {"rows":comparisons,"all_identical":all(r["different_sensels"]==0 for r in comparisons)})
    assert all(r["different_sensels"]==0 and r["clipped_native_white"]==0 for r in comparisons), "decode mismatch or clipped support; no interpretation"
    views, files = {}, []
    x,y,w,h = RAW_ROI
    for index,receipt,patch in checked:  # No view exists before BOTH complete decoder comparisons.
        d = receipt["decoder"]
        for name,(dx,dy) in PHASES.items():
            view = patch[dy::2,dx::2].astype(np.float32)
            view -= np.float32(d["black_level_per_channel"][d["raw_pattern"][dy][dx]])
            assert view.shape == (256,352) and np.isfinite(view).all()
            views[(index,name)] = view
            files.append({**array_save(out/f"sensor-{index}-{name}.npy",view), "index":index,"phase":name,"shape":[256,352],"origin_native_xy":[x+dx,y+dy],"spacing_native_xy":[2,2]})
    pooled = np.concatenate([v.ravel() for v in views.values()])
    lo,hi = np.percentile(pooled,[2,98]).tolist()
    from PIL import Image, ImageDraw
    charts = []
    ranges = [("fixed-dn",0.0,14848.0)] + ([("pooled-inspection-only",lo,hi)] if hi > lo else [])
    for label,low,high in ranges:
        canvas = Image.new("RGB",(764,610),"white")
        draw = ImageDraw.Draw(canvas)
        for row,name in enumerate(PHASES):
            for col,index in enumerate(INDICES):
                left,top = 10+382*col,25+286*row
                v = views[(index,name)]
                pixels = np.rint(np.clip((v-low)/(high-low),0,1)*255).astype(np.uint8)
                canvas.paste(Image.fromarray(pixels).convert("RGB"),(left,top))  # One sensel/pixel; no resize.
                dx,dy = PHASES[name]
                draw.text((left,top-15),f"frame {index} / {name}: native origin({x+dx},{y+dy}), step2",fill="black")
                draw.rectangle((left+(TARGET[0]-x)//2,top+(TARGET[1]-y)//2,left+(TARGET[0]+TARGET[2]-x)//2,top+(TARGET[1]+TARGET[3]-y)//2),outline="red")
        draw.text((10,585),f"{label}: {low:.1f}..{high:.1f} DN; full RAW ROI, one original green sensel per pixel",fill="black")
        chart = out/f"contact-{label}.png"
        assert not chart.exists()
        canvas.save(chart)
        charts.append({"image":binding(chart),"range_dn":[low,high],"display_only":True})
    save(out/"result.json", {"status":"DESCRIPTIVE_ONLY","sources":source_bindings(),"indices":INDICES,
        "raw_roi_xywh":RAW_ROI,"views_sensor_native_xywh":RAW_ROI,"context_sensor_native_xywh":CONTEXT,"target_native_xywh":TARGET,
        "metadata_only_scene_support":bounds,"views":files,"charts":charts,
        "sampling":"original G1/G2; one green sensel per display pixel, spacing2native px; no scene resampling",
        "display":"same ranges for all panels; pooled2/98 inspection only, no per-panel stretch",
        "interpretation":"Two originals cannot establish physical dust, noise, quality or a correction policy."})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("primary","analyze"))
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--index",type=int,choices=INDICES)
    args = parser.parse_args()
    assert args.out.is_dir(), "root creates fresh directories"
    if args.stage == "primary":
        assert args.index is not None
        primary(args.index,args.out)
    else:
        analyze(args.out)
