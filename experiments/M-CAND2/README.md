# M-CAND2

Full-covariance, unregularized Hotelling observer using the frozen CAND1 development
inputs, geometry-only sites, hierarchical bootstrap, and source-freeze discipline.

From `projects\strehl` with all numerical thread variables set to `8`:

```powershell
python -B experiments\M-CAND2\src\run.py preflight
python -B experiments\M-CAND2\src\check.py preflight experiments\M-CAND2\out\preflight.json
python -B experiments\M-CAND2\src\run.py arm unclipped-usm --freeze <sha>
python -B experiments\M-CAND2\src\run.py arm clipped-usm --freeze <sha>
python -B experiments\M-CAND2\src\run.py arm gamma3 --freeze <sha>
python -B experiments\M-CAND2\src\run.py arm logistic --freeze <sha>
python -B experiments\M-CAND2\src\run.py arm saturation --freeze <sha>
python -B experiments\M-CAND2\src\run.py arm quantization --freeze <sha>
python -B experiments\M-CAND2\src\run.py commission --freeze <sha>
```

Every command after preflight verifies all frozen source bytes. Each command
hard-refuses if an earlier ordered arm failed.

The display-referred amendment preserves those historical outputs and uses
versioned commands:

```powershell
python -B experiments\M-CAND2\src\run_v2.py preflight
python -B experiments\M-CAND2\src\check_v2.py preflight experiments\M-CAND2\out\amendment-display-preflight.json
python -B experiments\M-CAND2\src\run_v2.py verify-freeze --freeze <sha>
python -B experiments\M-CAND2\src\run_v2.py arm unclipped-usm --freeze <sha>
python -B experiments\M-CAND2\src\run_v2.py arm clipped-usm --freeze <sha>
python -B experiments\M-CAND2\src\run_v2.py arm gamma3 --freeze <sha>
python -B experiments\M-CAND2\src\run_v2.py arm logistic --freeze <sha>
python -B experiments\M-CAND2\src\run_v2.py gate --freeze <sha>
```

Both tone arms are mandatory even if clipping is invalid or one tone is RED.
The downstream gate alone permits saturation, quantization, optical response,
and null.
