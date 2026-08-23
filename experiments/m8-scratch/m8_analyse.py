"""M8 analysis — decoder scratch, retention, and the per-worker model.

Reads the CSVs written by `run-m8.ps1` and does the fits. Nothing here touches
the corpora; it only reads `data/*.csv`.

Units: everything is bytes internally. Printed figures are MiB (1024**2) unless
the column says MB, and every printed number says which. `M2-rss-resolved.md`
quoted a modelled 321 *decimal* MB against a measured 364/379 *MiB* in the same
sentence; the ratio it derived from them is fine, but the absolute gap is not
what those two numbers appear to say. See the report.

    python m8_analyse.py            # everything that has data
    python m8_analyse.py single     # one section
"""

import csv
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MIB = 1024.0 * 1024.0

# stack.rs, MEASURED M1 geometry.
ACTIVE_W, ACTIVE_H = 7032, 4688
BUFFER_W, BUFFER_H = 7168, 5120
FRAME_BYTES = BUFFER_W * BUFFER_H * 2
PX = (ACTIVE_W // 2) * (ACTIVE_H // 2)
PER_WORKER_MODEL = PX * (14 + 12 + 4) + FRAME_BYTES
MEMORY_BUDGET_BYTES = 6 << 30


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    rows = []
    header = None
    with open(path, newline="") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                if header is None:
                    header = next(csv.reader([line[1:]]))
                continue
            vals = next(csv.reader([line]))
            if header is None:
                continue
            row = {}
            for k, v in zip(header, vals):
                try:
                    row[k] = int(v)
                except ValueError:
                    try:
                        row[k] = float(v)
                    except ValueError:
                        row[k] = v
            rows.append(row)
    return rows


def ols(X, y):
    """Least squares with standard errors. Returns (beta, se, r2, resid)."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    dof = max(n - p, 1)
    s2 = float(resid @ resid) / dof
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * s2, 0.0))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    return beta, se, r2, resid


def mib(x):
    return x / MIB


def summarise(label, v):
    v = np.asarray(v, dtype=float)
    print(
        f"  {label:<34} n={len(v):<4} mean {mib(v.mean()):8.2f} MiB  "
        f"sd {mib(v.std(ddof=1)) if len(v) > 1 else 0:6.3f}  "
        f"min {mib(v.min()):8.2f}  max {mib(v.max()):8.2f}"
    )


# ---------------------------------------------------------------------------


def section_single():
    rows = load("single.csv")
    if not rows:
        return
    print("=" * 78)
    print("1. SINGLE DECODE IN ISOLATION  (data/single.csv)")
    print("=" * 78)
    print(f"  frame buffer (exact, from the decoder): {FRAME_BYTES} B = {mib(FRAME_BYTES):.2f} MiB")

    warm = [r for r in rows if r["idx"] == 0]
    body = [r for r in rows if r["idx"] > 0]

    def scratch_commit(r):
        return r["peak_commit"] - r["base_commit"] - r["alloc_bytes"]

    def scratch_ws(r):
        return r["peak_ws"] - r["base_ws"] - r["alloc_bytes"]

    def hold_delta(r):
        return r["hold_commit"] - r["base_commit"]

    def retention(r):
        return r["after_commit"] - r["base_commit"]

    print("\n  -- first decode in each process (process warm-up, reported separately) --")
    summarise("scratch_commit  idx=0", [scratch_commit(r) for r in warm])
    print("\n  -- every later decode (steady state) --")
    summarise("scratch_commit", [scratch_commit(r) for r in body])
    summarise("scratch_ws", [scratch_ws(r) for r in body])
    summarise("hold_commit - base (frame only)", [hold_delta(r) for r in body])
    summarise("after_commit - base (retention)", [retention(r) for r in body])
    summarise("file_bytes", [r["file_bytes"] for r in body])

    hd = np.array([hold_delta(r) for r in body], dtype=float)
    print(
        f"\n  hold-minus-base / frame_bytes: mean {hd.mean() / FRAME_BYTES:.5f}x "
        f"(the frame buffer is accounted for exactly; anything else is scratch)"
    )

    # Is scratch constant, file-size proportional, or pixel proportional?
    fb = np.array([r["file_bytes"] for r in body], dtype=float)
    sc = np.array([scratch_commit(r) for r in body], dtype=float)
    px = np.array([r["active_px"] for r in body], dtype=float)
    print(f"\n  active_px is constant at {int(px[0])} across every file available "
          f"({len(set(px.tolist()))} distinct value(s)),")
    print("  so pixel-proportional and constant CANNOT be separated by this corpus. Stated, not fitted.")

    print("\n  Model comparison, per RAYON_NUM_THREADS group. x is file_bytes in MiB,")
    print("  y is scratch_commit in MiB, so the slope is dimensionless.")
    print(f"  {'threads':>7} {'model':<26} {'a (MiB)':>18} {'b':>18} {'resid sd':>9} {'R^2':>8}")
    for t in sorted({r["threads"] for r in body}, key=lambda v: int(v)):
        sub = [r for r in body if r["threads"] == t]
        x = np.array([r["file_bytes"] for r in sub], dtype=float) / MIB
        y = np.array([scratch_commit(r) for r in sub], dtype=float) / MIB
        for name, X, labels in (
            ("constant           a", np.ones((len(x), 1)), ["a"]),
            ("proportional     b*x", x.reshape(-1, 1), ["b"]),
            ("affine       a + b*x", np.column_stack([np.ones_like(x), x]), ["a", "b"]),
        ):
            beta, se, r2, resid = ols(X, y)
            vals = dict(zip(labels, zip(beta, se)))
            a = f"{vals['a'][0]:9.3f}+/-{vals['a'][1]:.3f}" if "a" in vals else "".rjust(18)
            b = f"{vals['b'][0]:9.4f}+/-{vals['b'][1]:.4f}" if "b" in vals else "".rjust(18)
            print(f"  {t:>7} {name:<26} {a:>18} {b:>18} "
                  f"{resid.std(ddof=len(beta)):9.4f} {r2:8.4f}")

    print("\n  Same three models pooled over all thread counts, with a thread term:")
    tt = np.array([float(r["threads"]) for r in body])
    x = fb / MIB
    y = sc / MIB
    for name, X in (
        ("a + b*x", np.column_stack([np.ones_like(x), x])),
        ("a + b*x + c*log2(threads)", np.column_stack([np.ones_like(x), x, np.log2(tt)])),
    ):
        beta, se, r2, resid = ols(X, y)
        terms = "  ".join(f"{n}={v:.4f}+/-{s:.4f}" for n, v, s in zip("abc", beta, se))
        print(f"    {name:<28} R^2={r2:.4f} resid sd={resid.std(ddof=len(beta)):.4f} MiB   {terms}")

    print("\n  Leave-one-corpus-out: fit the affine model without one set, predict it.")
    sets = sorted({str(r.get("set", "?")) for r in body})
    for t in sorted({r["threads"] for r in body}, key=lambda v: int(v)):
        for held in sets:
            tr = [r for r in body if r["threads"] == t and str(r.get("set")) != held]
            te = [r for r in body if r["threads"] == t and str(r.get("set")) == held]
            if not te or len(tr) < 10:
                continue
            xt = np.array([r["file_bytes"] for r in tr], dtype=float) / MIB
            yt = np.array([scratch_commit(r) for r in tr], dtype=float) / MIB
            beta, _, _, _ = ols(np.column_stack([np.ones_like(xt), xt]), yt)
            xe = np.array([r["file_bytes"] for r in te], dtype=float) / MIB
            ye = np.array([scratch_commit(r) for r in te], dtype=float) / MIB
            pred = beta[0] + beta[1] * xe
            err = (pred - ye) / ye
            print(f"    threads={t:>2} held out {held:<16} n={len(te):<4} "
                  f"mean err {100 * err.mean():+6.2f}%  max |err| {100 * np.abs(err).max():5.2f}%")

    print("\n  Per corpus (real stacks and real dark frames, same body, same pixel count):")
    for t in sorted({r["threads"] for r in body}, key=lambda v: int(v)):
        for name in sets:
            sub = [r for r in body if r["threads"] == t and str(r.get("set")) == name]
            if not sub:
                continue
            f = np.mean([r["file_bytes"] for r in sub])
            s_ = np.mean([scratch_commit(r) for r in sub])
            w_ = np.mean([scratch_ws(r) for r in sub])
            print(f"    threads={t:>2} {name:<16} n={len(sub):<4} file {mib(f):6.2f} MiB  "
                  f"scratch_commit {mib(s_):6.2f} MiB ({mib(s_ - f):+5.2f} over file)  "
                  f"scratch_ws {mib(w_):6.2f} MiB")

    print("\n  scratch_commit - file_bytes, the fixed residue:")
    fixed = sc - fb
    summarise("scratch_commit - file_bytes", fixed)

    print("\n  by RAYON_NUM_THREADS (does the decoder's own parallelism cost memory?):")
    for t in sorted({r["threads"] for r in body}, key=lambda v: int(v)):
        sub = [r for r in body if r["threads"] == t]
        summarise(f"threads={t} scratch_commit", [scratch_commit(r) for r in sub])
        summarise(f"threads={t} scratch_ws", [scratch_ws(r) for r in sub])
        summarise(f"threads={t} decode_secs*1e9", [r["decode_secs"] * 1e9 for r in sub])


def section_seq():
    rows = load("seq.csv")
    if not rows:
        return
    print()
    print("=" * 78)
    print("2. SEQUENTIAL DECODES — separating retention from scratch  (data/seq.csv)")
    print("=" * 78)
    print("  One decode is ever live. True scratch cannot accumulate here, so any")
    print("  growth in the kernel peak or in resting commit is the allocator holding on.")
    groups = {}
    for r in rows:
        groups.setdefault((r["threads"], os.path.basename(str(r["path"]))[:3]), []).append(r)
    # Group by thread count only; the path prefix just keeps stacks apart.
    by_t = {}
    for r in rows:
        by_t.setdefault(r["threads"], []).append(r)
    for t, sub in sorted(by_t.items(), key=lambda kv: int(kv[0])):
        sub = sorted(sub, key=lambda r: r["i"])
        i = np.array([r["i"] for r in sub], dtype=float)
        cur = np.array([r["cur_commit"] for r in sub], dtype=float)
        kpk = np.array([r["kpeak_commit"] for r in sub], dtype=float)
        kpw = np.array([r["kpeak_ws"] for r in sub], dtype=float)
        tail = i >= 2
        X = np.column_stack([np.ones(tail.sum()), i[tail]])
        b_cur, se_cur, _, _ = ols(X, cur[tail])
        b_kpk, se_kpk, _, _ = ols(X, kpk[tail])
        print(f"\n  threads={t}, n={len(sub)} sequential decodes")
        print(f"    resting commit after drop : {mib(cur.min()):.2f} .. {mib(cur.max()):.2f} MiB, "
              f"slope {b_cur[1]:,.0f} +/- {se_cur[1]:,.0f} B/decode")
        print(f"    kernel peak commit        : {mib(kpk.min()):.2f} .. {mib(kpk.max()):.2f} MiB, "
              f"slope {b_kpk[1]:,.0f} +/- {se_kpk[1]:,.0f} B/decode")
        print(f"    kernel peak working set   : {mib(kpw.min()):.2f} .. {mib(kpw.max()):.2f} MiB")
        print(f"    peak commit at i=1 vs i=last: {mib(kpk[1]):.2f} -> {mib(kpk[-1]):.2f} MiB "
              f"(+{mib(kpk[-1] - kpk[1]):.2f} MiB over {len(sub) - 1} decodes)")


def fit_conc(rows, label, ycol, xcol="k"):
    k = np.array([r[xcol] for r in rows], dtype=float)
    y = np.array([r[ycol] for r in rows], dtype=float)
    X = np.column_stack([np.ones_like(k), k])
    beta, se, r2, resid = ols(X, y)
    print(f"\n  {label}")
    print(f"    intercept a = {beta[0]:>13,.0f} +/- {se[0]:>9,.0f} B  ({mib(beta[0]):8.2f} MiB)")
    print(f"    slope     b = {beta[1]:>13,.0f} +/- {se[1]:>9,.0f} B  ({mib(beta[1]):8.2f} MiB per concurrent decode)")
    print(f"    R^2 = {r2:.6f}, residual sd = {mib(resid.std(ddof=2)):.2f} MiB, n = {len(k)}")
    print(f"    b - frame_bytes = {beta[1] - FRAME_BYTES:,.0f} B = {mib(beta[1] - FRAME_BYTES):.2f} MiB")
    return beta, se, r2


def section_conc():
    rows = load("conc.csv")
    if not rows:
        return
    print()
    print("=" * 78)
    print("3. CONCURRENT DECODES — the constrained fit  (data/conc.csv)")
    print("=" * 78)
    print("  peak = a + b*k over a swept k, so the fixed overhead and the per-decode")
    print("  cost are separated by the data instead of by assumption. Two points")
    print("  cannot do this; that is why the earlier attempt produced a negative")
    print("  intercept (M2-rss-resolved.md section 4).")
    for mode in ("drop", "hold"):
        for stack in sorted({r["stack"] for r in rows}):
            for t in sorted({r["threads"] for r in rows}, key=lambda v: int(v)):
                sub = [
                    r for r in rows
                    if r["mode"] == mode and r["stack"] == stack and r["threads"] == t
                ]
                if len(sub) < 4:
                    continue
                mean_file = np.mean([r["mean_file_bytes"] for r in sub])
                print(f"\n  --- mode={mode}  stack={stack}  RAYON_NUM_THREADS={t}  "
                      f"mean file {mib(mean_file):.2f} MiB ---")
                fit_conc(sub, "kernel peak COMMIT", "kpeak_commit")
                fit_conc(sub, "kernel peak WORKING SET", "kpeak_ws")


def section_stack():
    fitrows = load("stack.csv") + load("reps.csv") + load("floor.csv")
    hold = load("holdout.csv")
    shape = load("shape.csv")
    if not fitrows:
        return
    print()
    print("=" * 78)
    print("4. THE REAL STACKER  (stack.csv + reps.csv + floor.csv fitted; holdout.csv held out)")
    print("=" * 78)
    print(f"  modelled per_worker_bytes = {PER_WORKER_MODEL:,} B = {mib(PER_WORKER_MODEL):.2f} MiB "
          f"= {PER_WORKER_MODEL / 1e6:.1f} decimal MB")
    print(f"    Selection  px*14 = {PX * 14:>12,} B = {mib(PX * 14):7.2f} MiB")
    print(f"    FocusField px*12 = {PX * 12:>12,} B = {mib(PX * 12):7.2f} MiB")
    print(f"    luma       px* 4 = {PX * 4:>12,} B = {mib(PX * 4):7.2f} MiB")
    print(f"    frame            = {FRAME_BYTES:>12,} B = {mib(FRAME_BYTES):7.2f} MiB")
    print("  NOTE ON UNITS. M2-rss-resolved quoted '321 MB' (decimal, from describe())")
    print("  next to '364/379 MB' read from PowerShell's /1MB, which is MiB. The ratio it")
    print("  derived is unaffected; the absolute gap those two numbers appear to show is.")

    for r in fitrows + hold + shape:
        r["live"] = min(r["chunks"], int(r["threads"]))
        # A binary reduce over `chunks` leaves at most ceil(log2(chunks))
        # partials alive above the one each live worker is already holding.
        r["extra"] = math.ceil(math.log2(r["chunks"])) if r["chunks"] > 1 else 0

    print("\n  peak_live reported by the binary vs min(chunks, threads):")
    allr = fitrows + hold + shape
    bad = [r for r in allr if int(r["peak_live"]) != r["live"]]
    print(f"    {len(allr) - len(bad)}/{len(allr)} agree; {len(bad)} disagree, ALL of them by")
    print("    exceeding it. Concurrent decodes are NOT bounded by min(chunks, pool).")
    for r in bad[:10]:
        print(f"      {r['stack']} N={r['frames']} t={r['threads']} chunks={r['chunks']} "
              f"peak_live={r['peak_live']}  >  min(chunks,threads)={r['live']}")

    floor = load("floor.csv")
    if floor:
        print("\n  --- THE FLOOR: one thread, tiny N (data/floor.csv) ---")
        print("  live == 1 throughout, so everything above one worker's buffers is")
        print("  runtime, prologue, epilogue, and partials waiting in the reduce tree.")
        g = {}
        for r in floor:
            g.setdefault(r["chunks"], []).append(r["peak_ws"])
        prev = None
        for c in sorted(g):
            v = np.array(g[c], dtype=float)
            step = "" if prev is None else f"  step +{mib(v.mean() - prev):6.1f} MiB"
            print(f"    chunks={c:>2}  n={len(v)}  peak_ws {mib(v.mean()):7.1f} MiB  "
                  f"sd {mib(v.std(ddof=1)):.2f}  ceil(log2 c)={r['extra'] if False else math.ceil(math.log2(c)) if c > 1 else 0}{step}")
            prev = v.mean()
        one = np.mean(g[1])
        print(f"    at chunks=1: {mib(one):.1f} MiB, minus one worker's buffers "
              f"({mib(PER_WORKER_MODEL):.1f} MiB) = {mib(one - PER_WORKER_MODEL):.1f} MiB of process floor.")
        print(f"    the step size is {mib(PX * 14):.2f} MiB, which is px*14 = one Selection, to "
              f"{100 * abs(110.03 - mib(np.mean(g[8]) - np.mean(g[4]))) / 110.03:.1f}% .")

    reps = load("reps.csv")
    if reps:
        print("\n  --- run-to-run spread at repeated conditions (peak_ws) ---")
        groups = {}
        for r in reps + floor:
            groups.setdefault((r["stack"], r["frames"], r["threads"]), []).append(r["peak_ws"])
        rel = []
        for key, v in sorted(groups.items()):
            v = np.array(v, dtype=float)
            if len(v) < 2:
                continue
            rel.append(v.std(ddof=1) / v.mean())
            print(f"    {key[0]:<12} N={key[1]:>3} t={key[2]:>2}  n={len(v)}  "
                  f"mean {mib(v.mean()):8.1f} MiB  sd {mib(v.std(ddof=1)):6.1f} MiB  "
                  f"({100 * v.std(ddof=1) / v.mean():5.2f}%)  "
                  f"range {mib(v.min()):.0f}..{mib(v.max()):.0f}")
        print(f"    pooled relative sd = {100 * np.mean(rel):.2f}%  "
              f"(max {100 * np.max(rel):.2f}%)")

    full = [r for r in fitrows if r["chunk_len"] >= 2 or r["chunks"] == r["frames"] <= 8]
    print(f"\n  {len([r for r in fitrows if r not in full])} of {len(fitrows)} fit runs are "
          "under-filled (chunk_len == 1 with many chunks): a worker that decodes")
    print("  exactly one frame is only briefly at its high-water mark, so the concurrency")
    print("  window never fills. Those are excluded from the headline fit.")

    result = {}
    for ycol in ("peak_ws", "peak_commit"):
        print(f"\n  --- target {ycol} ---")
        for label, rows_ in (("all runs", fitrows), ("well-filled only", full)):
            L = np.array([r["live"] for r in rows_], dtype=float)
            E = np.array([r["extra"] for r in rows_], dtype=float)
            C = np.array([r["chunks"] for r in rows_], dtype=float)
            T = np.array([float(r["threads"]) for r in rows_])
            y = np.array([r[ycol] for r in rows_], dtype=float)
            print(f"    [{label}, n={len(rows_)}]")
            models = {
                "a + b*live": np.column_stack([np.ones_like(L), L]),
                "a + b*live + c*chunks": np.column_stack([np.ones_like(L), L, C]),
                "a + b*live + c*threads": np.column_stack([np.ones_like(L), L, T]),
                "a + b*live + c*ceil(log2 chunks)": np.column_stack([np.ones_like(L), L, E]),
            }
            for name, X in models.items():
                beta, se, r2, resid = ols(X, y)
                terms = "  ".join(
                    f"{n}={mib(v):,.1f}+/-{mib(s):,.1f}"
                    for n, v, s in zip(["a", "b", "c"], beta, se)
                )
                flag = "  <-- NEGATIVE INTERCEPT, unphysical" if beta[0] < 0 else ""
                print(f"      {name:<32} R^2={r2:.5f} sd={mib(resid.std(ddof=len(beta))):7.1f} MiB  {terms} (MiB){flag}")
                result[(ycol, label, name)] = (beta, se, r2, resid)

            # The physically-derived model: the reduce-tree term is pinned at
            # one Selection, which is not fitted but computed from geometry.
            yy = y - PX * 14 * E
            beta, se, r2, resid = ols(np.column_stack([np.ones_like(L), L]), yy)
            pred = beta[0] + beta[1] * L + PX * 14 * E
            ss = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
            print(f"      {'a + b*live + px*14*ceil(log2 chunks)':<32} R^2={ss:.5f} "
                  f"sd={mib((y - pred).std(ddof=2)):7.1f} MiB  "
                  f"a={mib(beta[0]):,.1f}+/-{mib(se[0]):,.1f}  b={mib(beta[1]):,.1f}+/-{mib(se[1]):,.1f} (MiB)"
                  f"{'  <-- NEGATIVE INTERCEPT, unphysical' if beta[0] < 0 else ''}")
            result[(ycol, label, "pinned")] = (beta, se, ss, y - pred)

            # Everything except b measured independently: the floor comes from
            # the chunks=1 runs, the tree term from geometry. One free
            # parameter, no intercept to go negative.
            if floor:
                f0 = float(np.mean([r[ycol] for r in floor if r["chunks"] == 1])) - PER_WORKER_MODEL
                yy = y - f0 - PX * 14 * E
                X = L.reshape(-1, 1)
                b1 = float(np.linalg.lstsq(X, yy / MIB, rcond=None)[0][0]) * MIB
                pr = f0 + b1 * L + PX * 14 * E
                ss1 = 1 - ((y - pr) ** 2).sum() / ((y - y.mean()) ** 2).sum()
                s1 = (y - pr).std(ddof=1) / math.sqrt((L**2).sum())
                print(f"      {'floor pinned too, b free':<32} R^2={ss1:.5f} "
                      f"sd={mib((y - pr).std(ddof=1)):7.1f} MiB  "
                      f"floor={mib(f0):,.1f} (MEASURED)  b={mib(b1):,.1f}+/-{mib(s1):,.1f} (MiB)")
                result[(ycol, label, "floorpinned")] = (np.array([f0, b1]), np.array([0.0, s1]), ss1, y - pr)

        beta, se, r2, resid = result[(ycol, "well-filled only", "pinned")]
        scratch = beta[1] - PER_WORKER_MODEL
        print(f"\n    HEADLINE, {ycol}, well-filled, buffers + pinned reduce tree:")
        print(f"      per-worker b = {beta[1]:,.0f} +/- {se[1]:,.0f} B "
              f"= {mib(beta[1]):.1f} +/- {mib(se[1]):.1f} MiB = {beta[1] / 1e6:.1f} decimal MB")
        print(f"      process floor a = {beta[0]:,.0f} +/- {se[0]:,.0f} B = {mib(beta[0]):.1f} MiB")
        print(f"      b - modelled buffers = {scratch:,.0f} B = {mib(scratch):.1f} +/- "
              f"{mib(se[1]):.1f} MiB   <-- THE SCRATCH TERM, in situ")
        print(f"      b / modelled = {beta[1] / PER_WORKER_MODEL:.4f}x")

        if hold:
            print(f"\n    OUT OF SAMPLE — 119MSDCF (33 frames, f/5.6, ISO 50), never fitted:")
            errs = []
            for r in sorted(hold, key=lambda r: (r["live"], r["rep"])):
                pred = beta[0] + beta[1] * r["live"] + PX * 14 * r["extra"]
                obs = r[ycol]
                err = (pred - obs) / obs
                errs.append(err)
                print(f"      N={r['frames']} t={r['threads']:>2} chunks={r['chunks']} live={r['live']:>2} "
                      f"rep={r['rep']}  predicted {mib(pred):8.1f} MiB, observed {mib(obs):8.1f} MiB, "
                      f"error {100 * err:+6.2f}%")
            e = np.array(errs)
            print(f"      mean |error| = {100 * np.abs(e).mean():.2f}%, "
                  f"max |error| = {100 * np.abs(e).max():.2f}%, bias = {100 * e.mean():+.2f}%")
            b2 = result[(ycol, "well-filled only", "a + b*live")][0]
            e2 = np.array([((b2[0] + b2[1] * r["live"]) - r[ycol]) / r[ycol] for r in hold])
            print(f"      for comparison, plain a + b*live: mean |error| {100 * np.abs(e2).mean():.2f}%, "
                  f"max {100 * np.abs(e2).max():.2f}%")

    if shape:
        print("\n  --- SHAPE TEST (SYNTHESIS 3.2.1 assertion 1), thread count PINNED ---")
        print("  assertion 1 says peak must not grow with N at a pinned pool.")
        by_t = {}
        for r in shape:
            by_t.setdefault(int(r["threads"]), []).append(r)
        for t, sub in sorted(by_t.items()):
            base = [r for r in sub if r["frames"] == 2 * t]
            for mult in (3, 4, 8):
                far = [r for r in sub if r["frames"] == mult * t]
                if not base or not far:
                    continue
                b = np.mean([r["peak_ws"] for r in base])
                f = np.mean([r["peak_ws"] for r in far])
                print(f"    threads={t}: N={2 * t} -> {mib(b):7.1f} MiB, N={mult * t:>2} -> {mib(f):7.1f} MiB, "
                      f"ratio {f / b:.3f}  (chunks {base[0]['chunks']} -> {far[0]['chunks']}, "
                      f"chunk_len {base[0]['chunk_len']} -> {far[0]['chunk_len']})")
        print("\n  and with `chunks` matched as well as `threads` (coffee-bean, t=32, chunks=20):")
        for n in (40, 60):
            v = [r["peak_ws"] for r in fitrows if r["stack"] == "coffee-bean"
                 and r["frames"] == n and int(r["threads"]) == 32]
            if v:
                print(f"    N={n:>3}, chunk_len={2 if n == 40 else 3}: {mib(np.mean(v)):7.1f} MiB  (n={len(v)})")

    print("\n  --- what a no-intercept 'peak / live' says, at the conditions M2 used ---")
    for r in sorted(fitrows, key=lambda r: (r["stack"], r["frames"], r["live"])):
        if r["live"] in (11, 18) and int(r["threads"]) >= 32:
            print(f"    {r['stack']} N={r['frames']} t={r['threads']} live={r['live']} rep={r['rep']}: "
                  f"peak_ws/live = {mib(r['peak_ws'] / r['live']):.1f} MiB "
                  f"({r['peak_ws'] / r['live'] / 1e6:.1f} decimal MB)")
    return result


def plan(frames, per_worker, cpus=32, budget=MEMORY_BUDGET_BYTES):
    by_memory = max(budget // per_worker, 1)
    workers = min(by_memory, cpus, frames)
    chunk_len = -(-frames // workers)
    chunks = -(-frames // chunk_len)
    return workers, chunks, chunk_len


def predict_peak(chunks, floor, per_worker, live=None):
    """M8 model: process floor + live workers' buffers + the reduce tree."""
    live = chunks if live is None else live
    extra = math.ceil(math.log2(chunks)) if chunks > 1 else 0
    return floor + live * per_worker + extra * PX * 14


def honest_cap(floor, per_worker, budget=MEMORY_BUDGET_BYTES):
    """Largest W whose predicted peak still fits the budget."""
    w = 1
    while predict_peak(w + 1, floor, per_worker) <= budget:
        w += 1
        if w > 4096:
            break
    return w


def section_recommendation(floor, per_worker, se_per_worker=0.0):
    print()
    print("=" * 78)
    print("5. WHAT AN HONEST MODEL WOULD DO TO THE PLAN  (RECOMMENDATION, not applied)")
    print("=" * 78)
    print(f"  buffers only (shipped) : {PER_WORKER_MODEL:,} B = {mib(PER_WORKER_MODEL):.1f} MiB")
    print(f"  M8 per worker          : {per_worker:,.0f} +/- {se_per_worker:,.0f} B = "
          f"{mib(per_worker):.1f} +/- {mib(se_per_worker):.1f} MiB "
          f"({per_worker / PER_WORKER_MODEL:.3f}x)")
    print(f"  M8 process floor       : {floor:,.0f} B = {mib(floor):.1f} MiB")
    print(f"  M8 reduce tree         : {PX * 14:,} B x ceil(log2 chunks) = "
          f"{mib(PX * 14):.1f} MiB per level")
    print(f"  budget                 : {MEMORY_BUDGET_BYTES:,} B = "
          f"{mib(MEMORY_BUDGET_BYTES):.0f} MiB = {MEMORY_BUDGET_BYTES / 1e9:.2f} decimal GB")

    cap = honest_cap(floor, per_worker)
    lo = honest_cap(floor, per_worker + se_per_worker)
    hi = honest_cap(floor, per_worker - se_per_worker)
    print(f"\n  worker cap under the M8 model: {cap}  (+/-1 sigma on b: {lo}..{hi})")
    print(f"  worker cap as shipped        : {MEMORY_BUDGET_BYTES // PER_WORKER_MODEL}")

    print(f"\n  {'N':>5} | {'now':^22} | {'M8':^22} | {'predicted peak':^19}")
    print(f"  {'':>5} | {'workers':>7} {'chunks':>7} {'len':>5} | "
          f"{'workers':>7} {'chunks':>7} {'len':>5} | {'now':>9} {'M8':>9}")
    print("  " + "-" * 76)
    for n in (22, 33, 105, 220):
        w0, c0, l0 = plan(n, PER_WORKER_MODEL)
        w1, c1, l1 = plan(n, MEMORY_BUDGET_BYTES // cap)
        p0 = predict_peak(c0, floor, per_worker)
        p1 = predict_peak(c1, floor, per_worker)
        print(f"  {n:>5} | {w0:>7} {c0:>7} {l0:>5} | {w1:>7} {c1:>7} {l1:>5} | "
              f"{mib(p0):>8.0f}M {mib(p1):>8.0f}M")
    print(f"\n  (predicted peak is the M8 model applied to BOTH plans, so the two columns")
    print(f"   are comparable; 'now' is what the shipped plan actually costs, not what")
    print(f"   the shipped model claims it costs.)")
    print(f"\n  per_worker_bytes value to hand the planner for a cap of {cap}: "
          f"{MEMORY_BUDGET_BYTES // cap:,} B")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "single"):
        section_single()
    if which in ("all", "seq"):
        section_seq()
    if which in ("all", "conc"):
        section_conc()
    headline = None
    if which in ("all", "stack", "plan"):
        headline = section_stack()
    if which in ("all", "stack", "plan") and headline:
        beta, se, _, _ = headline[("peak_ws", "well-filled only", "pinned")]
        section_recommendation(beta[0], beta[1], se[1])


if __name__ == "__main__":
    main()
