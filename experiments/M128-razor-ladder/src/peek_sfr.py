"""Print the fitted parameters from an sfr_run half-width sweep JSON."""
import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path))
    print(f"== {path}  ({len(d)} entries)")
    for e in d:
        print(f"   half {e['half_um']:6.1f} core {e['core_um']:5.1f} "
              f"fc {e['fc_cymm']:8.2f} sigma {e['sigma_um']:7.3f} "
              f"amp {e['amp']:.4f} rms {e['rms_resid']:.5f} "
              f"npts {e['n_pts']:3d} ok {e['success']}")
