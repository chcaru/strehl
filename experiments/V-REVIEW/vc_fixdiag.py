import io,sys
F="vc_diag.py"; t=io.open(F,encoding="utf-8").read()
t=t.replace("for i, (py, px, nx, ny, r, m) in enumerate(S):",
            "for i, (py, px, nx, ny, r, m, al) in enumerate(S):",1)
t=t.replace("        out[i] = s / r * 1e6","        out[i] = (s/al) / r * 1e6",1)
io.open(F,"w",newline="\n",encoding="utf-8").write(t); print("diag updated")
