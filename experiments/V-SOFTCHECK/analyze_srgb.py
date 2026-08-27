"""sRGB gauge readout. Same instrument, sigmas and tiles scaled x2 so the
optical band and the physical sites match the linear gauge."""
import os, sys, numpy as np, softcheck as S
S.S_MID=(1.4,2.8); S.S_HI=(0.7,1.4); S.S_LOW=(6.0,12.0)
S.G_MID=S._white_gain(*S.S_MID); S.G_HI=S._white_gain(*S.S_HI); S.C_NOISE=S.G_MID/S.G_HI
from analyze import load, arms, line, noise_null
subj = sys.argv[1]; c = load(subj, "srgb", 256); N = int(c["N"]); nt = len(c["m_lo"])
print(f"=== {subj} / srgb (BYTE-IDENTICAL to shipped SHIP-V4) / N={N} / {nt} tiles / c_noise={float(c['c_noise']):.5f}")
print(f"GAUGE  master/mean-frame tile LEVEL = {np.median(c['m_lv']/c['f_lv'].mean(0)):.5f}"
      f"   master/mean-frame TOP-BAND = {np.median(c['m_hi_none']/c['f_hi_none'].mean(0)):.4f}")
print(f"REG    rms px median {np.median(c['reg_rms']):.2f} max {c['reg_rms'].max():.2f} (sRGB px; /2 for linear-equivalent)")
base = arms(c); print(line("BASELINE (real, no plant)", base))
for pn in ("blur080","blur140"): print(line(f"  MASTER {pn} [must FALL]", arms(c, m_plant=pn)))
print(line("  MASTER sharp030 [must RISE]", arms(c, m_plant="sharp030")))
print(line("  REF    blur080  [must RISE]", arms(c, f_key="blur080")))
print(line("  PLACEBO gain1.70 both [NO MOVE]", arms(c, m_plant="gain170", f_key="gain170")))
print(line("  PLACEBO frame shuffle [NO MOVE]", arms(c, idx=np.random.default_rng(3).permutation(N))))
r0,_ = noise_null(subj,"srgb",256,c,"identical"); print(line("  null A: N identical masters", r0))
r1,sg = noise_null(subj,"srgb",256,c,"noised"); print(line(f"  null B: N+1 iid noised sig={sg:.0f}DN", r1))
for o in [(0,0),(16,0),(48,48)]:
    print(line(f"  ref offset {o}", arms(c, f_key=f"off_{o[0]}_{o[1]}", ci=False)))
for n in (3,5,9,17,N):
    idx = np.unique(np.round(np.linspace(0,N-1,n)).astype(int)); assert idx[0]==0 and idx[-1]==N-1
    print(line(f"  n={len(idx):3d} idx {idx[0]}..{idx[-1]}", arms(c, idx=idx, ci=False)))
print(f"  detail half NOSUB {base['NOSUB']['median']:.4f} SUB {base['SUB']['median']:.4f}")
print(f"  FLAT   half NOSUB {base['NOSUB_flat']['median']:.4f} SUB {base['SUB_flat']['median']:.4f}")
for q in (0.75,0.90):
    r = arms(c, sel_q=q, ci=False)
    print(f"  tile-selection quantile {q:.2f}: NOSUB {r['NOSUB']['median']:.4f} SUB {r['SUB']['median']:.4f} n={r['NOSUB']['n']}")
