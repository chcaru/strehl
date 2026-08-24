"""One-shot source patch: independent permutation streams + win/loss reporting.

Kept in the experiment tree so the edit that produced the committed instrument is
itself reproducible (AGENTS.md rule 12).
"""

import pathlib

P = pathlib.Path("crates/strehl-cli/examples/m96-election-margin.rs")
s = P.read_text(encoding="utf-8")

OLD1 = """        let mut rng = Rng::new(args.seeds[0] ^ 0xA5A5_A5A5);
        let n = vol.reg.len();
        for i in (1..n).rev() {"""
NEW1 = """        // A DIFFERENT stream from the paired placebo below, so that running both
        // flags together gives two INDEPENDENT permutations. Sharing the seed
        // made the second arm sigma^2 of the first, which is not a null: the
        // square of a uniform random permutation is biased toward fixed points.
        let mut rng = Rng::new(args.seeds[0] ^ 0x1234_5678_9ABC_DEF0);
        let n = vol.reg.len();
        for i in (1..n).rev() {"""

OLD2 = """        let ties = mr.iter().zip(&mp).filter(|(a, b)| a == b).count();"""
NEW2 = """        let ties = mr.iter().zip(&mp).filter(|(a, b)| a == b).count();
        let losses = both.len() - wins - ties;"""

OLD3 = '''  d={d:<3} n={:9}  real-wins {:7.3}%  ties {:7.3}%  | arbitrary'''
NEW3 = '''  d={d:<3} n={:9}  real-wins {:7.3}%  ties {:7.3}%  w/(w+l) {:7.3}%  | arbitrary'''

OLD4 = """            100.0 * ties as f64 / both.len() as f64,
            100.0 * arb_r as f64 / both.len() as f64,"""
NEW4 = """            100.0 * ties as f64 / both.len() as f64,
            100.0 * wins as f64 / (wins + losses).max(1) as f64,
            100.0 * arb_r as f64 / both.len() as f64,"""

for old, new in ((OLD1, NEW1), (OLD2, NEW2), (OLD3, NEW3), (OLD4, NEW4)):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor matched {n} times, refusing: {old[:60]!r}")
    s = s.replace(old, new)

P.write_text(s, encoding="utf-8", newline="")
print("patched 4 anchors")
