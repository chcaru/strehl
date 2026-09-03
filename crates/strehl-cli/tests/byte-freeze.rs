//! **The byte-freeze registry, machine-checked.**
//!
//! # Why this file exists
//!
//! This project's epistemics rest on byte-freezes: a milestone renders a
//! specific stack with a specific command, records the SHA-256, and later work
//! cites that hash as proof the output has not moved. Until M108 *every one of
//! those freezes was enforced by prose in a report*. The verifier who found
//! that put it in one sentence:
//!
//! > "No test exists that pins any freeze hash. Every freeze in this project is
//! > enforced by prose in a report, not by CI -- an untested freeze is an
//! > unverified freeze."
//!
//! Two things went wrong while nobody was checking, and both are the reason
//! this file is shaped the way it is:
//!
//! 1. **A freeze went stale silently.** M85's hash broke at `885e9f7` (M86c,
//!    "wire alignment into strehl stack") and stayed cited in `merge_cmd.rs`
//!    for weeks as live proof the encoder still emits identical bytes. The
//!    change was correct; the proof it invalidated was still being quoted.
//!    (SYNTHESIS facts 1380, 1381.)
//! 2. **A hash was compared against a different pipeline's hash.** Three
//!    milestones froze three *different* invocations and none recorded the full
//!    command next to the hash. A later dispatch spliced one milestone's
//!    `--gate` onto another's `--limit`, produced a fourth invocation nobody
//!    had ever frozen, and commissioned a 1.9-hour investigation into a
//!    regression that had not happened. The absence of one flag was the entire
//!    cause. (SYNTHESIS facts 1379, 1382; AGENTS.md rule 47.)
//!
//! # What this is, and what it deliberately is not
//!
//! **It is not a wall against change.** Seven agents are landing quality
//! improvements in this tree; a byte-exact assertion that fires constantly gets
//! `#[ignore]`d by the third person who hits it, and then it protects nothing.
//! The value is in making a change **visible and deliberate** rather than
//! silent. Three design consequences follow, and each is load-bearing:
//!
//! * **The invocation is generated from the record.** [`Freeze::command`] builds
//!   the argv and the environment out of the registry row. There is no second
//!   place where the command lives, so a hash can never be compared against a
//!   command other than the one it was measured under. That is the mechanical
//!   fix for defect 2 above; prose in a report could not be.
//! * **The failure message teaches.** Most moves here *will* be intended. When
//!   the hash moves the test prints both hashes, the exact reproducing command,
//!   the recorded reason for the last re-baseline, and the three cases the
//!   reader might be in -- including how to re-baseline. A golden-file test that
//!   only says `assertion failed` will be silenced.
//! * **The registry is data.** `byte-freezes.tsv` sits next to this file and is
//!   validated by tests that need no capture library, no binary and no RAW
//!   decode, so a fresh clone still checks that every freeze records a complete,
//!   unambiguous, non-defaulted invocation.
//!
//! # Hermeticity, and why the frozen rows do not solve alignment
//!
//! The capture library is **read only** and is the owner's irreplaceable data.
//! `strehl align`'s sidecar and `stack`'s discover-or-solve cache have between
//! them put thirteen stray `warpmap.txt` files inside it in one night
//! (facts 1384, 1385); one of them held a 40-frame solve for a 299-frame
//! bracket, which would silently have merged 40 frames while reporting 299.
//!
//! So every row here runs in one of exactly two modes, both of which write
//! nothing anywhere near the captures:
//!
//! * `align = off` -- `STREHL_ALIGN=0`. `align_cmd::align_enabled()` returns
//!   false and `load_or_solve` returns before a sidecar path is even computed,
//!   so this is hermetic **at every commit**, whichever agent's aligner is
//!   currently in the tree.
//! * `align = sidecar:F` -- `STREHL_WARPMAP` pointed at a committed fixture.
//!   Documented at `merge_cmd.rs:1035`: when that variable is set nothing is
//!   written anywhere, the sidecar is hard-validated against the bracket, and a
//!   mismatch is a refusal rather than a silent re-solve.
//!
//! `align = solve` -- letting the merge discover-or-solve -- is **rejected by
//! the validator**, and that is a decision rather than an omission. When these
//! rows were measured, at `fea1a72`, `align_cmd::sidecar_path` still resolved to
//! `<stackdir>/warpmap.txt`, so a solving row would have written into the
//! read-only library on every run. M85's repair landed at `dccaea8` while this
//! milestone was in flight -- the default is now `cache_root()`
//! (`%LOCALAPPDATA%\strehl\warpmaps`, overridable with `$STREHL_CACHE_DIR`) --
//! so the hard objection is gone and a softer one remains: a solving row freezes
//! the aligner's **solver**, and the solver was being rewritten by two
//! milestones on the day this was written. A freeze that moves every week is a
//! freeze that gets deleted. Admit a solving row when the solver settles; it is
//! the only row that would cover the solver at all. Revisit this restriction,
//! do not inherit it.
//!
//! The two modes freeze **different pipelines**, and the difference between them
//! is exactly the M86c watershed. Keeping both is what lets a hash move be
//! localised: if only the sidecar row moves, warp application changed; if both
//! move, the merge core did.
//!
//! # Both backends, always
//!
//! There is a second axis, and for the whole life of this file it was frozen at
//! one end without anyone noticing. `Freeze::argv` hardcoded `--merge
//! estimator` into every row, and by the time that was read back
//! `merge_cmd::DEFAULT_MERGE_BACKEND` had already moved to `Pyramid` -- so a
//! green byte-freeze certified only the backend nobody gets by default, and a
//! regression in the path every default render takes could not trip a single
//! check here (SYNTHESIS fact 1909).
//!
//! `merge` is now a registry column, and
//! [`every_registry_row_records_a_complete_invocation`] requires at least one
//! row on **each** backend, so whichever way that constant is pointed the
//! registry has already frozen it. The column also decides which gate flag the
//! argv carries -- `--gate` on the estimator, `--pyramid-gate` on the pyramid --
//! because `main.rs` refuses each under the other backend rather than carrying
//! the number across two different quantities.
//!
//! # Running it
//!
//! `cargo test -p strehl-cli --test byte-freeze`. The render arm needs the
//! capture library; without it the test **skips with a loud message** rather
//! than failing, because a test that fails on a fresh clone is a test that gets
//! ignored. Set `STREHL_FREEZE_REQUIRE=1` to turn every skip into a hard
//! failure -- that is the setting for a machine that is supposed to have the
//! data, and for CI.
//!
//! Measured cost at `fea1a72` on the reference rig: 3.3 s (unaligned) and 7.6 s
//! (sidecar) per render in `--release`, 26 s unaligned in `dev`. The hash is
//! **identical in both profiles** (measured), so this runs under a plain
//! `cargo test`. The pyramid row costs 3.6 s per render in `--release`
//! (measured at `a5ecda36`), and its hash was measured under **both** profiles
//! rather than inheriting that claim from the estimator rows: the whole file
//! reproduces bit-for-bit under `cargo test` (dev, 350 s for five tests) and
//! under `cargo test --release` (47 s).

use std::collections::BTreeSet;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------------------
// SHA-256
// ---------------------------------------------------------------------------

/// FIPS 180-4 SHA-256, inline so this test adds no dependency to the workspace.
///
/// Rule 35 applies to a hasher as much as to a constant: this implementation is
/// asserted against the **published** NIST vectors in
/// [`the_hasher_reproduces_the_published_test_vectors`], not against itself or
/// against another copy of the same code, and the baselines in the registry were
/// cross-checked against PowerShell's `Get-FileHash` -- an independent
/// implementation -- when they were measured.
mod sha256 {
    const K: [u32; 64] = [
        0x428a_2f98,
        0x7137_4491,
        0xb5c0_fbcf,
        0xe9b5_dba5,
        0x3956_c25b,
        0x59f1_11f1,
        0x923f_82a4,
        0xab1c_5ed5,
        0xd807_aa98,
        0x1283_5b01,
        0x2431_85be,
        0x550c_7dc3,
        0x72be_5d74,
        0x80de_b1fe,
        0x9bdc_06a7,
        0xc19b_f174,
        0xe49b_69c1,
        0xefbe_4786,
        0x0fc1_9dc6,
        0x240c_a1cc,
        0x2de9_2c6f,
        0x4a74_84aa,
        0x5cb0_a9dc,
        0x76f9_88da,
        0x983e_5152,
        0xa831_c66d,
        0xb003_27c8,
        0xbf59_7fc7,
        0xc6e0_0bf3,
        0xd5a7_9147,
        0x06ca_6351,
        0x1429_2967,
        0x27b7_0a85,
        0x2e1b_2138,
        0x4d2c_6dfc,
        0x5338_0d13,
        0x650a_7354,
        0x766a_0abb,
        0x81c2_c92e,
        0x9272_2c85,
        0xa2bf_e8a1,
        0xa81a_664b,
        0xc24b_8b70,
        0xc76c_51a3,
        0xd192_e819,
        0xd699_0624,
        0xf40e_3585,
        0x106a_a070,
        0x19a4_c116,
        0x1e37_6c08,
        0x2748_774c,
        0x34b0_bcb5,
        0x391c_0cb3,
        0x4ed8_aa4a,
        0x5b9c_ca4f,
        0x682e_6ff3,
        0x748f_82ee,
        0x78a5_636f,
        0x84c8_7814,
        0x8cc7_0208,
        0x90be_fffa,
        0xa450_6ceb,
        0xbef9_a3f7,
        0xc671_78f2,
    ];

    /// Streaming state, so a 49 MB render is hashed in 64 KiB bites rather than
    /// held in memory twice.
    pub struct Hasher {
        h: [u32; 8],
        buf: [u8; 64],
        buf_len: usize,
        total: u64,
    }

    impl Default for Hasher {
        fn default() -> Self {
            Self::new()
        }
    }

    impl Hasher {
        pub fn new() -> Self {
            Self {
                h: [
                    0x6a09_e667,
                    0xbb67_ae85,
                    0x3c6e_f372,
                    0xa54f_f53a,
                    0x510e_527f,
                    0x9b05_688c,
                    0x1f83_d9ab,
                    0x5be0_cd19,
                ],
                buf: [0u8; 64],
                buf_len: 0,
                total: 0,
            }
        }

        pub fn update(&mut self, mut data: &[u8]) {
            self.total = self.total.wrapping_add(data.len() as u64);
            if self.buf_len > 0 {
                let want = 64 - self.buf_len;
                let take = want.min(data.len());
                self.buf[self.buf_len..self.buf_len + take].copy_from_slice(&data[..take]);
                self.buf_len += take;
                data = &data[take..];
                if self.buf_len < 64 {
                    // Still a partial block. Returning here matters: falling
                    // through would reach the `self.buf_len = rest.len()` below
                    // with an empty remainder and reset the partial block to
                    // zero length, which makes `finish`'s padding loop
                    // oscillate 0,1,0,1 and never reach 56. It did.
                    return;
                }
                let block = self.buf;
                self.compress(&block);
                self.buf_len = 0;
            }
            let (blocks, rest) = data.as_chunks::<64>();
            for block in blocks {
                self.compress(block);
            }
            self.buf[..rest.len()].copy_from_slice(rest);
            self.buf_len = rest.len();
        }

        pub fn finish(mut self) -> [u8; 32] {
            let bits = self.total.wrapping_mul(8);
            self.update(&[0x80]);
            // `update` counted the padding byte; the length field is over the
            // message, so it was captured in `bits` before this point.
            while self.buf_len != 56 {
                self.update(&[0x00]);
            }
            let mut block = self.buf;
            block[56..].copy_from_slice(&bits.to_be_bytes());
            self.compress(&block);
            let mut out = [0u8; 32];
            for (i, w) in self.h.iter().enumerate() {
                out[i * 4..i * 4 + 4].copy_from_slice(&w.to_be_bytes());
            }
            out
        }

        fn compress(&mut self, block: &[u8; 64]) {
            let mut w = [0u32; 64];
            for (i, word) in w.iter_mut().take(16).enumerate() {
                *word = u32::from_be_bytes([
                    block[i * 4],
                    block[i * 4 + 1],
                    block[i * 4 + 2],
                    block[i * 4 + 3],
                ]);
            }
            for i in 16..64 {
                let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
                let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
                w[i] = w[i - 16]
                    .wrapping_add(s0)
                    .wrapping_add(w[i - 7])
                    .wrapping_add(s1);
            }
            let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh] = self.h;
            for i in 0..64 {
                let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
                let ch = (e & f) ^ (!e & g);
                let t1 = hh
                    .wrapping_add(s1)
                    .wrapping_add(ch)
                    .wrapping_add(K[i])
                    .wrapping_add(w[i]);
                let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
                let maj = (a & b) ^ (a & c) ^ (b & c);
                let t2 = s0.wrapping_add(maj);
                hh = g;
                g = f;
                f = e;
                e = d.wrapping_add(t1);
                d = c;
                c = b;
                b = a;
                a = t1.wrapping_add(t2);
            }
            for (slot, v) in self.h.iter_mut().zip([a, b, c, d, e, f, g, hh]) {
                *slot = slot.wrapping_add(v);
            }
        }
    }

    pub fn hex(bytes: &[u8; 32]) -> String {
        let mut s = String::with_capacity(64);
        for b in bytes {
            s.push_str(&format!("{b:02X}"));
        }
        s
    }

    /// Convenience for the test vectors.
    pub fn of(data: &[u8]) -> String {
        let mut h = Hasher::new();
        h.update(data);
        hex(&h.finish())
    }
}

// ---------------------------------------------------------------------------
// The registry
// ---------------------------------------------------------------------------

const REGISTRY_TEXT: &str = include_str!("byte-freezes.tsv");
const REGISTRY_FILE: &str = "crates/strehl-cli/tests/byte-freezes.tsv";

/// The header, verbatim. Checked rather than skipped: renaming or reordering a
/// column otherwise shifts every field silently, which is the same class of
/// defect as reading a hash without its command.
const HEADER: &[&str] = &[
    "id",
    "stack",
    "frames",
    "limit",
    "merge",
    "gate",
    "srgb",
    "env_align",
    "env_warpmap",
    "env_fix_halo",
    "env_cache_dir",
    "alignment_mode",
    "sha256",
    "bytes",
    "workers",
    "baselined_at",
    "baselined_on",
    "why",
];

/// One frozen invocation. Every field that changes the output is here; nothing
/// about the command lives anywhere else.
#[derive(Debug, Clone)]
struct Freeze {
    id: String,
    stack: String,
    frames: String,
    limit: String,
    merge: String,
    gate: String,
    srgb: bool,
    env_align: String,
    env_warpmap: String,
    env_fix_halo: String,
    env_cache_dir: String,
    alignment_mode: String,
    sha256: String,
    bytes: u64,
    workers: String,
    baselined_at: String,
    baselined_on: String,
    why: String,
    /// 1-based line number in the TSV, so a validation failure names a location
    /// a human can open.
    line: usize,
}

/// The literal recorded when a variable is deliberately not set.
///
/// There is no empty field and no absent column. Rule 47's whole point is that
/// a reader cannot tell a default from an omission, so "not set" is spelled out
/// and is a value like any other.
const UNSET: &str = "unset";

/// The literal recorded for a path the harness itself supplies at run time.
const SCRATCH: &str = "scratch";

/// The two spellings the `merge` column admits, which are the two spellings
/// `--merge` itself accepts (`merge_cmd::MergeBackend::name`).
///
/// Spelled here rather than imported because this test drives the binary as a
/// stranger would -- through argv. If the CLI ever renames a backend, the row
/// must fail loudly at the command line rather than follow the rename silently
/// through a shared constant.
const ESTIMATOR: &str = "estimator";
const PYRAMID: &str = "pyramid";

/// Environment variables that change what `strehl stack` emits.
///
/// Every one of them is **removed** before a row's own settings are applied, so
/// the ambient environment of whoever runs the test cannot quietly render a
/// different pipeline than the row describes. This is the same defect as the
/// missing `--gate`, one layer down: an unrecorded input.
///
/// Rule 47 as amended requires that the environment be recorded beside the hash
/// and not merely controlled. The first four have their own registry column;
/// `STREHL_FIX_HALO_DELTA` is only read when `STREHL_FIX_HALO` is set, so it is
/// covered by that column's value and by this list's clearing.
const RENDER_ENV: &[&str] = &[
    "STREHL_ALIGN",
    "STREHL_WARPMAP",
    "STREHL_CACHE_DIR",
    // The coverage policy changes both the sampling geometry and, under
    // `crop`, the output dimensions. Commissioned with an ambient
    // `STREHL_COVER=crop`: the aligned coffee-bean freeze moved from
    // 49,450,019 to 48,875,075 bytes while its unaligned control held. Without
    // clearing this variable, a dirty shell looks exactly like a geometry
    // regression in the byte-freeze.
    "STREHL_COVER",
    "STREHL_FIX_HALO",
    "STREHL_FIX_HALO_DELTA",
    // The per-frame measured noise floor. `STREHL_GATE_FLOOR=white` restores
    // the compile-time white-noise constant everywhere, which is a DIFFERENT
    // merge -- it moves the gate by up to 1.85x on a warped frame and so moves
    // which coefficients are averaged rather than selected. An operator with
    // this exported would render a different image from the frozen one and the
    // failure would look like a code regression.
    "STREHL_GATE_FLOOR",
    // The sensor defect map. The correction rewrites photosites BEFORE the
    // warp, so a row rendered with it in a different state is a different
    // render of the same frames -- 16,039 of 32,966,016 delivered samples move
    // on `coffee-bean` with the shipped map (BUILD-DEFECT.md sec 5).
    //
    // **STREHL_DEFECT is the one that matters now.** The correction is off by
    // default, and both hashes here are measured with it off -- but "off by
    // default" is a property of the code, not of the ambient environment. An
    // operator with `STREHL_DEFECT=on` exported in their shell would render a
    // corrected stack and compare it against an uncorrected hash. The default
    // has already moved once in each direction in this file's lifetime, which
    // is exactly why the variable is cleared rather than assumed.
    //
    // `_MAP` substitutes a different map for the embedded one AND implies
    // `on`; `_ARM` and `_HOT_FLOOR` change what is applied. All four are
    // listed: the cost of a redundant entry is nothing and the cost of a
    // missing one is a freeze that silently stops being hermetic. That is the
    // STREHL_ALIGN=0 defect and it has now been committed twice.
    "STREHL_DEFECT",
    "STREHL_DEFECT_MAP",
    "STREHL_DEFECT_ARM",
    "STREHL_DEFECT_HOT_FLOOR",
    // The edge-aware selection variables. Every one of these re-routes the
    // election, so a row rendered with one of them set is not the row it says
    // it is. STREHL_ONLY_FRAME is the extreme case: it renders a single frame
    // with no election at all, and would move every hash in this file while
    // appearing nowhere in any record.
    //
    // This is the STREHL_ALIGN=0 defect described in the header of
    // byte-freezes.tsv, committed a second time -- by me, when I added these
    // variables and did not add them here. Recorded rather than quietly fixed
    // because the header's claim is that the lesson was learned, and it was
    // not.
    "STREHL_EDGE_AWARE",
    "STREHL_EDGE_TAU",
    "STREHL_EDGE_CONF",
    // The noise-driven window shrink. It sets the per-pixel election radius on
    // 96.58% of `couch-fibers-cpl` (r13 99.93% with it off, 3.42% with it on),
    // so an ambient `STREHL_ACUITY=0` would render a materially different
    // election than every row here claims. It exists only so both arms of the
    // restoration A/B can come from one binary; it must never leak into a
    // freeze.
    "STREHL_ACUITY",
    // The full-resolution gather. It selects what every output pixel is
    // interpolated *from* -- a full-resolution demosaic of the whole frame, or
    // that pixel's own half-resolution phase plane -- so an ambient
    // `STREHL_FULLRES_GATHER=0` renders a different image than every row here
    // claims. It moved these rows when its default flipped on, which is how it
    // came to be in this list.
    "STREHL_FULLRES_GATHER",
    "STREHL_ONLY_FRAME",
    // Which merge runs, and how its fold is partitioned. `STREHL_MERGE` is the
    // most dangerous entry in this list: it selects the whole backend, so an
    // ambient `STREHL_MERGE=pyramid` would render a completely different
    // pipeline than every row here claims -- 99.9895% of pixels, mean 1820 DN.
    // `STREHL_PYRAMID_WORKERS` is milder but real: it changes the fold's
    // reduction order, which is worth 1 DN on a fifth of a percent of pixels,
    // and a byte-freeze is precisely the instrument that cannot tolerate 1 DN.
    "STREHL_MERGE",
    "STREHL_PYRAMID_WORKERS",
    // The veil envelope. `STREHL_VEIL` rewrites the merged sums at every
    // eligible pixel, so an ambient setting would move these hashes while
    // appearing nowhere in any row. Registered here in the same commit that
    // introduced the variables, because the two comments above record what it
    // costs to do otherwise.
    "STREHL_VEIL",
    "STREHL_VEIL_MARGIN",
    "STREHL_VEIL_FLOOR",
    // The lateral-CA profile. This one arrived by the opposite route to every
    // entry above: the variable is old, but it only became able to move a hash
    // when the correction was defaulted ON. While unset meant off, an ambient
    // value could only ever move the bytes AWAY from the recorded pipeline in
    // the direction nobody used, and the omission never bit. Now unset means
    // the gear-matched profile applies, `off` is a real and different render,
    // and the row's bytes depend on which of the two the ambient shell happens
    // to hold. `scripts\gallery.ps1` sets this variable, so "ran the gallery,
    // then ran the tests, in one shell" is not a hypothetical path to it.
    //
    // Worth stating plainly because it generalises: a default flip can turn a
    // dormant unrecorded input into a live one without anything in this file
    // changing. The list is not made safe by being complete on the day it was
    // written.
    "STREHL_FIX_CA",
    // The photometric gain term, arriving by the same route as `STREHL_FIX_CA`
    // above and one flip later. That comment ended: "a default flip can turn a
    // dormant unrecorded input into a live one without anything in this file
    // changing." This is that sentence coming true. The variable is old; it
    // became able to move a hash the moment the default went from `off` to
    // `on`, because unset now means the gain is fitted and applied, and `off`
    // is a real and different render.
    //
    // Twice predicted, twice arrived. The list is not made safe by being
    // complete on the day it was written -- and it is not made safe by having
    // said so, either.
    "STREHL_PHOTOMETRIC",
    // The soft admission kernel. This entry is the third instance of the
    // pattern the two comments above predict, and the first that can do
    // something worse than move a hash: it can *abort the test*.
    //
    // Both rows in `byte-freezes.tsv` pass `--merge estimator` explicitly, and
    // on that backend the variable has always been live -- `Estimator::new`
    // resolves it from the process environment. So an ambient
    // `STREHL_SOFT_GATE=gaussian` does not produce a frozen render with
    // different bytes; it produces a *differently weighted* fold that no row
    // records, and an ambient typo produces `panic!` at rc=101, which reads as
    // a crashed harness rather than a dirty shell.
    //
    // It was missing from this list for the whole life of the variable. The
    // omission never bit for the same reason `STREHL_FIX_CA`'s did not: nobody
    // sets it, because until now it did nothing on the default backend. That
    // is exactly the condition under which these entries get forgotten, and
    // exactly the condition that ends the moment the switch becomes useful.
    "STREHL_SOFT_GATE",
    // The per-coefficient significance floor. It multiplies the noise floor
    // each band coefficient is judged against, so it rewrites `select_weight`
    // for every coefficient in every band of every frame -- the election
    // itself, not a post-process.
    //
    // Registered in the commit that introduces the variable, which is what the
    // four comments above say should have happened each time and did not. It
    // ships defaulted OFF, so unset and `0` are the same render today and this
    // entry cannot yet move a hash by being cleared.
    //
    // IT IS NOW REACHABLE. This entry used to end "it is also unreachable from
    // these rows for a second reason: every row here hardcodes `--merge
    // estimator` and this variable only exists on the pyramid backend, which is
    // `DEFAULT_MERGE_BACKEND`." That sentence retired the moment
    // `coffee-bean-20-gate2-pyramid` was added. The variable is live on that
    // row, and the row's teeth were proven with exactly this mechanism: with
    // `significance_scale_default`'s unset arm planted at 1.0 in the source --
    // the same render the ambient variable would produce, but reaching past
    // this list, which is the only way a plant CAN reach past it -- the pyramid
    // row moved
    //   C6765BFA0D2FD203F65A7B02FE36920902B26A6706CCEAA8E87B76AC1CE5CD65 ->
    //   A4B699DA7FE32E70ED35002720539460C43EFEC093BA68191A9E7A4C14479547
    // while both estimator rows held. Written in full rather than truncated for
    // the reason the `sha256` column insists on it: this corpus already carries
    // a freeze recorded as `D99F5D82...76CA`, which no machine can check.
    "STREHL_PYRAMID_SIGNIFICANCE",
    // The rest of the pyramid's own environment, registered in the commit that
    // gives it something to hide -- the first pyramid row. Both are read by
    // `MergeConfig::default()` through a `OnceLock`, so an ambient value is
    // resolved once per process and applies to the whole fold:
    //
    //   * `STREHL_HULL` selects what the reconstruction is clamped to. Anything
    //     other than the default `InputRange` rewrites merged samples.
    //   * `STREHL_PYRAMID_MEAN_COARSE` sets how many coarse bands are replaced
    //     by a plain mean. It defaults to 0 -- "until the ladder that chooses
    //     it has been run, so this field cannot move a byte until it is
    //     measured" (`pyramid.rs`) -- and a shell that sets it moves bytes now.
    //
    // Neither could reach a row in this file until today, which is precisely
    // the condition the five comments above describe forgetting under.
    "STREHL_HULL",
    "STREHL_PYRAMID_MEAN_COARSE",
];

impl Freeze {
    fn fixture_dir() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("data")
    }

    /// Is this row a pyramid freeze? Decided by the recorded column and by
    /// nothing else -- never by `DEFAULT_MERGE_BACKEND`, which is the value a
    /// freeze must be able to outlive.
    fn is_pyramid(&self) -> bool {
        self.merge == PYRAMID
    }

    /// The argv this row freezes, built from the row itself.
    fn argv(&self, stack_dir: &Path, out: &Path) -> Vec<String> {
        let mut v = vec![
            "stack".to_string(),
            stack_dir.display().to_string(),
            // The backend is an INPUT, and an input that is merely defaulted
            // rather than recorded is the exact defect this file's header
            // describes: the day `DEFAULT_MERGE_BACKEND` moves, an unnamed row
            // would silently change pipeline and every hash below would move at
            // once.
            //
            // THIS WAS HARDCODED TO `estimator` UNTIL THE FIRST PYRAMID ROW WAS
            // ADDED. The note that stood here said so, and said what to do:
            // "the day a pyramid row is added this must become a registry
            // column, exactly like `--gate` did." That day came, and the reason
            // it had to is sharper than the note anticipated --
            // `DEFAULT_MERGE_BACKEND` had ALREADY moved to `Pyramid`, so
            // hardcoding `estimator` meant this registry certified only the
            // NON-default backend and every default render was unguarded.
            "--merge".to_string(),
            self.merge.clone(),
        ];
        if !self.is_pyramid() {
            // Every row in this registry was frozen while `--photometric`
            // defaulted OFF. The default is now ON, so an unnamed row would
            // render a pipeline it does not describe and every hash below
            // would move at once -- not because the render regressed, but
            // because the row stopped saying what it froze.
            //
            // Named for the same reason `--merge` is named directly above: the
            // mode is an INPUT, and an input that is merely defaulted rather
            // than recorded is the defect this file's header describes.
            //
            // ESTIMATOR ROWS ONLY, and that is a property of the CLI rather
            // than a choice made here: `main.rs`'s wrong-backend table REFUSES
            // `--photometric` under `--merge pyramid` ("NOT YET IMPLEMENTED on
            // this backend, rather than inapplicable"), so passing it on a
            // pyramid row would exit non-zero rather than freeze anything. The
            // pyramid says the same thing on its own stderr -- `not applied :
            // photometric gain, ...` -- which is the observation this omission
            // rests on, not an assumption about the table.
            v.push("--photometric".to_string());
            v.push("off".to_string());
        }
        v.push("--limit".to_string());
        v.push(self.limit.clone());
        // The noise gate, by value, on whichever flag the row's backend
        // accepts. THE TWO ARE DIFFERENT QUANTITIES -- `--gate` is a multiple
        // of the focus-response SD (default 4.0), `--pyramid-gate` a multiple
        // of the modelled band-noise power (default 2.0) -- and `main.rs`
        // refuses each under the other backend rather than carrying the number
        // across. So this is a switch, not a rename: the `gate` column records
        // the number, the `merge` column decides what it means, and a row that
        // named the wrong one would not run at all.
        v.push(if self.is_pyramid() {
            "--pyramid-gate".to_string()
        } else {
            "--gate".to_string()
        });
        v.push(self.gate.clone());
        if self.srgb {
            v.push("--srgb".to_string());
        }
        v.push("--out".to_string());
        v.push(out.display().to_string());
        v
    }

    /// The environment this row freezes, as `(name, value)` pairs applied after
    /// every entry of [`RENDER_ENV`] has been removed.
    ///
    /// Built from the recorded columns, exactly as [`Freeze::argv`] is built
    /// from the recorded flags. This is the point of the whole file: the thing
    /// that is *recorded* and the thing that is *executed* are the same object,
    /// so the record cannot be incomplete. An earlier draft of rule 47 bound
    /// only the CLI flags, and within two hours a freeze was found that
    /// reproduces exactly but only under `STREHL_ALIGN=0` -- a value that
    /// appeared nowhere in its record.
    ///
    /// `scratch` is a run-time path the harness supplies; every other value is
    /// taken from the row verbatim.
    fn env(&self, scratch: &Path) -> Vec<(String, String)> {
        let mut v = Vec::new();
        let mut put = |k: &str, recorded: &str, resolve: &dyn Fn(&str) -> String| {
            if recorded != UNSET {
                v.push((k.to_string(), resolve(recorded)));
            }
        };
        put("STREHL_ALIGN", &self.env_align, &|s| s.to_string());
        put("STREHL_WARPMAP", &self.env_warpmap, &|s| {
            Self::fixture_dir().join(s).display().to_string()
        });
        put("STREHL_FIX_HALO", &self.env_fix_halo, &|s| s.to_string());
        put("STREHL_CACHE_DIR", &self.env_cache_dir, &|s| {
            if s == SCRATCH {
                scratch.join("cache").display().to_string()
            } else {
                s.to_string()
            }
        });
        // STREHL_DEFECT=off, hardcoded, and now for a stronger reason than
        // when it was written.
        //
        // Sensor defect correction is ON by default. It is applied by
        // `stack.rs`'s `load_frame`, which is the PYRAMID backend's loader;
        // the estimator loads frames through `field_for`/`Scratch` and does
        // not apply it. While every row here was an estimator row, the note in
        // this place said "no row here has ever been rendered with the
        // correction, AND NONE CAN BE" -- `merge_cmd::preflight_defect_backend_support`
        // refuses to render an estimator stack with a correction configured
        // rather than silently dropping it.
        //
        // THAT SECOND CLAUSE IS RETIRED. `coffee-bean-20-gate2-pyramid` renders
        // on the backend that DOES apply the correction, so this line stopped
        // being a restatement of an impossibility and became the setting that
        // decides that row's bytes: on `coffee-bean` the correction fires at
        // -14.859% (p 0.0025), so `off` versus `on` is a different image.
        // MEASURED, not inferred from the code path -- the pyramid says which
        // it did on its own stderr, `defect map      : off (STREHL_DEFECT=off)`.
        //
        // Still hardcoded rather than a column because every row genuinely is
        // an uncorrected freeze, and a column with one value in every row
        // records nothing the reader cannot already read here or in the
        // reproduction `command` prints. The day a CORRECTED row is added it
        // must become a column, exactly like `--merge` just did -- and unlike
        // `--merge`, whose hardcode had already gone stale against
        // `DEFAULT_MERGE_BACKEND` by the time anyone looked, this one is still
        // true of every row in the file.
        v.push(("STREHL_DEFECT".to_string(), "off".to_string()));
        v
    }

    /// A copy-pasteable reproduction, for the failure message. This is what a
    /// milestone report should paste beside a hash.
    fn command(&self, stack_dir: &Path, out: &Path) -> String {
        let scratch = Path::new("<scratch>");
        let mut s = String::new();
        let _ = writeln!(s, "  # frames: {}", self.frames);
        for name in RENDER_ENV {
            let _ = writeln!(s, "  Remove-Item Env:{name} -ErrorAction SilentlyContinue");
        }
        for (k, v) in self.env(scratch) {
            let _ = writeln!(s, "  $env:{k} = \"{v}\"");
        }
        let _ = write!(s, "  strehl.exe");
        for a in self.argv(stack_dir, out) {
            let _ = write!(s, " {a}");
        }
        s
    }
}

fn parse_registry() -> Vec<Freeze> {
    let mut rows = Vec::new();
    let mut header_seen = false;
    for (i, raw) in REGISTRY_TEXT.lines().enumerate() {
        let line = i + 1;
        if raw.trim().is_empty() || raw.starts_with('#') {
            continue;
        }
        let f: Vec<&str> = raw.split('\t').collect();
        if !header_seen {
            assert_eq!(
                f, HEADER,
                "\n{REGISTRY_FILE}:{line}: the header row does not match the columns \
                 byte-freeze.rs expects.\nIf you added or renamed a column, update `HEADER` \
                 and the `Freeze` struct in the same commit. This check exists because a \
                 shifted column reads as a valid row.\n"
            );
            header_seen = true;
            continue;
        }
        assert_eq!(
            f.len(),
            HEADER.len(),
            "\n{REGISTRY_FILE}:{line}: {} tab-separated fields, expected {}. \
             Fields must be separated by TABS, and no field may contain one.\n",
            f.len(),
            HEADER.len()
        );
        // The rejection lives on the ENVIRONMENT COMBINATION rather than on a
        // mode label, because the combination is the true cause: alignment on
        // (`STREHL_ALIGN` unset) with no override (`STREHL_WARPMAP` unset) is a
        // solving row however it is spelled.
        let align_on = f[7] == UNSET;
        let no_override = f[8] == UNSET;
        if align_on && no_override {
            panic!(
                "\n{REGISTRY_FILE}:{line}: env_align = `unset` with env_warpmap = `unset` is \
                 a SOLVING row, and solving rows are not admissible.\n\n\
                 A solving row freezes the aligner's SOLVER as well as the merge, and the \
                 solver was under active rewrite by two milestones on the day these rows \
                 were measured. A freeze that moves every week is a freeze that gets \
                 deleted, which leaves you with nothing.\n\n\
                 There is a sharper objection, measured rather than assumed. A solving row \
                 does not solve every time: `align_cmd::load_or_solve` first looks for a \
                 CACHED sidecar and reuses it whenever `check_stack` passes and the frame \
                 count matches (`align_cmd.rs:967-980`). `StackIdentity::from_paths` \
                 digests filenames and file lengths only (`warpmap.rs:238`), never \
                 contents, so a cached sidecar whose placements have been altered passes \
                 both tests. I swapped two placements inside one and the render moved from \
                 119936E6... to 8065EA8D... at exit 0, reporting `20 placed / 0 refused`. \
                 Every guard in this file except the alignment-mode token stayed green. A \
                 solving row would therefore have reported a MOVED FREEZE for a renderer \
                 that had not changed -- a fourth false break, from the same root cause as \
                 the first three.\n\n\
                 Until `dccaea8` there was a harder objection still: `align_cmd::sidecar_path` \
                 resolved to `<stackdir>/warpmap.txt`, so every run of this test would have \
                 written into the READ-ONLY capture library. Thirteen stray sidecars \
                 accumulated there in one night that way (SYNTHESIS facts 1384, 1385), one \
                 of them a 40-frame solve sitting under a 299-frame bracket.\n\n\
                 Set env_align = `0` to freeze the unregistered merge, or env_warpmap = \
                 `<fixture file under tests/data>` to freeze an aligned pipeline against a \
                 COMMITTED warp map.\n\n\
                 When the solver settles, this restriction should be REVISITED, not \
                 inherited -- a solving row is the only one that would cover the solver.\n"
            );
        }
        if !align_on && !no_override {
            panic!(
                "\n{REGISTRY_FILE}:{line}: env_align = `{}` and env_warpmap = `{}` are both \
                 set.\n\n\
                 With alignment switched off the override is never read, so this row \
                 records an input that cannot affect its hash. That is the decorative \
                 record rule 47 exists to stop: the next reader cannot tell which of the \
                 two actually produced the bytes.\n",
                f[7], f[8]
            );
        }
        if !align_on && f[7] != "0" {
            panic!(
                "\n{REGISTRY_FILE}:{line}: env_align = `{}`; use `0` (off) or `unset` (on). \
                 An empty field is not a value -- see the `unset` convention at the top of \
                 the registry.\n",
                f[7]
            );
        }
        // The backend, validated HERE rather than only in the row-completeness
        // test, because `Freeze::is_pyramid` reads it to decide which gate flag
        // the argv carries. An unrecognised spelling must not be able to fall
        // through that comparison as "estimator" -- the row would then build a
        // command nobody wrote and the failure would be reported against the
        // wrong backend.
        if !matches!(f[4], ESTIMATOR | PYRAMID) {
            panic!(
                "\n{REGISTRY_FILE}:{line}: merge = `{}`; use `{ESTIMATOR}` or `{PYRAMID}`.\n\n\
                 RECORD THE BACKEND, NOT THE FACT THAT YOU LEFT IT ALONE. \
                 `DEFAULT_MERGE_BACKEND` is `pyramid` today and was `estimator` \
                 yesterday; a row that does not name its backend freezes whichever \
                 one the constant happens to hold, and moves the day it flips.\n",
                f[4]
            );
        }
        let srgb = match f[6] {
            "yes" => true,
            "no" => false,
            other => panic!("\n{REGISTRY_FILE}:{line}: srgb = `{other}`; use `yes` or `no`.\n"),
        };
        rows.push(Freeze {
            id: f[0].to_string(),
            stack: f[1].to_string(),
            frames: f[2].to_string(),
            limit: f[3].to_string(),
            merge: f[4].to_string(),
            gate: f[5].to_string(),
            srgb,
            env_align: f[7].to_string(),
            env_warpmap: f[8].to_string(),
            env_fix_halo: f[9].to_string(),
            env_cache_dir: f[10].to_string(),
            alignment_mode: f[11].to_string(),
            sha256: f[12].to_string(),
            bytes: f[13].parse().unwrap_or_else(|e| {
                panic!(
                    "\n{REGISTRY_FILE}:{line}: bytes = `{}` is not a number ({e}).\n",
                    f[13]
                )
            }),
            workers: f[14].to_string(),
            baselined_at: f[15].to_string(),
            baselined_on: f[16].to_string(),
            why: f[17].to_string(),
            line,
        });
    }
    assert!(
        header_seen,
        "\n{REGISTRY_FILE}: no header row found. The file must contain one.\n"
    );
    rows
}

// ---------------------------------------------------------------------------
// Locating the capture library
// ---------------------------------------------------------------------------

/// The reference rig's library, used when `$STREHL_CAPTURES` says nothing.
const DEFAULT_CAPTURE_LIBRARY: &str = r"D:\personal\macro";

/// Where the owner's captures live, or a reason this machine has none.
///
/// `$STREHL_CAPTURES` wins so the freeze is runnable on a second machine without
/// editing a hard-coded path into the source -- and so the skip path itself is
/// exercisable from a shell, which is the only way anyone will ever check that
/// it works.
///
/// A `$STREHL_CAPTURES` that points nowhere is treated as *absent* rather than
/// as an error: evidentially it is the same situation, we cannot check the
/// freeze either way. What stops that from hiding a typo is
/// `STREHL_FREEZE_REQUIRE=1`, which turns every skip into a hard failure and
/// prints the path that was tried.
fn capture_library() -> Result<PathBuf, String> {
    if let Some(p) = std::env::var_os("STREHL_CAPTURES") {
        let p = PathBuf::from(p);
        if p.is_dir() {
            return Ok(p);
        }
        return Err(format!(
            "$STREHL_CAPTURES is set to `{}`, and there is no directory there.\n\
             Point it at a capture library, or unset it to fall back to `{DEFAULT_CAPTURE_LIBRARY}`.",
            p.display()
        ));
    }
    let default = PathBuf::from(DEFAULT_CAPTURE_LIBRARY);
    if default.is_dir() {
        return Ok(default);
    }
    Err(format!(
        "No capture library on this machine. The renders below need the owner's RAW\n\
         captures, which are local data on one rig and are not in the repository:\n\
         \n\x20   {DEFAULT_CAPTURE_LIBRARY}   (override with $STREHL_CAPTURES)\n\
         \n\
         This is expected on a fresh clone and is NOT a defect."
    ))
}

/// Write to the process's real stderr, **bypassing libtest's output capture**.
///
/// This exists because of a defect measured in this very file. libtest captures
/// `print!`/`eprint!` for tests that PASS and only replays it for tests that
/// fail, so every `println!` here was invisible in the mode all of this test's
/// callers actually use: a piped `cargo test` in an agent tool call or a CI log.
/// Measured A/B on the committed test at `2c13138`, both piped, no `--nocapture`:
///
/// ```text
///   library absent, nothing rendered : test result: ok. 5 passed ... in 0.00s   exit 0
///   library present, both freezes ok : test result: ok. 5 passed ... in 17.21s  exit 0
/// ```
///
/// Byte-identical but for a duration nobody reads. **A run that verified nothing
/// and a run that verified everything were the same observation**, which is
/// discipline 702 exactly, in the instrument built to enforce it. I had
/// "verified" the skip banner with `--nocapture` -- a mode no caller uses.
///
/// The capture is a thread-local consulted by the `print!` family; a direct
/// write to the underlying handle is not routed through it. That is measured
/// rather than assumed, by the A/B above being re-run after this change.
fn note(msg: &str) {
    use std::io::Write;
    let mut e = std::io::stderr();
    let _ = e.write_all(msg.as_bytes());
    let _ = e.write_all(b"\n");
    let _ = e.flush();
}

/// Skip, unless the operator has said skipping is a failure.
///
/// A skip is the correct answer on a fresh clone and a *defect* on a machine
/// that is supposed to hold the data, so the two are separated by a flag rather
/// than by hope. Note the asymmetry that keeps this honest: an absent library
/// skips, but a library that is present with the row's stack **missing** is a
/// hard failure -- so a machine that has the data cannot skip by accident.
fn skip(reason: &str) {
    let required = std::env::var("STREHL_FREEZE_REQUIRE")
        .map(|v| !matches!(v.trim(), "" | "0" | "off" | "false" | "no"))
        .unwrap_or(false);
    assert!(
        !required,
        "\n\n\
         ==============================================================================\n\
         BYTE-FREEZE NOT CHECKED, and STREHL_FREEZE_REQUIRE says that is a failure.\n\
         ==============================================================================\n\
         {reason}\n\n\
         Nothing was rendered, so this run is evidence about NOTHING. Unset\n\
         STREHL_FREEZE_REQUIRE if you genuinely do not have the captures.\n"
    );
    note(&format!(
        "\n\
         ------------------------------------------------------------------------------\n\
         SKIPPED: the byte-freeze renders were NOT checked. 0 of {n} freezes verified.\n\
         ------------------------------------------------------------------------------\n\
         {reason}\n\n\
         The registry rows themselves WERE still validated by the other tests in this\n\
         file -- their completeness, not their hashes. Set STREHL_FREEZE_REQUIRE=1 to\n\
         make this skip a hard failure on a machine that is supposed to have the data,\n\
         which is what CI should do.\n\n\
         THIS LINE IS WRITTEN TO THE REAL STDERR ON PURPOSE. libtest captures the\n\
         `print!` family for passing tests, so a skip printed the ordinary way is\n\
         invisible in a piped `cargo test` -- making a run that verified nothing\n\
         indistinguishable from one that verified everything (discipline 702).\n\
         ------------------------------------------------------------------------------",
        n = parse_registry().len()
    ));
}

// ---------------------------------------------------------------------------
// Tests that need nothing but the repository
// ---------------------------------------------------------------------------

/// Rule 35: assert the instrument against something it did not produce.
///
/// These are the published FIPS 180-4 / NIST example vectors. They have power to
/// fail: flipping any constant, the padding, or the length encoding breaks at
/// least one of them, and the long vector is the only one that exercises a
/// multi-block message with a non-trivial length field.
#[test]
fn the_hasher_reproduces_the_published_test_vectors() {
    assert_eq!(
        sha256::of(b""),
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
    );
    assert_eq!(
        sha256::of(b"abc"),
        "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD"
    );
    assert_eq!(
        sha256::of(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
        "248D6A61D20638B8E5C026930C3E6039A33CE45964FF2167F6ECEDD419DB06C1"
    );
    let million = vec![b'a'; 1_000_000];
    assert_eq!(
        sha256::of(&million),
        "CDC76E5C9914FB9281A1C7E284D73E67F1809A48A497200E046D39CCC7112CD0"
    );
}

/// The mode parser, against lines `strehl stack` really emitted.
///
/// Worth its own test because the mode token is the FIRST gate: if it misreads,
/// every later check is comparing hashes from a pipeline nobody chose. The four
/// strings below are copied verbatim out of render logs measured at `fea1a72`,
/// not composed for the test -- a parser test written against invented input
/// tests the author's memory of the format rather than the format.
#[test]
fn the_alignment_parser_names_every_mode_the_tool_can_report() {
    let off = "alignment      : OFF -- frames are combined unregistered. M86 measured \
               232.7 px of drift on bee-3-cpl; expect softness that grows with radius.";
    let solved = "alignment      : ON (solved), reference frame 10, 20 placed / 0 refused";
    let over = "alignment      : ON (sidecar-override), reference frame 10, 20 placed / 0 refused";
    let cache = "alignment      : ON (sidecar), reference frame 10, 20 placed / 0 refused";

    assert_eq!(alignment_mode(off), "off");
    assert_eq!(alignment_mode(solved), "on-solved");
    assert_eq!(alignment_mode(over), "on-sidecar-override");

    // The prefix trap. `ON (sidecar)` is a prefix of `ON (sidecar-override)`, so
    // testing them in the wrong order silently reports every OVERRIDDEN run as a
    // CACHE HIT. That would turn the one signal that distinguishes isolated
    // registration from ambient registration into a permanent false alarm --
    // and a permanent false alarm is how this check gets deleted.
    assert_eq!(alignment_mode(cache), "on-sidecar-cache");
    assert_ne!(alignment_mode(over), "on-sidecar-cache");

    // A reworded or absent line must read as MISSING and never as a mode. The
    // isolation gate treats MISSING as a failure precisely so that a silent
    // rewording shows up as "this check has gone blind" rather than as a pass.
    assert!(alignment_mode("workers        : 10 chunks of <= 2 frames").starts_with("MISSING"));
    assert!(alignment_mode("alignment      : ON (magic)").starts_with("MISSING"));

    // The counts on the same line, which the placement gate reads.
    assert_eq!(placement(over), Some((20, 0)));
    assert_eq!(placement(off), None);
}

/// Rule 47, mechanically. Every row must record a complete invocation, with the
/// gate **by value** -- `default` is rejected, because that is exactly the
/// record that cannot be told apart from an omission, and `DEFAULT_GATE` has
/// already moved once.
#[test]
fn every_registry_row_records_a_complete_invocation() {
    let rows = parse_registry();
    assert!(
        !rows.is_empty(),
        "\n{REGISTRY_FILE}: the registry is empty. An empty registry passes every \
         other check in this file while proving nothing.\n"
    );

    let mut ids = BTreeSet::new();
    for r in &rows {
        let at = format!("{REGISTRY_FILE}:{}", r.line);

        assert!(
            ids.insert(r.id.clone()),
            "\n{at}: duplicate id `{}`.\n",
            r.id
        );
        assert!(
            !r.id.is_empty()
                && r.id
                    .chars()
                    .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-'),
            "\n{at}: id `{}` must be kebab-case (rule 19).\n",
            r.id
        );

        assert!(
            !r.stack.is_empty() && !r.stack.contains(['/', '\\', ':']),
            "\n{at}: stack `{}` must be a single directory name under the capture \
             library, not a path -- the library root is machine-local and belongs in \
             $STREHL_CAPTURES, not in a frozen record.\n",
            r.stack
        );

        let limit: usize = r
            .limit
            .parse()
            .unwrap_or_else(|_| panic!("\n{at}: limit `{}` is not a positive integer.\n", r.limit));
        assert!(limit > 0, "\n{at}: limit must be > 0.\n");

        // The backend, by name, for the reason the gate is recorded by value
        // one assertion below -- and for one the gate never had. Until a
        // pyramid row existed, `Freeze::argv` hardcoded `--merge estimator`
        // into every row while `DEFAULT_MERGE_BACKEND` was already `pyramid`,
        // so a green registry certified only the backend nobody runs by
        // default. A regression in the pyramid path could not have tripped
        // anything in this file. This column is what fixes that, and it is
        // worth nothing unless at least one row on each backend exists -- which
        // is what the next assertion, outside the loop, requires.
        assert!(
            matches!(r.merge.as_str(), ESTIMATOR | PYRAMID),
            "\n{at}: merge = `{}`; use `{ESTIMATOR}` or `{PYRAMID}` -- the two spellings \
             `--merge` itself accepts.\n",
            r.merge
        );

        assert!(
            !matches!(
                r.gate.trim().to_ascii_lowercase().as_str(),
                "" | "default" | "-" | "none" | "n/a"
            ),
            "\n{at}: gate = `{}`.\n\n\
             RECORD THE VALUE, NOT THE FACT THAT YOU LEFT IT ALONE (rule 47).\n\
             `DEFAULT_GATE` is 4.0 today and was not always. A freeze recorded as \
             `default` cannot be reproduced, cannot be falsified, and cannot be told \
             apart from a row where somebody forgot the flag -- and that exact \
             ambiguity cost a 1.9-hour investigation into a regression that had never \
             happened (SYNTHESIS fact 1379).\n",
            r.gate
        );
        let gate: f32 = r
            .gate
            .parse()
            .unwrap_or_else(|_| panic!("\n{at}: gate `{}` is not a number.\n", r.gate));
        assert!(
            gate.is_finite() && gate >= 0.0,
            "\n{at}: gate must be finite and non-negative.\n"
        );

        let expected_mode = if r.env_align == "0" {
            "off"
        } else {
            "on-sidecar-override"
        };
        assert_eq!(
            r.alignment_mode, expected_mode,
            "\n{at}: env_align = `{}` / env_warpmap = `{}` must report alignment_mode \
             `{expected_mode}`, not `{}`. These columns are the SETTING and the \
             OBSERVATION; the test asserts the observation, which is how a silent flip \
             of the alignment default gets caught (that is what M86c did).\n\n\
             Note that `on-sidecar-cache` is not among the admissible values here, and \
             cannot be: it means the render was registered by a file the harness did not \
             put there. It is a legal OBSERVATION and an illegal RECORD.\n",
            r.env_align, r.env_warpmap, r.alignment_mode
        );

        if r.env_warpmap != UNSET {
            let p = Freeze::fixture_dir().join(&r.env_warpmap);
            assert!(
                p.is_file(),
                "\n{at}: the warp fixture `{}` does not exist.\n\
                 It is committed data, not a cache: regenerate it with\n\
                   strehl align <stackdir> --limit {} --out {}\n\
                 and say in your report why the registration changed.\n",
                p.display(),
                r.limit,
                p.display()
            );
        }

        assert!(
            r.env_cache_dir == SCRATCH,
            "\n{at}: env_cache_dir = `{}`; the only admissible value is `{SCRATCH}`.\n\n\
             $STREHL_CACHE_DIR is where `align` caches solved sidecars, and it defaults \
             to a SHARED per-user directory. A freeze that reads it is a freeze that \
             depends on whatever another agent last solved on this machine. `{SCRATCH}` \
             means the harness supplies an empty per-run directory, so the row's own \
             mode is the only thing that can register it.\n",
            r.env_cache_dir
        );

        assert!(
            !r.frames.is_empty() && r.frames.contains("..") && !r.frames.contains(' '),
            "\n{at}: frames = `{}` must name the range --limit selects, as \
             `FIRST..LAST` (for example `DSC00016..DSC00035`).\n\n\
             `--limit 20` is not reproducible without knowing WHICH twenty. The flag \
             takes a prefix of the directory in name order, so the range moves the \
             moment a frame is added, removed or renamed -- and the hash moves with it, \
             for a reason that has nothing to do with the renderer.\n",
            r.frames
        );

        assert!(
            r.sha256.len() == 64
                && r.sha256
                    .chars()
                    .all(|c| c.is_ascii_digit() || ('A'..='F').contains(&c)),
            "\n{at}: sha256 `{}` must be 64 UPPERCASE hex characters. Truncated \
             hashes belong in prose, never in the registry -- the corpus already \
             carries a freeze recorded only as `D99F5D82...76CA`, which cannot be \
             checked by anything.\n",
            r.sha256
        );
        assert!(r.bytes > 0, "\n{at}: bytes must be > 0.\n");

        assert!(
            r.baselined_at.len() >= 7 && r.baselined_at.chars().all(|c| c.is_ascii_hexdigit()),
            "\n{at}: baselined_at `{}` must be a git sha of at least 7 hex digits \
             (rule 31: a freeze measured against an uncommitted tree cannot be \
             reproduced by anyone else).\n",
            r.baselined_at
        );
        let d: Vec<&str> = r.baselined_on.split('-').collect();
        assert!(
            d.len() == 3
                && d[0].len() == 4
                && d[1].len() == 2
                && d[2].len() == 2
                && r.baselined_on
                    .chars()
                    .all(|c| c.is_ascii_digit() || c == '-'),
            "\n{at}: baselined_on `{}` must be YYYY-MM-DD.\n",
            r.baselined_on
        );

        assert!(
            r.why.len() >= 60
                && !matches!(
                    r.why.trim().to_ascii_lowercase().as_str(),
                    "" | "-" | "tbd" | "todo" | "n/a" | "see report"
                ),
            "\n{at}: `why` is {} characters and must be a real explanation.\n\n\
             This is the column that would have prevented SYNTHESIS fact 1379. It \
             must say what this hash IS, what moved it last, and why that move was \
             correct. If you re-baselined this row, REWRITE this column -- a `why` \
             that still describes the previous baseline is worse than an empty one, \
             because it reads as current.\n",
            r.why.len()
        );
    }

    // THE DEFAULT BACKEND MUST BE FROZEN BY SOMETHING.
    //
    // This is the assertion the registry did not have, and its absence was a
    // hole rather than an omission: for the whole life of this file every row
    // ran `--merge estimator`, while `DEFAULT_MERGE_BACKEND` had already moved
    // to `pyramid`. A green byte-freeze certified the backend nobody gets by
    // default, and a regression in the path every default render takes could
    // not trip a single check here.
    //
    // Written against the SPELLINGS rather than against
    // `merge_cmd::DEFAULT_MERGE_BACKEND`, deliberately: this test drives the
    // binary through argv as a stranger would, and a check that imported the
    // constant would follow it wherever it went. What is wanted is coverage of
    // BOTH backends at all times, so that whichever one the constant names, the
    // registry already froze it. Freezing everything is the same as freezing
    // nothing -- but freezing neither arm of a switch that selects the whole
    // merge is worse than either.
    for backend in [ESTIMATOR, PYRAMID] {
        assert!(
            rows.iter().any(|r| r.merge == backend),
            "\n{REGISTRY_FILE}: no row freezes `--merge {backend}`.\n\n\
             Both backends must be covered, because `DEFAULT_MERGE_BACKEND` selects \
             one of them for every render that does not name one, and it has already \
             moved once. A registry that covers only the non-default backend is the \
             defect this assertion was written for: it goes green while the path every \
             default render takes is unguarded.\n\n\
             Do not delete a backend's last row to make this pass. Add one.\n"
        );
    }
}

/// The anti-splice check, and a power check on the pair.
///
/// Two rows may not freeze the same invocation, because then a mismatch names
/// two possible causes. And two rows that differ **only** in alignment must have
/// **different** hashes: if they agreed, the aligned row would carry no
/// information about alignment at all and would be arithmetic rather than
/// evidence (rule 20).
#[test]
fn no_two_rows_freeze_the_same_invocation() {
    let rows = parse_registry();
    // The key is the WHOLE rule-47 record: the flags and the environment. An
    // earlier version keyed on flags plus an alignment mode enum, which would
    // have let two rows differing only in, say, STREHL_FIX_HALO collide.
    let key = |r: &Freeze| {
        format!(
            "{}|{}|{}|{}|{}|{}|{}|{}|{}",
            r.stack,
            r.frames,
            r.limit,
            r.merge,
            r.gate,
            r.srgb,
            r.env_align,
            r.env_warpmap,
            r.env_fix_halo
        )
    };
    let mut seen: Vec<(String, String)> = Vec::new();
    for r in &rows {
        let k = key(r);
        if let Some((other, _)) = seen.iter().find(|(_, kk)| *kk == k) {
            panic!(
                "\n{REGISTRY_FILE}:{}: `{}` freezes the same invocation as `{other}`.\n\
                 Two hashes for one command means one of them is wrong and nothing \
                 says which.\n",
                r.line, r.id
            );
        }
        seen.push((r.id.clone(), k));
    }

    // "Differ only in alignment" has to mean it. `merge` joins the key for the
    // same reason `gate` is in it: two rows on DIFFERENT backends are not a
    // registration pair at all, and comparing them would report a merge
    // difference as if it were an alignment result.
    let no_align =
        |r: &Freeze| format!("{}|{}|{}|{}|{}", r.stack, r.limit, r.merge, r.gate, r.srgb);
    for (i, a) in rows.iter().enumerate() {
        for b in rows.iter().skip(i + 1) {
            if no_align(a) == no_align(b) {
                assert_ne!(
                    a.sha256, b.sha256,
                    "\n{REGISTRY_FILE}: `{}` and `{}` differ only in alignment yet \
                     record the SAME hash.\n\n\
                     Then the pair has no power: whichever of them you check, you learn \
                     nothing about registration. Either one of the two rows is \
                     mis-recorded, or registration has become a no-op on this stack -- \
                     and that second possibility is a finding, not something to \
                     record quietly in a table.\n",
                    a.id, b.id
                );
            }
        }
    }
}

// ---------------------------------------------------------------------------
// The render
// ---------------------------------------------------------------------------

/// Pull `alignment      : ...` out of the render log and normalise it to the
/// coarse token the registry records.
///
/// Deliberately coarse: the full line carries prose that a later milestone will
/// reword, and a freeze that fires on a reworded sentence teaches the reader to
/// ignore it. What is asserted is the MODE, which is the thing that must never
/// change without somebody deciding it should.
fn alignment_mode(log: &str) -> String {
    let mut found = None;
    for line in log.lines() {
        let Some(rest) = line
            .split_once(':')
            .and_then(|(k, v)| k.trim_start().starts_with("alignment").then_some(v.trim()))
        else {
            continue;
        };
        // `ON (sidecar-override)` must be tested before `ON (sidecar)`, which is
        // a prefix of it. Getting that order wrong would report every overridden
        // run as a cache hit -- and since the cache-hit token is the poisoning
        // signature below, that would be an alarm nobody could act on.
        let token = if rest.starts_with("OFF") {
            "off"
        } else if rest.starts_with("ON (solved)") {
            "on-solved"
        } else if rest.starts_with("ON (sidecar-override)") {
            "on-sidecar-override"
        } else if rest.starts_with("ON (sidecar)") {
            // A CACHED sidecar was loaded from `$STREHL_CACHE_DIR`. No row may
            // record this: it means the render was registered by a file this
            // test did not put there and cannot see. It is a distinct token
            // rather than a fall-through to MISSING because it is the ONE
            // observable difference between a fresh solve and a poisoned one,
            // and a reader who sees `MISSING` learns nothing while a reader who
            // sees `on-sidecar-cache` has the diagnosis.
            //
            // Measured, not theorised: swapping two placements inside a cached
            // sidecar (leaving its frame count and stack digest valid, which
            // `StackIdentity` cannot see past -- `warpmap.rs:238`) moved a
            // render from 119936E6... to 8065EA8D... at exit 0, with
            // `20 placed / 0 refused` and every ordinary guard green. The only
            // thing that changed on stderr was this token.
            "on-sidecar-cache"
        } else {
            continue;
        };
        found = Some(token.to_string());
    }
    found.unwrap_or_else(|| "MISSING (no `alignment : ON/OFF` line in the log)".to_string())
}

/// The chunking fingerprint, for the failure message only.
///
/// Two backends, two lines, because they partition the fold differently and
/// each says so in its own words:
///
/// * the estimator prints `workers         : N chunks of <= M frames (...)`;
/// * the pyramid prints `memory plan     : N workers x M MB = ... budget, ...`
///   and no `workers` line at all.
///
/// The pyramid arm was added with the first pyramid row. Without it that row
/// would record `unknown` in the `workers` column -- and this column exists to
/// be "the first thing to suspect when a hash moves on a machine that is not
/// the one above", which `unknown` cannot be. Only the host-dependent head of
/// the line is kept (`N workers x M MB`); everything after the `=` is derived
/// from it and the timings that follow are not reproducible text.
fn workers_line(log: &str) -> String {
    log.lines()
        .find_map(|l| {
            let (k, v) = l.split_once(':')?;
            k.trim_start().starts_with("workers").then(|| {
                v.trim()
                    .split_once(" (")
                    .map(|(a, _)| a.to_string())
                    .unwrap_or_else(|| v.trim().to_string())
            })
        })
        .or_else(|| {
            log.lines().find_map(|l| {
                let (k, v) = l.split_once(':')?;
                k.trim_start().starts_with("memory plan").then(|| {
                    v.trim()
                        .split_once(" = ")
                        .map(|(a, _)| a.to_string())
                        .unwrap_or_else(|| v.trim().to_string())
                })
            })
        })
        .unwrap_or_else(|| "unknown".to_string())
}

/// The `N placed / M refused` counts on the `alignment` line.
///
/// **Derived, never recorded.** `placed` must equal `--limit` and `refused`
/// must be zero, and both of those come from the row's own `limit` rather than
/// from a column somebody could re-baseline. A recorded count can be edited by
/// the same hand that edits a hash; a derived one cannot.
///
/// This is the check that catches a sidecar solved over a *different subset* of
/// the bracket. `load_or_solve` compares `map.len() == paths.len()` and
/// re-solves on a mismatch, so an 8-frame sidecar under a `--limit 20` run is
/// caught -- but `StackIdentity::from_paths` digests only filename and file
/// length (`warpmap.rs:238`), never content, so an 8-frame sidecar under a
/// `--limit 8` run is accepted **silently** even though it may have come from a
/// different reference frame, a different subset or a different resampler. The
/// count is the only thing on the tool's own output that can see that.
fn placement(log: &str) -> Option<(usize, usize)> {
    let line = log.lines().rev().find(|l| {
        l.split_once(':')
            .is_some_and(|(k, _)| k.trim_start().starts_with("alignment"))
            && l.contains("placed")
    })?;
    let toks: Vec<&str> = line.split_whitespace().collect();
    let grab = |word: &str| -> Option<usize> {
        toks.iter()
            .position(|t| *t == word)
            .and_then(|i| i.checked_sub(1))
            .and_then(|i| toks[i].parse().ok())
    };
    Some((grab("placed")?, grab("refused")?))
}

fn hash_file(p: &Path) -> (String, u64) {
    use std::io::Read;
    let mut f = std::fs::File::open(p)
        .unwrap_or_else(|e| panic!("opening the render `{}`: {e}", p.display()));
    let mut h = sha256::Hasher::new();
    let mut buf = vec![0u8; 64 * 1024];
    let mut total = 0u64;
    loop {
        let n = f.read(&mut buf).expect("reading the render");
        if n == 0 {
            break;
        }
        total += n as u64;
        h.update(&buf[..n]);
    }
    (sha256::hex(&h.finish()), total)
}

/// Names of the entries in a directory. Names only, not mtimes: several agents
/// share this machine and one of them rewriting a file it already owns is not
/// evidence about *this* test, whereas a NEW file appearing is.
fn entry_names(dir: &Path) -> BTreeSet<String> {
    std::fs::read_dir(dir)
        .map(|it| {
            it.filter_map(|e| e.ok())
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .collect()
        })
        .unwrap_or_default()
}

/// One render, with everything the checks downstream need to read.
struct Rendered {
    pass: u32,
    hash: String,
    bytes: u64,
    mode: String,
    workers: String,
    placement: Option<(usize, usize)>,
    scratch: PathBuf,
    out: PathBuf,
}

/// A canary on the shared resource, deliberately **not** an assertion.
///
/// The capture library is read-only and several agents share this machine. A
/// stray sidecar there is a real problem, but it is not necessarily *this*
/// runner's problem, and turning someone else's mistake into your red teaches
/// you to ignore reds. So this prints and names names. What IS asserted is that
/// this test's own renders add nothing -- see the hermeticity check in `render`.
fn report_strays(lib: &Path) {
    let mut strays = Vec::new();
    if let Ok(top) = std::fs::read_dir(lib) {
        for stack in top.filter_map(|e| e.ok()) {
            let dir = stack.path();
            if !dir.is_dir() {
                continue;
            }
            if let Ok(inner) = std::fs::read_dir(&dir) {
                for f in inner.filter_map(|e| e.ok()) {
                    let name = f.file_name().to_string_lossy().into_owned();
                    if name.contains("warpmap") {
                        strays.push(f.path().display().to_string());
                    }
                }
            }
        }
    }
    if strays.is_empty() {
        return;
    }
    note(&format!(
        "\n\
         ------------------------------------------------------------------------------\n\
         WARNING: the read-only capture library contains {} stray sidecar file(s):\n\
         {}\n\n\
         Nothing in this test wrote them -- every row here runs with STREHL_ALIGN=0 or\n\
         STREHL_WARPMAP, neither of which writes anywhere. Some other process did, and\n\
         AGENTS.md rule 45 says nothing may. They should be quarantined out, not left.\n\n\
         This is a WARNING and not a failure because another agent's write is not\n\
         evidence about this test. It is written to the REAL stderr because libtest\n\
         captures the `print!` family for passing tests -- and this warning only ever\n\
         appears on a run that passes, so printed the ordinary way it would never once\n\
         have been seen. Eleven of these accumulated in one night before anybody\n\
         looked.\n\
         ------------------------------------------------------------------------------",
        strays.len(),
        strays
            .iter()
            .map(|s| format!("  {s}"))
            .collect::<Vec<_>>()
            .join("\n")
    ));
}

/// Run the row's own command once, in its own process, and read back everything
/// the gates need.
fn render(r: &Freeze, stack_dir: &Path, pass: u32) -> Rendered {
    let scratch = std::env::temp_dir().join(format!(
        "strehl-freeze-{}-{}-p{pass}",
        std::process::id(),
        r.id
    ));
    let _ = std::fs::remove_dir_all(&scratch);
    std::fs::create_dir_all(&scratch).expect("creating the scratch directory");
    let out = scratch.join("render.tif");

    let before = entry_names(stack_dir);

    let mut cmd = Command::new(env!("CARGO_BIN_EXE_strehl"));
    cmd.args(r.argv(stack_dir, &out));
    for name in RENDER_ENV {
        cmd.env_remove(name);
    }
    for (k, v) in r.env(&scratch) {
        cmd.env(k, v);
    }
    let output = cmd
        .output()
        .unwrap_or_else(|e| panic!("running `{}`: {e}", env!("CARGO_BIN_EXE_strehl")));
    let log = String::from_utf8_lossy(&output.stderr).into_owned();

    let after = entry_names(stack_dir);
    assert_eq!(
        before,
        after,
        "\n\nHERMETICITY FAILURE for `{}` (pass {pass}).\n\
         The capture directory `{}` gained or lost an entry while this render ran.\n\
         Added: {:?}\n\
         That library is the owner's irreplaceable data and is strictly read-only\n\
         (AGENTS.md rule 45). Nothing here may write to it. If a sidecar appeared,\n\
         the alignment mode of this row is no longer hermetic and the row must be\n\
         changed, not the assertion.\n\
         (Several agents share this machine; if another process created the file,\n\
         this still needs a human, because the library is supposed to be clean.)\n",
        r.id,
        stack_dir.display(),
        after.difference(&before).collect::<Vec<_>>()
    );

    assert!(
        output.status.success(),
        "\n\nThe frozen render for `{}` FAILED TO RUN (exit {:?}, pass {pass}).\n\
         This is not a moved hash -- the command did not complete.\n\n\
         What the tool reported about registration before it stopped:\n\
         \x20 alignment : {mode}\n\
         \x20 placement : {place}\n\
         If the placement count is short of `--limit {limit}`, that IS the diagnosis:\n\
         the warp map and the bracket disagree, and `merge_cmd.rs:932` refuses to\n\
         merge a frame the solve refused rather than quietly giving it identity.\n\n\
         Command:\n{}\n\nLog:\n{log}\n",
        r.id,
        output.status.code(),
        r.command(stack_dir, &out),
        mode = alignment_mode(&log),
        place = match placement(&log) {
            Some((p, f)) => format!("{p} placed / {f} refused"),
            None => "not reported".to_string(),
        },
        limit = r.limit
    );

    let (hash, bytes) = hash_file(&out);
    Rendered {
        pass,
        hash,
        bytes,
        mode: alignment_mode(&log),
        workers: workers_line(&log),
        placement: placement(&log),
        scratch,
        out,
    }
}

/// The two gates that must pass **before** any hash is compared.
///
/// A hash is only evidence about the pipeline the row describes. If the tool
/// did not actually run that pipeline, comparing hashes is not a weak check --
/// it is a check of something else entirely, and it will be green or red for
/// reasons that have nothing to do with the freeze.
///
/// **On the placement gate, honestly.** As the code stands, `placed == limit &&
/// refused == 0` is *implied by the run succeeding*: `load_or_solve` requires
/// `map.len() == paths.len()`, every entry is either placed or refused, and
/// `merge_cmd.rs:932` bails on a refused frame rather than giving it identity.
/// I planted a refused frame in a copy of the fixture and measured exactly that
/// -- `19 placed / 1 refused`, then exit 1. So today this assertion cannot fail
/// where the exit-code check would not have failed first, and pretending
/// otherwise would be the same overclaim this milestone exists to stop.
///
/// It is kept because it is a **tripwire on that guarantee**, not a duplicate of
/// it. "Warn and skip the bad frame instead of failing the whole render" is an
/// obvious, well-meant change for somebody to make; the moment it lands, the
/// exit code stops carrying this information and a short placement becomes
/// silent. This assertion is what would notice, and it costs one line.
fn check_pipeline(r: &Freeze, g: &Rendered, stack_dir: &Path, out: &Path) {
    let bar = "=".repeat(78);

    assert!(
        g.mode == r.alignment_mode,
        "\n\n{bar}\n\
         ENVIRONMENT NOT ISOLATED: `{id}` (pass {pass})\n\
         {bar}\n\n\
         This row freezes a specific pipeline, and `strehl stack` reported a\n\
         different one on its own output. NO HASH WAS COMPARED, because a hash from\n\
         the wrong pipeline is not weak evidence -- it is evidence about something\n\
         else.\n\n\
         \x20 registry says the tool must report : {want}\n\
         \x20 the tool actually reported         : {got}\n\n\
         The `alignment` line is the tool's own statement about which pipeline it\n\
         ran. `MISSING` means no such line was found at all, which means either the\n\
         binary is older than the alignment wiring or the line has been reworded --\n\
         and in the second case this check has gone blind and must be repaired, not\n\
         removed.\n\n\
         WHAT USUALLY CAUSES THIS\n\
         \x20 * An ambient STREHL_ALIGN / STREHL_WARPMAP in the shell. This test\n\
         \x20   removes all of {n} render variables before applying the row's own,\n\
         \x20   so if that is the cause, the removal list is now incomplete.\n\
         \x20 * A sidecar the tool discovered by itself. The capture library is\n\
         \x20   read-only and must contain none; the warning printed at the top of\n\
         \x20   this test lists any it found.\n\
         \x20 * The row is simply wrong about the mode. Fix the row.\n\
         {cache}\n\
         Command that was run:\n{cmd}\n",
        id = r.id,
        pass = g.pass,
        want = r.alignment_mode,
        got = g.mode,
        n = RENDER_ENV.len(),
        cache = if g.mode == "on-sidecar-cache" {
            "\n\
             THIS PARTICULAR MISMATCH IS THE DANGEROUS ONE. `on-sidecar-cache` means\n\
             the render was registered by a CACHED sidecar under $STREHL_CACHE_DIR --\n\
             a file this harness did not write and cannot inspect. The row sets that\n\
             variable to a fresh empty directory precisely so this cannot happen, so\n\
             seeing it means the isolation itself has failed.\n\n\
             Do not re-baseline against it. `StackIdentity::from_paths` digests\n\
             filenames and file LENGTHS only (`warpmap.rs:238`), never contents, so a\n\
             cache entry whose placements have been altered passes every check the\n\
             tool makes. Measured at fea1a72: swapping two placements inside one moved\n\
             this bracket's render from 119936E6... to 8065EA8D... at exit 0, still\n\
             reporting `20 placed / 0 refused`. A hash frozen against a cache hit is a\n\
             hash frozen against ambient state.\n"
        } else {
            ""
        },
        cmd = r.command(stack_dir, out)
    );

    // Alignment off places nothing, so there is no count to check; the mode
    // assertion above is the whole of the isolation check for those rows.
    if r.env_align == "0" {
        return;
    }

    let limit: usize = r.limit.parse().expect("limit was validated at parse time");
    let Some((placed, refused)) = g.placement else {
        panic!(
            "\n\n{bar}\n\
             PLACEMENT COUNT UNREADABLE: `{id}` (pass {pass})\n\
             {bar}\n\n\
             This row aligns from a sidecar, so `strehl stack` should have reported\n\
             `N placed / M refused` on its `alignment` line and did not. That count is\n\
             the only signal on the tool's output that the warp map covers the frames\n\
             actually being merged.\n\n\
             It matters because `StackIdentity::from_paths` digests filename and file\n\
             LENGTH only (`warpmap.rs:238`), never content: a sidecar solved from a\n\
             different reference frame, a different subset or a different resampler is\n\
             accepted silently as long as the frame COUNT matches. Without this line\n\
             that acceptance is invisible.\n\n\
             Repair this parser -- do not delete the check.\n\n\
             Command that was run:\n{cmd}\n",
            id = r.id,
            pass = g.pass,
            cmd = r.command(stack_dir, out)
        )
    };

    assert!(
        placed == limit && refused == 0,
        "\n\n{bar}\n\
         PLACEMENT DOES NOT MATCH THE BRACKET: `{id}` (pass {pass})\n\
         {bar}\n\n\
         \x20 --limit says frames to merge : {limit}\n\
         \x20 the tool placed              : {placed}\n\
         \x20 the tool refused             : {refused}\n\n\
         Both numbers are DERIVED from the row, not recorded in it, precisely so\n\
         that they cannot be re-baselined into agreement with a bad sidecar.\n\n\
         Every frame in the bracket must be placed and none refused, or the render\n\
         is not the render this row froze. A partial placement means the warp map\n\
         and the bracket disagree -- and that disagreement is exactly the failure\n\
         `StackIdentity` cannot see, because it digests filename and file length\n\
         only (`warpmap.rs:238`) and never content. A 40-frame solve was found\n\
         sitting under a 299-frame bracket on the flagship stack.\n\n\
         IF YOU ARE READING THIS, SOMETHING CHANGED IN THE TOOL. On the code as\n\
         measured, a refused frame makes `merge_cmd.rs:932` bail and the run exits\n\
         non-zero, so this assertion should be unreachable -- see its doc comment.\n\
         Reaching it means the refusal is no longer fatal, which means the exit\n\
         code no longer carries this information and this check is now the only\n\
         thing that sees it. Do not relax it.\n\n\
         Check the fixture `tests/data/` this row names, and check that nothing\n\
         wrote a sidecar into the capture directory underneath the run.\n\n\
         Command that was run:\n{cmd}\n",
        id = r.id,
        pass = g.pass,
        cmd = r.command(stack_dir, out)
    );
}

#[test]
fn the_frozen_renders_still_produce_their_recorded_bytes() {
    let rows = parse_registry();
    let lib = match capture_library() {
        Ok(lib) => lib,
        Err(why) => {
            skip(&why);
            return;
        }
    };

    report_strays(&lib);

    for r in &rows {
        let stack_dir = lib.join(&r.stack);
        assert!(
            stack_dir.is_dir(),
            "\nThe capture library `{}` exists but has no `{}` in it.\n\
             This is a hard failure and not a skip on purpose: a machine that has the\n\
             library is a machine that must run the freeze, so the only way to skip is\n\
             to genuinely not have the data.\n",
            lib.display(),
            r.stack
        );

        check_frame_range(r, &stack_dir);

        // TWO passes, in two SEPARATE PROCESSES, before either hash is trusted.
        //
        // This separates two failures that a single render conflates. If the two
        // passes disagree with each other, the pipeline is not deterministic
        // under the conditions being frozen, and no hash here means anything --
        // that is a more serious finding than a moved freeze and it gets its own
        // message. If they agree with each other but not with the registry, the
        // pipeline is deterministic and something moved, which is the ordinary
        // case this test exists for.
        let a = render(r, &stack_dir, 1);
        check_pipeline(r, &a, &stack_dir, &a.out);
        let b = render(r, &stack_dir, 2);
        check_pipeline(r, &b, &stack_dir, &b.out);

        assert!(
            a.hash == b.hash && a.bytes == b.bytes,
            "{}",
            nondeterminism_report(r, &stack_dir, &a, &b)
        );

        if a.hash == r.sha256 && a.bytes == r.bytes {
            // Real stderr, not `println!`. This is the POSITIVE half of the
            // same fix: a passing run has to be able to say what it checked.
            // Without it, "5 passed" is emitted identically by a run that
            // verified both freezes and a run that verified none, and the
            // difference is the whole value of the test.
            note(&format!(
                "freeze `{}` HOLDS: {} ({} bytes, alignment {}, {}{}) -- reproduced twice",
                r.id,
                r.sha256,
                r.bytes,
                a.mode,
                a.workers,
                match a.placement {
                    Some((p, f)) => format!(", {p} placed / {f} refused"),
                    None => String::new(),
                }
            ));
            let _ = std::fs::remove_dir_all(&a.scratch);
            let _ = std::fs::remove_dir_all(&b.scratch);
            continue;
        }

        // Keep pass 1's artifact: the first thing anyone will want is to diff it.
        let _ = std::fs::remove_dir_all(&b.scratch);
        panic!(
            "{}",
            moved_report(r, &stack_dir, &a.out, &a.hash, a.bytes, &a.mode, &a.workers)
        );
    }
}

/// The fourth gate: `--limit N` must select the frames the row says it selects.
///
/// Checked against the directory **before** anything is rendered, because a
/// changed frame range moves the hash for a reason that has nothing to do with
/// the renderer, and that is the most expensive kind of false break: it looks
/// exactly like a regression. `--limit` takes a prefix in name order, so adding
/// one file to the front of a bracket silently reframes every freeze on it.
///
/// This is the one gate whose expected value is RECORDED rather than derived --
/// it has to be, since the whole point is to detect the directory changing under
/// the record. It is therefore also the one gate a careless re-baseline can
/// silence, which is why the failure message insists on an explanation.
fn check_frame_range(r: &Freeze, stack_dir: &Path) {
    let limit: usize = r.limit.parse().expect("limit was validated at parse time");
    let mut names: Vec<String> = std::fs::read_dir(stack_dir)
        .unwrap_or_else(|e| panic!("reading `{}`: {e}", stack_dir.display()))
        .filter_map(|e| e.ok())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .filter(|n| n.to_ascii_lowercase().ends_with(".arw"))
        .collect();
    names.sort();

    let bar = "=".repeat(78);
    assert!(
        names.len() >= limit,
        "\n\n{bar}\n\
         FRAME RANGE: `{id}` wants {limit} frames and `{dir}` holds {have}\n\
         {bar}\n\n\
         The bracket has lost frames, or this is not the bracket the row was\n\
         measured against. Either way the freeze cannot be evaluated -- rendering\n\
         fewer frames would produce a different image and report it as a moved hash.\n",
        id = r.id,
        dir = stack_dir.display(),
        have = names.len()
    );

    let stem = |n: &str| {
        n.rsplit_once('.')
            .map_or(n.to_string(), |(s, _)| s.to_string())
    };
    let got = format!("{}..{}", stem(&names[0]), stem(&names[limit - 1]));
    assert!(
        got == r.frames,
        "\n\n{bar}\n\
         FRAME RANGE MOVED: `{id}`\n\
         {bar}\n\n\
         \x20 registry says : {want}\n\
         \x20 directory has : {got}\n\
         \x20 stack         : {dir}\n\
         \x20 --limit       : {limit}   (a PREFIX in name order, not a selection)\n\n\
         NOTHING HAS BEEN RENDERED. This is deliberate: the hash below would have\n\
         moved, and it would have looked like a renderer regression when in fact the\n\
         INPUT changed. That confusion is the whole reason this column exists.\n\n\
         What to do:\n\n\
         \x20 * If a frame was ADDED to or REMOVED from the bracket, the capture\n\
         \x20   library is supposed to be immutable (AGENTS.md rule 45) and somebody\n\
         \x20   has modified the owner's data. Investigate that FIRST; do not\n\
         \x20   re-baseline over it.\n\n\
         \x20 * If a NON-frame file was added or removed, only this check is affected\n\
         \x20   and the hash is fine -- but the registry still has to be corrected.\n\n\
         \x20 * If the bracket legitimately changed, the freeze is measuring a\n\
         \x20   different subject and must be RE-BASELINED, with `frames` and `why`\n\
         \x20   both rewritten. A `why` that does not mention the reframing is worse\n\
         \x20   than no `why` at all.\n\n\
         \x20 * Row is at {file}:{line}.\n",
        id = r.id,
        want = r.frames,
        dir = stack_dir.display(),
        file = REGISTRY_FILE,
        line = r.line
    );
}

/// The two passes disagreed with each other. This is not a moved freeze.
fn nondeterminism_report(r: &Freeze, stack_dir: &Path, a: &Rendered, b: &Rendered) -> String {
    let bar = "=".repeat(78);
    format!(
        "\n\n{bar}\n\
         NOT DETERMINISTIC: `{id}` rendered twice and produced two different files\n\
         {bar}\n\n\
         \x20 pass 1 sha256 : {ah}  ({ab} bytes)\n\
         \x20 pass 2 sha256 : {bh}  ({bb} bytes)\n\
         \x20 registry says : {rh}  ({rb} bytes)\n\n\
         Two runs of the SAME command, in two separate processes, on the same\n\
         inputs, disagreed. **Do not re-baseline anything.** A freeze on a\n\
         non-deterministic pipeline is not a weak freeze; it is a coin toss that\n\
         will be red for one person in two and get deleted by the third.\n\n\
         This is a more important finding than a moved hash and it should be\n\
         reported as one. Likely causes, roughly in order:\n\n\
         \x20 * A reduction whose order depends on thread scheduling. The merge\n\
         \x20   reduces in a chunk tree and f32 addition is not associative, so an\n\
         \x20   order that varies run to run varies the low bits. Try pinning\n\
         \x20   RAYON_NUM_THREADS and see whether the disagreement disappears --\n\
         \x20   if it does, that is the answer.\n\
         \x20 * Something in the render reading wall-clock time, a process id, a\n\
         \x20   hash-map iteration order, or an uninitialised buffer.\n\
         \x20 * Something MUTATING UNDERNEATH THE RUN. The capture library is\n\
         \x20   read-only and shared; if another process wrote a sidecar or touched\n\
         \x20   a frame between the two passes, the two passes did not have the\n\
         \x20   same inputs. The hermeticity check in this test compares entry\n\
         \x20   NAMES, so a rewritten file with an unchanged name passes it.\n\
         \x20   Check that first if the library is not quiet.\n\n\
         \x20 pass 1 alignment : {am} ({aw}){ap}\n\
         \x20 pass 2 alignment : {bm} ({bw}){bp}\n\n\
         Both renders were kept:\n\
         \x20 {ao}\n\
         \x20 {bo}\n\n\
         Command (identical for both passes, generated from the registry row):\n{cmd}\n",
        id = r.id,
        ah = a.hash,
        ab = a.bytes,
        bh = b.hash,
        bb = b.bytes,
        rh = r.sha256,
        rb = r.bytes,
        am = a.mode,
        aw = a.workers,
        bm = b.mode,
        bw = b.workers,
        ap = match a.placement {
            Some((p, f)) => format!(", {p} placed / {f} refused"),
            None => String::new(),
        },
        bp = match b.placement {
            Some((p, f)) => format!(", {p} placed / {f} refused"),
            None => String::new(),
        },
        ao = a.out.display(),
        bo = b.out.display(),
        cmd = r.command(stack_dir, &a.out)
    )
}

/// The message a stranger hits in CI. It has to answer "what moved", "was it
/// me", and "what do I do now" without them reading a report first -- because
/// most moves here are intended, and a message that only says `assertion failed`
/// gets the test deleted.
#[allow(clippy::too_many_arguments)]
fn moved_report(
    r: &Freeze,
    stack_dir: &Path,
    out: &Path,
    got_hash: &str,
    got_bytes: u64,
    got_mode: &str,
    got_workers: &str,
) -> String {
    let mut s = String::new();
    let bar = "=".repeat(78);
    let _ = write!(
        s,
        "\n{bar}\nBYTE-FREEZE MOVED: {}\n{bar}\n\n\
         The render this row freezes no longer produces the recorded bytes.\n\n\
         \x20 expected sha256 : {}\n\
         \x20 actual   sha256 : {got_hash}\n\
         \x20 expected bytes  : {}\n\
         \x20 actual   bytes  : {got_bytes}{}\n\
         \x20 expected align  : {}\n\
         \x20 actual   align  : {got_mode}{}\n\
         \x20 baseline chunks : {}\n\
         \x20 this run chunks : {got_workers}{}\n\n\
         The render was kept at:\n\x20 {}\n\n\
         THE EXACT COMMAND THAT PRODUCED THE `actual` NUMBERS. It is generated from\n\
         the registry row, so it cannot be a different pipeline's command -- which is\n\
         the mistake that produced SYNTHESIS fact 1379:\n\n{}\n\n\
         Last re-baselined at {} on {}, because:\n\x20 \"{}\"\n\n{bar}\n\
         WHAT TO DO\n{bar}\n\
         Most moves here are INTENDED. This project lands quality improvements\n\
         constantly; the freeze exists to make a change visible and deliberate, not\n\
         to prevent it. Work out which case you are in.\n\n\
         (1) YOU DID NOT EXPECT THIS. Do not re-baseline yet.\n\
         \x20   - Re-render the baseline WITH ITS OWN RECORDED COMMAND (above) before\n\
         \x20     you diff a single commit. Rule 47's closing clause exists because the\n\
         \x20     last apparent break was a fabricated comparison, not a regression.\n\
         \x20   - Then bisect: run the same command at earlier commits.\n\
         \x20   - Read docs/research/M106-freeze-attribution.md first.\n\n\
         (2) YOU DID EXPECT THIS -- you changed the merge, the focus measure, the\n\
         \x20   encoder, the resampler, or a constant one of them reads. Re-baseline:\n\
         \x20   - edit {REGISTRY_FILE}, row `{}`\n\
         \x20   - sha256       -> {got_hash}\n\
         \x20   - bytes        -> {got_bytes}\n\
         \x20   - baselined_at -> the commit that moves it (COMMITTED; rule 31)\n\
         \x20   - baselined_on -> today\n\
         \x20   - why          -> REWRITE IT. Not \"see the report\". Say what moved\n\
         \x20                     the bytes and why that is correct. A `why` still\n\
         \x20                     describing the previous baseline is worse than an\n\
         \x20                     empty one, because it reads as current.\n\
         \x20   - say in your milestone report that you moved a freeze, and name it.\n\n\
         (3) YOU ARE NOT SURE IT IS YOURS. Stash your change, REBUILD, and re-run.\n\
         \x20   After restoring a file, set its mtime to now --\n\
         \x20   `(Get-Item <path>).LastWriteTime = Get-Date` -- or cargo will consider\n\
         \x20   the stale artifact fresh and you will test the binary you meant to\n\
         \x20   remove (AGENTS.md rule 33). Read the `Compiling` lines.\n\n\
         DO NOT delete this test, and do not #[ignore] it. If the row is wrong, fix\n\
         the row: that is a two-line edit and it leaves a record of who moved what.\n{bar}\n",
        r.id,
        r.sha256,
        r.bytes,
        if got_bytes == r.bytes {
            "   (unchanged -- same geometry, the pixel VALUES moved)"
        } else {
            "   <-- THE GEOMETRY CHANGED. Suspect resolution, binning or demosaic \
             before you suspect the merge."
        },
        r.alignment_mode,
        if got_mode == r.alignment_mode {
            "   (as recorded)"
        } else {
            "   <-- THE PIPELINE CHANGED, not just its output. This row rendered a \
             different pipeline than the one it freezes; fix that before reading the hash."
        },
        r.workers,
        if got_workers == r.workers {
            "   (as recorded)"
        } else {
            "   <-- DIFFERENT CHUNKING. This is a property of the HOST (RAM and core \
             count), not of the code. If you are not on the machine named in the row, \
             suspect this FIRST: the merge reduces in a chunk tree and floating-point \
             addition is not associative. Reproduce on the baseline host, or \
             re-baseline for yours and say so."
        },
        out.display(),
        r.command(stack_dir, out),
        r.baselined_at,
        r.baselined_on,
        r.why,
        r.id,
    );
    s
}
