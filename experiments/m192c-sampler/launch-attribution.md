# M192c launch attribution, frozen before execution

The first 64-arm commission failed the predeclared exact-two-process spawn bar:
all three prospective modes observed four Job processes. The intended allocated
child was observed; helper names were unfortunately omitted from the prospective
record. The inherited no-spawn baseline records one python.exe, while prospective
no-spawn records two PIDs. Do not infer helper identity from their memory size.

Test four synthetic parent/child launch combinations, using inherited console
sharing versus CREATE_NO_WINDOW at each generation. Parent begins suspended in
its own no-kill-on-close Job; both Python programs exit naturally after a 0.15 s
child sleep. Record actual process-table names/parent PIDs, creation identity,
Job final count. Hypothesis: the launch flag adds a console helper per generation.
Falsifier: extra process names/parentage do not match that explanation, or counts
do not change with flags. Nothing from these unscored cases repairs the original
commission. The resulting launch choice must be frozen before repeating all arms.

Command: `python -B experiments/m192c-sampler/launch-attribution.py`.
