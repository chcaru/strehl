"""Seal one original-CFA signal fixture for conditional incremental-noise controls.

This does not treat an existing noisy exposure as noise-free scene truth. Its
exact pixel values define a fixed experimental signal; fresh independent model
noise is added by the actual core consumer harness. No RAW decoder is invoked.
"""
from pathlib import Path
import hashlib, json, struct
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "outputs/multi-stack/completion/noise-transfer-input-01"
OUT.mkdir(exist_ok=False)
RENDER = ROOT / "outputs/multi-stack/completion/hdr-precision-01"
identities = json.loads((RENDER / "source-identities.json").read_text())
source = identities[30]  # Frozen short-exposure mid-sweep acquisition, no candidate selection.
matches = []
for path in (ROOT / "outputs/multi-stack/completion/hdr-source-cache-current").glob("*.cfa"):
    with path.open("rb") as f:
        prefix = f.read(12)
        assert prefix[:8] == b"STRHCFA1"
        size = struct.unpack("<I", prefix[8:])[0]
        assert size <= 256 * 1024
        raw_header = f.read(size)
        header = json.loads(raw_header)
        if header["source"] == source:
            payload = f.read()
            assert hashlib.sha256(raw_header + payload[:-32]).digest() == payload[-32:]
            matches.append((path, header, payload[:-32]))
assert len(matches) == 1
path, header, payload = matches[0]
g = header["geometry"]
assert (g["width"], g["height"]) == (7032, 4688)
cfa = np.frombuffer(payload, "<u2").reshape(4688, 7032)
# Near the pre-frozen QR witness, in this original sensor's integer gauge. This
# fixture is not registered or claimed equivalent to a saved output crop.
x, y, side = 4008, 448, 256
patch = cfa[y:y+side, x:x+side]
offsets = [(0, 0), (0, 1), (1, 1), (1, 0)]
gain = 2.533541440963745
planes = np.stack([(patch[dy::2, dx::2].astype(np.float32) - 512) * gain for dy, dx in offsets])
assert np.isfinite(planes).all() and (planes > 0).all()
scenes = {
    "flat": np.full_like(planes, 1200),
    "original-texture": planes,
}
files = []
for name, scene in scenes.items():
    # Defocus here is an explicit planted spatial blur, not a measurement of the
    # source's focus or optical PSF. Never smooth across the CFA channel axis.
    groups = [scene] if name == "flat" else [scene, np.stack([gaussian_filter(p, 1.5) for p in scene]), np.stack([gaussian_filter(p, 3) for p in scene])]
    for group, signal in enumerate(groups):
        target = OUT / f"{name}-{group}.f32"
        signal.astype("<f4").tofile(target)
        files.append({"scene":name,"group":group,"file":target.name,"sha256":hashlib.file_digest(target.open("rb"),"sha256").hexdigest()})
calibration = json.loads((RENDER / "calibration.json").read_text())[0]
report = {"schema":"strehl.incremental-noise-fixture.v1","width":128,"height":128,"source":source,
    "source_index":30,"cache":str(path),"cache_sha256":hashlib.file_digest(path.open("rb"),"sha256").hexdigest(),
    "sensor_crop":[x,y,side,side],"gain_short_to_common":gain,"noise_planes":calibration["noise_planes"],"files":files,
    "scope":"Conditional simulated independent temporal noise on fixed original-CFA signal. Does not estimate existing image noise, camera-model correctness, true scene radiance, alignment, or real photograph quality.",
    "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT / "fixture.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"output":str(OUT),"plane_signal_range":[float(planes.min()),float(planes.max())],"fixtures":len(files)}))
