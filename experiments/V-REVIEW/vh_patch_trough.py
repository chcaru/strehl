import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\halo3.py"
t = io.open(P, encoding="utf-8").read()
A = """                        r["width"] <= MAX_RIM_WIDTH) else "CLEAN")
"""
if t.count(A) != 1: sys.exit("ANCHOR 1 NOT FOUND (%d)" % t.count(A))
B = """                        r["width"] <= MAX_RIM_WIDTH and
                        r["trough_px"] <= R - 30) else "CLEAN")
"""
t = t.replace(A, B, 1)
C = """    return dict(overshoot=amp, at_px=float(kp), width=width, floor=floor,
"""
if t.count(C) != 1: sys.exit("ANCHOR 2 NOT FOUND (%d)" % t.count(C))
D = """    # A DECLINE STILL RUNNING WHEN THE WINDOW ENDS IS NOT A LOCAL RIM.
    # Measured: a synthetic backdrop gradient is still falling at 200 px, so
    # its drawdown only LOOKS narrow because the window truncates it. A rim
    # falls back to the background well inside the window.
    return dict(overshoot=amp, at_px=float(kp), width=width, floor=floor,
                trough_px=float(kt),
"""
t = t.replace(C, D, 1)
io.open(P, "w", newline="\n", encoding="utf-8").write(t)
print("patched: trough must be inside the window")
