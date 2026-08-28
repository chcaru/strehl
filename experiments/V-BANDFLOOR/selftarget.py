import numpy as np, slopetest as st, nscale as ns
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
# duty read from the run banners (band-0 "averaged", default arm)
DUTY = {"112MSDCF": 39.7, "113MSDCF": 33.2, "119MSDCF": 48.3, "paper": 0.0}  # all EVEN-half banners
print("%-10s %10s %10s %8s %8s %8s" % ("subject","flat lvl","detail lvl","sf0","duty%","clip%"))
print("-"*60)
rows=[]
for s in ["112MSDCF","113MSDCF","119MSDCF","paper"]:
    ge,cm,cf = ns.load64(OUT+r"\%s__EVEN__A-unset.tiff"%s)
    go,_,_   = ns.load64(OUT+r"\%s__ODD__A-unset.tiff"%s)
    fl,ed,nx = st.sites(ge)
    be,bo = st.octaves(ge), st.octaves(go)
    sf0 = st.sigfrac(fl,be[0],bo[0],nx)
    flvl = float(np.mean([t.mean() for t in st.tiles(fl,ge,nx)]))
    dlvl = float(np.mean([t.mean() for t in st.tiles(ed,ge,nx)]))
    rows.append((s,flvl,dlvl,sf0,DUTY[s]))
    print("%-10s %10.1f %10.1f %8.3f %8.1f %8.4f" % (s,flvl,dlvl,sf0,DUTY[s],100*cf))
a=np.array([[r[1],r[3],r[4]] for r in rows],dtype=float)
print()
print("Spearman duty vs flat-site LEVEL       : %+.3f" % np.corrcoef(np.argsort(np.argsort(a[:,0])),np.argsort(np.argsort(a[:,2])))[0,1])
print("Spearman duty vs measured SIGNAL FRAC  : %+.3f" % np.corrcoef(np.argsort(np.argsort(a[:,1])),np.argsort(np.argsort(a[:,2])))[0,1])

