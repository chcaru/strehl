import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dustaxis as da
r = da.run_subject("109MSDCF", commission=True)
print("sites used %d, controls %d" % (r["n_sites_used"], r["n_control"]))
print("UNMODIFIED master ratio %.4f  (defect med %.1f vs control med %.1f)"
      % (r["ratio"], r["defect_med"], r["control_med"]))
print("\nPOWER -- planted single-pixel defects at the mapped sites:")
for p in r["power"]:
    print("   +%7.0f DN -> ratio %.4f%s" % (p["amp_dn"], p["ratio"],
          "   <- detected" if p["ratio"] > da.DUST_MAX else ""))
print("\nIMPROVEMENT -- 3x3 median over the planted image: ratio %.4f "
      "(planted 4000 DN read %.4f)" % (r["improved"], r["power"][0]["ratio"]))
