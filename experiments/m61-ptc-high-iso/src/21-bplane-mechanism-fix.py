"""M61 step 21 -- B-plane mechanism, corrected. Supersedes step 20.

Step 20 (committed 911dcb3, run and FAILED) had two defects. Rule 15 says
leave them in and supersede, so step 20 stays in the tree and this script
records what it got wrong before doing anything else.

DEFECT 1 -- a crash. `np.bincount(v - lo)` with `lo` set to the 5th
percentile, without first restricting v to [lo, hi]. The bottom 5% of values
are below lo, so `v - lo` is negative and bincount raises. D1 never ran.
Caught by the interpreter, not by me.

DEFECT 2 -- and this one is worse, because it did NOT raise; it printed a
table that looked like an answer. I read the "black pedestal" off
`raw_image_visible.min()`, the minimum of an ILLUMINATED frame. That is a
scene statistic, not a black level. The output duly showed the green planes
with HIGHER floors than R and B in every stack, which is exactly what you
would get from a scene with more green light in its darkest corner, and
nothing to do with a pedestal. `raw_image_visible` is by construction the
CROPPED frame -- the masked optical-black border, the only part of the sensor
that actually measures the pedestal, is precisely what it excludes. D3 as
run in step 20 is VOID, and if the numbers had happened to land near 430 I
would have had a spurious positive.

THE REAL RESULT STEP 20 DID PRODUCE, which survives and is why D2 is now
live rather than unavailable: I pre-registered that nothing in this corpus
clips, on M61's earlier finding that the CPL costs 1.5-2 stops. That
pre-registration was WRONG. `foam` (ISO 1000) reaches 16383 and
`coffee-bean` (ISO 50) reaches it on both greens. So D2 is measurable after
all -- my pre-registered excuse for not measuring it was falsified by the
data, which is the good direction for that to fail in.

--------------------------------------------------------------------------
PRE-REGISTERED HERE, BEFORE RUNNING
--------------------------------------------------------------------------
Hypotheses unchanged from step 20:
  H-A sensor conversion gain, or ANALOG attenuation ahead of the ADC
  H-B in-camera DIGITAL per-channel scale, written into the ARW
  H-C decoder-applied scale absent from the file (largely excluded already
      by M61's rawler/LibRaw bit-identity, max |diff| = 0)

D1 CODE OCCUPANCY -- as step 20, with the clipping bug fixed. A post-
   quantisation scale s < 1 maps codes many-to-one and leaves periodic
   unreachable codes; a pre-ADC scale does not.
     gaps in B and not in G -> H-B ; no B-specific gaps -> H-A
   Sparse-sampling guard retained unchanged: measured only where median
   occupancy >= 100 px, B compared to G at MATCHED OCCUPANCY not matched DN.

D2 SATURATION CEILING -- now live. A post-ADC scale s caps the plane at
   s * full scale, so B could never reach what the greens reach.
     B ceiling < G ceiling by ~0.84 -> H-B ; equal ceilings -> H-A
   GUARD, and it is the one that matters: a plane failing to reach the
   ceiling proves nothing on its own, because a scene may simply contain
   little blue light. Only a stack where the GREENS clip can test B at all,
   and even then B not clipping is ambiguous. So D2 is read ONLY as: does
   ANY frame anywhere in the corpus put a B pixel at the same ceiling the
   greens reach? One such pixel refutes a 0.84 post-ADC cap. Zero such
   pixels across many frames is suggestive but not conclusive.

D3' BLACK PEDESTAL, done properly, by two independent routes:
     (a) the file's declared `black_level_per_channel` metadata;
     (b) the MASKED OPTICAL-BLACK border -- the rows/columns of the full
         `raw_image` that lie outside the visible crop, which see no light
         by construction. CFA phase is taken relative to the crop origin so
         plane labels match the visible area.
   A pedestal-inclusive scale would put B near 0.84*512 ~ 430 on route (b).
   Agreement of the two routes is itself a check on my plane indexing.

   NOTE ON A NEAR-MISS, recorded because it would have failed SILENTLY: my
   first version of route (b) scanned only the TOP and LEFT bands. The smoke
   test showed this camera reports top_margin = left_margin = 0 and hides
   its masked border at the BOTTOM and RIGHT (raw_image 5120x7168 vs visible
   4688x7028). A top/left-only scan returns an EMPTY array and would have
   printed "UNAVAILABLE" without raising -- the exact silent-zero failure the
   brief warned about, and I walked into it. Caught before this commit by
   smoke-testing for execution rather than trusting the code. Route (b) now
   scans all four bands.

   GUARD on route (b), pre-registered: a masked border is only usable if it
   actually looks like a pedestal. If the measured values are not near the
   declared black level, the band is padding rather than optical black and
   route (b) is reported UNUSABLE rather than read.

D4 THE WHITE-BALANCE VECTOR -- new, and its reading fixed in advance. I read
   `raw_image_visible`, which is PRE-white-balance, so any WB multiplier in
   the metadata was NOT applied to my data.
     - if B/G in `camera_whitebalance` or `daylight_whitebalance` is near
       0.84 or its reciprocal 1.19, that is a COINCIDENCE WORTH RECORDING
       and nothing more -- it cannot be the cause, because those multipliers
       were not applied to the surface I measured. I pre-commit to calling
       it a coincidence rather than a finding.
     - if they are nowhere near, that removes the coincidence and the
       question is unaffected either way.
   D4 cannot support a verdict. It is recorded to stop a later reader from
   finding the resemblance and mistaking it for a mechanism.

D5 OVERRANGE -- values above the 15360 white level. If planes reach 16383
   while white level is 15360, some multiplicative step exists somewhere
   above unity. Pre-registered reading: this bears on whether in-camera
   digital scaling happens AT ALL, which is a precondition for H-B; it does
   not by itself say the B plane is scaled.

I was asked not to say which outcome I expect. The mappings above are
written in both directions and no prediction is recorded.

THE LIMIT, restated because it does not go away: if the answer is H-A,
nothing here separates a true sensor conversion gain from an analog
attenuation ahead of the ADC. Both are upstream of quantisation. The report
sketches the dark-noise decomposition that could, and that decomposition is
NOT run here.
"""
import glob
import os
import sys

import numpy as np

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "bplane-mechanism.txt")
WHITE, CONTAINER = 15360, 16383
OCC_FLOOR = 100
PL = ("R", "G1", "G2", "B")
LINES = []


def say(s=""):
    print(s)
    LINES.append(s)


def split(a, r0=0, c0=0):
    return {"R": a[r0::2, c0::2], "G1": a[r0::2, c0 + 1::2],
            "G2": a[r0 + 1::2, c0::2], "B": a[r0 + 1::2, c0 + 1::2]}


def load(path):
    import rawpy
    with rawpy.imread(path) as r:
        vis = r.raw_image_visible.astype(np.int32)
        full = r.raw_image.astype(np.int32)
        s = r.sizes
        meta = {"black": list(r.black_level_per_channel),
                "white": int(r.white_level),
                "cam_wb": list(r.camera_whitebalance),
                "day_wb": list(r.daylight_whitebalance),
                "top": int(s.top_margin), "left": int(s.left_margin),
                "h": int(s.height), "w": int(s.width)}
    return vis, full, meta


def optical_black(full, m):
    """Planes of the masked border, CFA phase relative to the crop origin.

    Scans all four bands outside the visible crop. On this camera
    top_margin = left_margin = 0 and the masked region is the BOTTOM and
    RIGHT bands -- a top/left-only scan returns empty and reports nothing,
    which is the silent-zero failure mode the brief warned about.
    """
    top, left, h, w = m["top"], m["left"], m["h"], m["w"]
    H, W = full.shape
    bands = []
    if top >= 2:
        bands.append((full[0:top, :], (top - top) % 2, (0 - left) % 2))
    if left >= 2:
        bands.append((full[top:top + h, 0:left], 0, (0 - left) % 2))
    if H - (top + h) >= 2:
        bands.append((full[top + h:H, :], (top + h - top) % 2, (0 - left) % 2))
    if W - (left + w) >= 2:
        bands.append((full[top:top + h, left + w:W], 0, (left + w - left) % 2))
    out = {p: [] for p in PL}
    for band, r0, c0 in bands:
        if band.shape[0] < 2 or band.shape[1] < 2:
            continue
        for p, v in split(band, r0, c0).items():
            out[p].append(v.ravel())
    return {p: (np.concatenate(v) if v else np.array([], dtype=np.int32))
            for p, v in out.items()}


def gaps(v):
    v = v[(v > 600) & (v < CONTAINER)]
    if v.size < 20000:
        return None
    lo, hi = int(np.percentile(v, 20)), int(np.percentile(v, 80))
    if hi - lo < 60:
        return None
    v = v[(v >= lo) & (v <= hi)]
    counts = np.bincount(v - lo, minlength=hi - lo + 1)[:hi - lo + 1]
    med = float(np.median(counts))
    if med < OCC_FLOOR:
        return (lo, hi, None, med)
    return (lo, hi, float((counts == 0).mean()), med)


def main() -> int:
    say("=" * 78)
    say("M61 step 21 -- B plane 0.84x: sensor, in-camera digital, or decoder?")
    say("SUPERSEDES step 20, which crashed in D1 and ran a VOID D3.")
    say("=" * 78)
    say()

    picks = [("109MSDCF", 160), ("112MSDCF", 500), ("bee-2", 400),
             ("bee-3", 100), ("foam", 1000), ("coffee-bean", 50),
             ("coffee-bubbles", 1000), ("113MSDCF", 500)]
    frames = []
    for st, iso in picks:
        fs = sorted(glob.glob(os.path.join(CORPUS, st, "*.ARW")))
        if fs:
            frames.append((st, iso, fs[len(fs) // 2]))

    store, meta0 = {}, None
    for st, iso, f in frames:
        vis, full, m = load(f)
        store[st] = (iso, split(vis), optical_black(full, m), m)
        meta0 = meta0 or m

    say("-" * 78)
    say("D3' -- BLACK PEDESTAL, two independent routes")
    say("-" * 78)
    say("  Step 20 read this off min(illuminated frame). That was VOID: it is")
    say("  a scene statistic. The masked optical-black border is the part of")
    say("  the sensor that sees no light, and raw_image_visible excludes it.")
    say()
    say("  route (a) declared black_level_per_channel: "
        f"{meta0['black']}   white_level={meta0['white']}")
    say()
    say("  route (b) MEASURED mean of the masked optical-black border:")
    say(f"  {'stack':<16}{'ISO':>5}" + "".join(f"{p:>10}" for p in PL) +
        f"{'n px':>10}{'B/G':>8}")
    ob_ratios = []
    ob_all = []
    for st, (iso, _, ob, m) in store.items():
        if ob["R"].size == 0:
            say(f"  {st:<16}{iso:>5}   no masked border exposed by decoder")
            continue
        mu = {p: float(ob[p].mean()) for p in PL}
        g = (mu["G1"] + mu["G2"]) / 2
        rat = mu["B"] / g if g else float("nan")
        ob_ratios.append(rat)
        ob_all.extend(mu.values())
        say(f"  {st:<16}{iso:>5}" + "".join(f"{mu[p]:>10.2f}" for p in PL) +
            f"{ob['R'].size:>10}{rat:>8.4f}")
    ob_abs = float(np.mean(ob_all)) if ob_all else 0.0
    say()
    if ob_ratios:
        r = float(np.mean(ob_ratios))
        declared = float(np.mean(meta0["black"])) if meta0["black"] else 0.0
        near = abs(ob_abs - declared) < max(20.0, 0.1 * max(declared, 1.0))
        say(f"  route (b) grand mean across planes = {ob_abs:.2f} vs declared "
            f"{declared:.2f}")
        if not near:
            say("  ROUTE (b) UNUSABLE, per the pre-registered guard: the band")
            say("  does not look like a pedestal, so it is padding rather than")
            say("  optical black. Not read. Route (a) stands alone.")
        else:
            say(f"  D3' reading: masked-black B/G = {r:.4f}")
            say("    A scale applied to the raw INCLUDING its pedestal would")
            say("    put this near 0.84. Near 1.00 means the pedestal is common")
            say("    to all planes, so any per-channel scale acts on the")
            say("    pedestal-SUBTRACTED signal, or there is none.")
            say(f"    -> {'consistent with a pedestal-inclusive scale' if abs(r-0.84) < 0.03 else 'NOT a pedestal-inclusive scale'}")
    else:
        say("  D3' route (b) UNAVAILABLE -- no masked border found.")
    say()

    say("-" * 78)
    say("D2 -- SATURATION CEILING  (step 20 pre-registered this as UNAVAILABLE")
    say("      on the grounds that the CPL prevents clipping. FALSIFIED.)")
    say("-" * 78)
    say(f"  {'stack':<16}{'ISO':>5}" + "".join(f"{p+' max':>10}" for p in PL) +
        f"{'B at ceil':>11}")
    b_hits = 0
    for st, (iso, pl, _, m) in store.items():
        mx = {p: int(pl[p].max()) for p in PL}
        gmax = max(mx["G1"], mx["G2"])
        hit = mx["B"] >= gmax and gmax >= WHITE
        b_hits += hit
        say(f"  {st:<16}{iso:>5}" + "".join(f"{mx[p]:>10}" for p in PL) +
            f"{('YES' if hit else '-'):>11}")
    say()
    say("  D2 reading, per the pre-registered rule (one B pixel at the ceiling")
    say("  the greens reach refutes a 0.84 post-ADC cap):")
    if b_hits:
        say(f"    B reaches the greens' ceiling in {b_hits} stack(s).")
        say(f"    A post-ADC scale of 0.84 would cap B at ~{int(0.84*CONTAINER)}")
        say(f"    and it could NEVER emit {CONTAINER}. This REFUTES H-B in the")
        say("    simple post-ADC-scale form.")
    else:
        say("    B reaches the greens' ceiling nowhere. Suggestive of a cap,")
        say("    but NOT conclusive -- a scene may simply hold little blue.")
    say()

    say("-" * 78)
    say("D5 -- OVERRANGE: values above the white level")
    say("-" * 78)
    say(f"  white_level={WHITE}, container={CONTAINER}. Counting px > {WHITE}:")
    say(f"  {'stack':<16}" + "".join(f"{p:>12}" for p in PL))
    over_any = False
    for st, (iso, pl, _, m) in store.items():
        cnt = {p: int((pl[p] > WHITE).sum()) for p in PL}
        over_any = over_any or any(cnt.values())
        say(f"  {st:<16}" + "".join(f"{cnt[p]:>12}" for p in PL))
    say()
    say(f"  D5 reading: overrange present -> {'YES' if over_any else 'NO'}.")
    say("    Values above the declared white level mean SOME multiplicative")
    say("    step above unity exists in the chain. That is a precondition for")
    say("    in-camera digital scaling existing at all; it does not by itself")
    say("    say the B plane is scaled.")
    say()

    say("-" * 78)
    say("D4 -- WHITE-BALANCE VECTOR (recorded, cannot support a verdict)")
    say("-" * 78)
    cw, dw = meta0["cam_wb"], meta0["day_wb"]
    say(f"  camera_whitebalance   {cw}")
    say(f"  daylight_whitebalance {dw}")
    for nm, v in (("camera", cw), ("daylight", dw)):
        if v[1]:
            say(f"  {nm}: B/G = {v[2]/v[1]:.4f}   G/B = {v[1]/v[2]:.4f}"
                f"   (compare 0.840 and 1.190)")
    say("  Pre-committed reading: I measured raw_image_visible, which is")
    say("  PRE-white-balance, so these multipliers were NOT applied to my")
    say("  data. Any resemblance to 0.84 is a coincidence, recorded so a")
    say("  later reader does not mistake it for a mechanism.")
    say()

    say("-" * 78)
    say("D1 -- CODE OCCUPANCY: gaps in the B histogram?  (bug fixed)")
    say("-" * 78)
    say(f"  {'stack':<16}{'plane':>6}{'window':>16}{'med occ':>10}{'gap %':>9}")
    verdicts = []
    for st, (iso, pl, _, m) in store.items():
        row = {}
        for p in PL:
            r = gaps(pl[p].ravel())
            if r is None:
                say(f"  {st:<16}{p:>6}{'too sparse':>16}")
                continue
            lo, hi, gp, med = r
            gs = "UNAVAIL" if gp is None else f"{100*gp:.2f}"
            say(f"  {st:<16}{p:>6}{f'{lo}-{hi}':>16}{med:>10.0f}{gs:>9}")
            row[p] = gp
        if row.get("B") is not None and row.get("G1") is not None:
            gvals = [row[p] for p in ("G1", "G2") if row.get(p) is not None]
            verdicts.append((st, row["B"], sum(gvals) / len(gvals)))
        say()

    say("-" * 78)
    say("D1 VERDICT")
    say("-" * 78)
    if not verdicts:
        say("  UNAVAILABLE -- occupancy floor unmet. Reported as unavailable,")
        say("  not as a null.")
    else:
        say(f"  {'stack':<16}{'B gap %':>10}{'G gap %':>10}   reading")
        nb = 0
        for st, gb, gg in verdicts:
            comb = gb > 0.02 and gb > 5 * max(gg, 1e-6)
            nb += comb
            say(f"  {st:<16}{100*gb:>10.2f}{100*gg:>10.2f}   "
                f"{'GAPS in B only' if comb else 'no B-specific gaps'}")
        say()
        say(f"  B-specific comb in {nb}/{len(verdicts)} stacks.")
    say()
    say("=" * 78)
    say("All planes read from rawpy raw_image_visible -- pre-white-balance,")
    say("pre-demosaic, per CFA plane, never binned across a quad.")
    say("=" * 78)

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"\n[wrote {OUT}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
