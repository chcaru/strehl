"""Plot the mean silhouette profile of each arm on a common SCENE-distance axis."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
pa = np.load("edge_prof_prior.npy"); pb = np.load("edge_prof_strehl.npy"); g = np.load("edge_grid.npy")
ma, mb = np.median(pa, 0), np.median(pb, 0)
fig, ax = plt.subplots(2, 1, figsize=(11, 8), sharex=True, height_ratios=[3, 2])
ax[0].plot(g, ma, label=f"PRIOR (focus-stack fork)  n={len(pa)}", lw=1.6)
ax[0].plot(g, mb, label="STREHL SHIP-V2", lw=1.6)
ax[0].axhline(0, color="k", lw=.5); ax[0].axhline(1, color="k", lw=.5)
ax[0].axvline(0, color="k", lw=.5, ls=":")
ax[0].set_ylabel("normalised (own asymptotes)"); ax[0].legend()
ax[0].set_title("median occluding-edge profile at the bean silhouette, LINEAR light\n"
                "negative = inside the bean, positive = paper background; x in PRIOR pixels")
ax[1].plot(g, mb - ma, color="crimson", lw=1.4)
ax[1].axhline(0, color="k", lw=.5); ax[1].axvline(0, color="k", lw=.5, ls=":")
ax[1].set_ylabel("strehl - prior"); ax[1].set_xlabel("distance from silhouette (prior px)")
for a in ax: a.grid(alpha=.3)
plt.tight_layout(); plt.savefig(r"C:\dev\strehl-out\V-HEADTOHEAD\edge_profiles.png", dpi=110)
print("edge zone stats (median profile):")
for lo, hi in ((-110,-60),(-55,-25),(-25,-8),(-8,0),(0,8),(8,25),(25,55),(60,110)):
    m = (g>=lo)&(g<=hi)
    print(f"  {lo:+5}..{hi:+5}  prior {ma[m].mean():+.4f}  strehl {mb[m].mean():+.4f}  d {mb[m].mean()-ma[m].mean():+.4f}")
