import struct, pathlib, math, json
def f64(h): return struct.unpack(">d", bytes.fromhex(h))[0]
p = pathlib.Path("experiments/M87-occlusion/cache/align/bee3-warpmap.txt")
W, H = 3516, 2344            # binned plane, per the sidecar header
cx, cy = W/2.0, H/2.0
rows = []
for ln in p.read_text().split("\n"):
    t = ln.split("#")[0].split()
    if len(t) == 6 and t[1] == "placed":
        i = int(t[0]); a = complex(f64(t[2]), f64(t[3])); b = complex(f64(t[4]), f64(t[5]))
        rows.append((i, a, b))
print("frames placed:", len(rows))
corners = [complex(0,0), complex(W,0), complex(0,H), complex(W,H)]
# ROI_LEG (binned output coords) from the original brief: x 300..1400, y 1200..1900
roi_c = complex((300+1400)/2.0, (1200+1900)/2.0)
half_diag = abs(complex(W,H) - complex(cx,cy))
best = None
for i, a, b in rows:
    disp = max(abs(a*z + b - z) for z in corners)
    if best is None or disp > best[1]: best = (i, disp, a, b)
i, disp, a, b = best
s = abs(a)
print(f"max corner drift over all frames: frame {i}, {disp:.2f} px BINNED = {2*disp:.2f} px FULL-SENSOR")
print(f"  scale |a| = {s:.6f}   (1-|a|) = {1-s:.6f}   rot = {math.degrees(math.atan2(a.imag,a.real)):+.4f} deg")
f298 = [r for r in rows if r[0] == 298][0]
s298 = abs(f298[1])
print(f"frame 298: scale |a| = {s298:.6f}, 1-scale = {1-s298:.6f}")
print(f"  corner drift = {max(abs(f298[1]*z+f298[2]-z) for z in corners):.2f} binned / "
      f"{2*max(abs(f298[1]*z+f298[2]-z) for z in corners):.2f} full")
# what scale would 603 px full-sensor corner drift imply, pure scale about centre?
print(f"half-diagonal: {half_diag:.1f} binned, {2*half_diag:.1f} full")
print(f"  603 px full  -> 1-s = {603/(2*half_diag):.5f} -> s = {1-603/(2*half_diag):.5f}")
print(f"  232.7 px full-> 1-s = {232.7/(2*half_diag):.5f} -> s = {1-232.7/(2*half_diag):.5f}")
print(f"  232.7 px binned->1-s = {232.7/half_diag:.5f} -> s = {1-232.7/half_diag:.5f}")
# in-ROI drift peak-to-peak, the quantity my verdict actually rests on
d = [abs(a*roi_c + b - roi_c) for _, a, b in rows]
print(f"ROI_LEG centre drift: p-p = {max(d)-min(d):.2f} px binned  (max {max(d):.2f})")
json.dump({"max_corner_binned":disp,"max_corner_full":2*disp,"frame":i,
           "scale_max":s,"scale_298":s298,"roi_pp_binned":max(d)-min(d)},
          open("experiments/M87-occlusion/data/50-drift-audit.json","w"), indent=1)
