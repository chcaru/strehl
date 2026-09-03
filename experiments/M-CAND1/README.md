# M-CAND1

Finite target-conditional information observer for the first Candidate 1 kill arm.
The observer is trained and evaluated only on development captures listed in
`input-manifest.json`; it never enumerates the capture root.

From `projects\strehl`:

```powershell
$env:OMP_NUM_THREADS='8'
$env:OPENBLAS_NUM_THREADS='8'
$env:MKL_NUM_THREADS='8'
$env:NUMEXPR_NUM_THREADS='8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M-CAND1\src\run.py preflight
python -B experiments\M-CAND1\src\check.py preflight experiments\M-CAND1\out\preflight.json
python -B experiments\M-CAND1\src\run.py usm --freeze <freeze-commit>
python -B experiments\M-CAND1\src\check.py usm experiments\M-CAND1\out\usm.json
python -B experiments\M-CAND1\src\run.py commission --freeze <freeze-commit>
python -B experiments\M-CAND1\src\check.py commission experiments\M-CAND1\out\commission.json
```

The `commission` command hard-refuses to run unless the frozen USM result passed.
Every scientific command verifies the owned source bytes against the freeze commit.
