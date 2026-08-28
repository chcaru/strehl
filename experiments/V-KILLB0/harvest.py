import os, sys
import numpy as np, tifffile
_E = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_E, "V-LINEAR2")); sys.path.insert(0, os.path.join(_E, "V-HEADTOHEAD2"))
import bandsignal as BS
import h2
from h2h2b import band_power

T, MARGIN = BS.T, BS.MARGIN
ALLB = BS.FINE
LO = np.array([b[0] for b in ALLB]); HI = np.array([b[1] for b in ALLB])
SLO = np.array([BS.SEL_LO]); SHI = np.array([BS.SEL_HI])
NY, NX = 10, 13
TARGET_READS = 80

def main():
    d, key, n_real, decim = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".tif"))
    n_dev = len(files)
    far_real = max(20, round(n_real / 6))
    step_dev = max(1, round(n_dev / TARGET_READS))
    step = step_dev * decim
    idx = list(range(0, n_dev, step_dev))
    far = max(2, round(far_real / step))
    m0 = tifffile.memmap(os.path.join(d, files[0]), mode="r"); H, W = m0.shape[0], m0.shape[1]; del m0
    ys = np.linspace(MARGIN, H - MARGIN - T, NY).astype(int)
    xs = np.linspace(MARGIN, W - MARGIN - T, NX).astype(int)
    pos = [(int(y), int(x)) for y in ys for x in xs]
    print(f"{key}: n_dev={n_dev} decim={decim} step={step} far={far} tiles={len(pos)} reads={len(idx)}")
    power = np.zeros((len(idx), len(pos), len(ALLB))); selp = np.zeros((len(idx), len(pos)))
    for a, f in enumerate(idx):
        mm = tifffile.memmap(os.path.join(d, files[f]), mode="r")
        for i, (y, x) in enumerate(pos):
            crop = h2.luma709(np.asarray(mm[y:y+T, x:x+T, :3], np.float64))
            bp = band_power(crop, LO, HI); sp = band_power(crop, SLO, SHI)
            power[a, i] = np.nan if bp is None else bp
            selp[a, i] = np.nan if sp is None else sp[0]
        del mm
        sys.stderr.write(f"\r  {a+1}/{len(idx)}   ")
    sys.stderr.write("\n")
    o = r"C:\dev\strehl-out\V-KILLB0"
    np.save(os.path.join(o, f"{key}-power.npy"), power)
    np.save(os.path.join(o, f"{key}-selp.npy"), selp)
    np.save(os.path.join(o, f"{key}-meta.npy"), np.array([far, len(pos)]))
    print("saved")

if __name__ == "__main__":
    main()
