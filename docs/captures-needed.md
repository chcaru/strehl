# Captures needed from the owner

Measurements that are blocked on data no existing file can supply. Each entry
says exactly what to shoot, why, and what it unblocks.

---

## 1. Dark frames — OUTSTANDING

**Status:** owner will provide later. Proceed without; label anything that
depends on it `ARGUED`, never `MEASURED`.

### What to shoot

| | |
| --- | --- |
| Lens or body cap | **On.** No light may reach the sensor. |
| Room | Dark. Cover the viewfinder if shooting with the EVF exposed. |
| Mode | Manual. |
| Shutter | ~1/100 s (match a typical stacking exposure). |
| Aperture | Irrelevant — the cap is on. |
| Format | **RAW (.ARW).** Not JPEG, not compressed-lossy. |
| Noise reduction | **All off.** Long-exposure NR and high-ISO NR both. |
| Count | **20 frames at ISO 100, then 20 frames at ISO 400.** |
| Between frames | Change nothing. Do not move the camera or touch settings. |

Both ISOs matter: the A7C II appears to have a **second base ISO at 400**, where
read noise drops sharply (4.20 e- to 1.47 e-). If that is real, the noise model
needs two calibration points, not one.

### Why it cannot come from existing files

The plan was to get this free from the sensor's optically-masked border pixels,
which see no light by construction and are therefore a dark frame embedded in
every RAW. **`rawler` does not expose them:** it reports `blackareas` as empty
for Sony, and crops the masked border away during decode. What remains outside
the active area is synthetic zero padding, not sensor data. Verified in
`research/M1-decode-measured.md` §3 — probed 3,544,448 pixels, all exactly 0.

### What it unblocks

**The central design pillar.** `strehl` claims that averaging N frames below the
noise floor buys ~sqrt(N). That is only true for *temporal* noise, which differs
every frame. **Fixed-pattern noise** — a per-pixel offset identical in every
frame — does not average away at all. It is a floor.

A dark frame separates them, because it contains nothing else:

- temporal sigma per pixel, across the 20 frames -> the part that averages away
- spread of per-pixel *means* -> the fixed-pattern part that does not

Plot sigma against N on log-log axes. Slope -0.5 means the noise is independent
and the pillar holds. **Any asymptote is the fixed-pattern floor**, and its value
is the hard limit on what averaging can ever achieve. Re-run after subtracting a
master bias to find how much of it is calibratable.

Second use, nearly free: with frames at two ISOs and a few flat exposures, fit a
real **photon-transfer curve** and measure the gain `g` directly. Right now `g`
is inferred from reproducing the camera's white level to 0.23%, which is a
consistency check on one relation, not a measurement.

---

## 2. Rail-captured stack — DEFERRED, no hardware

**Status:** owner has no focus rail. Rail support is deferred from v1
(`research/SYNTHESIS.md` §9). Not blocking anything currently planned.

If a rail is ever borrowed: one stack of a subject with **visible depth
discontinuities** — overlapping structure where a near surface occludes a far
one, not a smooth continuous surface. That is the case affine cannot model, and
it is where the parallax and occlusion claims need testing.

---

## 3. Not needed

Recorded so nobody asks twice.

- **Flat fields for vignetting.** Not on the v1 path.
- **A focus-bracketed stack.** Already have 22 frames in
  `C:\dev\macro\test\109MSDCF` plus 2310 further ARWs, all verified decodable.
