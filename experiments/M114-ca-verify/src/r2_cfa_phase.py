"""M114 R2 -- is (dx=0,dy=0) really a RED sensel, at the origin strehl uses?

Independent of rawler and of M107's comment. Two witnesses:

  A. LibRaw (via rawpy), a different decoder: raw_pattern / raw_colors at the
     full-buffer origin, plus the margins LibRaw reports.
  B. Physics: the as-shot white balance says raw R must sit LOWEST relative to
     green on a roughly neutral scene (wb R=2.569, G=1, B=1.568). So the phase
     with the smallest mean/greenmean is RED and the one with the middle value
     is BLUE.  Both greens must agree with each other to a few percent.

BARS:
  C1  LibRaw's colour index at full-buffer (0,0) must be RED (index 0).
      RED IF: it is 1/2/3.
  C2  LibRaw's margins must be EVEN (or the phase at the origin strehl uses,
      (0,0), differs from the phase LibRaw's visible image starts at).
  C3  phase (0,0) must have the LOWEST mean of the four; phase (1,1) the
      second lowest; (1,0) and (0,1) must agree within 5%.
      RED IF: the ordering is anything else.
  C4  the ratio mean(G)/mean(R-phase) must be consistent with wb_R/wb_G = 2.569
      to within a factor of 2 -- a weak but non-vacuous bound.
"""
import numpy as np
import rawpy

PATH = r"D:\personal\macro\bee-3-cpl\DSC00001.ARW"
NAMES = {0: "R", 1: "G", 2: "B", 3: "G2"}

with rawpy.imread(PATH) as raw:
    s = raw.sizes
    pattern = raw.raw_pattern.copy()
    colors_vis = raw.raw_colors_visible[:8, :8].copy()
    colors_full = raw.raw_colors[:8, :8].copy()
    img = raw.raw_image.astype(np.float64).copy()
    img_vis = raw.raw_image_visible.astype(np.float64).copy()
    desc = raw.color_desc
    cam_wb = list(raw.camera_whitebalance)

print("file        :", PATH)
print("color_desc  :", desc)
print("sizes       :", s)
print("raw_pattern :\n", pattern)
print("raw_colors[0:4,0:4] (FULL buffer):\n", colors_full[:4, :4])
print("raw_colors_visible[0:4,0:4]:\n", colors_vis[:4, :4])
print("camera_whitebalance:", cam_wb)
print("raw_image.shape =", img.shape, " raw_image_visible.shape =", img_vis.shape)

print()
c00 = int(colors_full[0, 0])
c10 = int(colors_full[0, 1])
c01 = int(colors_full[1, 0])
c11 = int(colors_full[1, 1])
print("full-buffer phase map: (dx=0,dy=0)=%s  (1,0)=%s  (0,1)=%s  (1,1)=%s"
      % (desc[c00:c00+1].decode(), desc[c10:c10+1].decode(),
         desc[c01:c01+1].decode(), desc[c11:c11+1].decode()))
c1 = (c00 == 0)
print("C1 LibRaw says full-buffer (0,0) is RED           :", "PASS" if c1 else "FAIL")
c2 = (s.top_margin % 2 == 0) and (s.left_margin % 2 == 0)
print("C2 margins even (top=%d left=%d)                  : %s"
      % (s.top_margin, s.left_margin, "PASS" if c2 else "FAIL"))

# strehl's active area is 7032x4688 at (0,0) of the 7168x5120 buffer.
AW, AH = 7032, 4688
a = img[:AH, :AW]
black = 512.0
means = {}
for dy in (0, 1):
    for dx in (0, 1):
        p = a[dy::2, dx::2]
        means[(dx, dy)] = float(p.mean() - black)
for k in sorted(means):
    print("   phase (dx=%d,dy=%d) mean-black = %10.2f DN" % (k[0], k[1], means[k]))

g = 0.5 * (means[(1, 0)] + means[(0, 1)])
order = sorted(means, key=lambda k: means[k])
c3 = (order[0] == (0, 0) and order[1] == (1, 1)
      and abs(means[(1, 0)] - means[(0, 1)]) / g < 0.05)
print("C3 (0,0) lowest, (1,1) next, greens agree <5%%     :", "PASS" if c3 else "FAIL",
      " order =", order)
ratio = g / means[(0, 0)]
print("C4 mean(G)/mean(phase00) = %.3f  vs wb_R/wb_G = 2.569" % ratio,
      "PASS" if 1.28 < ratio < 5.14 else "FAIL")
print("   mean(G)/mean(phase11) = %.3f  vs wb_B/wb_G = 1.568"
      % (g / means[(1, 1)]))
