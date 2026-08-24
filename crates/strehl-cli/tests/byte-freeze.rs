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
//! `cargo test`.

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
    "limit",
    "gate",
    "srgb",
    "align",
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
    limit: String,
    gate: String,
    srgb: bool,
    align: Align,
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

#[derive(Debug, Clone, PartialEq, Eq)]
enum Align {
    /// `STREHL_ALIGN=0`.
    Off,
    /// `STREHL_WARPMAP=tests/data/<fixture>`.
    Sidecar(String),
}

/// Environment variables that change what `strehl stack` emits.
///
/// Every one of them is **removed** before a row's own settings are applied, so
/// the ambient environment of whoever runs the test cannot quietly render a
/// different pipeline than the row describes. This is the same defect as the
/// missing `--gate`, one layer down: an unrecorded input.
const RENDER_ENV: &[&str] = &[
    "STREHL_ALIGN",
    "STREHL_WARPMAP",
    "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO",
    "STREHL_FIX_HALO_DELTA",
];

impl Freeze {
    fn fixture_dir() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("data")
    }

    /// The argv this row freezes, built from the row itself.
    fn argv(&self, stack_dir: &Path, out: &Path) -> Vec<String> {
        let mut v = vec![
            "stack".to_string(),
            stack_dir.display().to_string(),
            "--limit".to_string(),
            self.limit.clone(),
            "--gate".to_string(),
            self.gate.clone(),
        ];
        if self.srgb {
            v.push("--srgb".to_string());
        }
        v.push("--out".to_string());
        v.push(out.display().to_string());
        v
    }

    /// The environment this row freezes, as `(name, value)` pairs applied after
    /// every entry of [`RENDER_ENV`] has been removed.
    fn env(&self) -> Vec<(String, String)> {
        match &self.align {
            Align::Off => vec![("STREHL_ALIGN".to_string(), "0".to_string())],
            Align::Sidecar(f) => vec![(
                "STREHL_WARPMAP".to_string(),
                Self::fixture_dir().join(f).display().to_string(),
            )],
        }
    }

    /// A copy-pasteable reproduction, for the failure message. This is what a
    /// milestone report should paste beside a hash.
    fn command(&self, stack_dir: &Path, out: &Path) -> String {
        let mut s = String::new();
        for name in RENDER_ENV {
            let _ = writeln!(s, "  Remove-Item Env:{name} -ErrorAction SilentlyContinue");
        }
        for (k, v) in self.env() {
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
        let align = match f[5] {
            "off" => Align::Off,
            s if s.starts_with("sidecar:") => Align::Sidecar(s["sidecar:".len()..].to_string()),
            "solve" => panic!(
                "\n{REGISTRY_FILE}:{line}: align = `solve` is not admissible.\n\n\
                 A solving row freezes the aligner's SOLVER as well as the merge, and the \
                 solver was under active rewrite by two milestones on the day these rows \
                 were measured. A freeze that moves every week is a freeze that gets \
                 deleted, which leaves you with nothing.\n\n\
                 Until `fea1a72` there was a harder objection too: `align_cmd::sidecar_path` \
                 resolved to `<stackdir>/warpmap.txt`, so every run of this test would have \
                 written into the READ-ONLY capture library. Thirteen stray sidecars \
                 accumulated there in one night that way (SYNTHESIS facts 1384, 1385), one \
                 of them a 40-frame solve sitting under a 299-frame bracket. That was \
                 repaired at `dccaea8`; a solving row must still set `$STREHL_CACHE_DIR` to \
                 a scratch path, because the shared cache is shared.\n\n\
                 Use `align = sidecar:<fixture>` to freeze an aligned pipeline against a \
                 committed warp map, or `align = off` to freeze the unregistered merge.\n\n\
                 When the solver settles, this restriction should be REVISITED, not \
                 inherited -- a solving row is the only one that would cover the solver.\n"
            ),
            other => panic!(
                "\n{REGISTRY_FILE}:{line}: align = `{other}` is not a mode. \
                 Use `off` or `sidecar:<fixture file under tests/data>`.\n"
            ),
        };
        let srgb = match f[4] {
            "yes" => true,
            "no" => false,
            other => panic!("\n{REGISTRY_FILE}:{line}: srgb = `{other}`; use `yes` or `no`.\n"),
        };
        rows.push(Freeze {
            id: f[0].to_string(),
            stack: f[1].to_string(),
            limit: f[2].to_string(),
            gate: f[3].to_string(),
            srgb,
            align,
            alignment_mode: f[6].to_string(),
            sha256: f[7].to_string(),
            bytes: f[8].parse().unwrap_or_else(|e| {
                panic!(
                    "\n{REGISTRY_FILE}:{line}: bytes = `{}` is not a number ({e}).\n",
                    f[8]
                )
            }),
            workers: f[9].to_string(),
            baselined_at: f[10].to_string(),
            baselined_on: f[11].to_string(),
            why: f[12].to_string(),
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
    println!(
        "\n\
         ------------------------------------------------------------------------------\n\
         SKIPPED: the byte-freeze renders were NOT checked.\n\
         ------------------------------------------------------------------------------\n\
         {reason}\n\n\
         The registry rows themselves WERE still validated by the other tests in this\n\
         file -- their completeness, not their hashes. Set STREHL_FREEZE_REQUIRE=1 to\n\
         make this skip a hard failure on a machine that is supposed to have the data,\n\
         which is what CI should do.\n\
         ------------------------------------------------------------------------------\n"
    );
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

        let expected_mode = match &r.align {
            Align::Off => "off",
            Align::Sidecar(_) => "on-sidecar-override",
        };
        assert_eq!(
            r.alignment_mode, expected_mode,
            "\n{at}: align = `{:?}` must report alignment_mode `{expected_mode}`, \
             not `{}`. These two columns are the SETTING and the OBSERVATION; the \
             test asserts the observation, which is how a silent flip of the \
             alignment default gets caught (that is what M86c did).\n",
            r.align, r.alignment_mode
        );

        if let Align::Sidecar(f) = &r.align {
            let p = Freeze::fixture_dir().join(f);
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
    let key = |r: &Freeze| {
        format!(
            "{}|{}|{}|{}|{:?}",
            r.stack, r.limit, r.gate, r.srgb, r.align
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

    let no_align = |r: &Freeze| format!("{}|{}|{}|{}", r.stack, r.limit, r.gate, r.srgb);
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
        let token = if rest.starts_with("OFF") {
            "off"
        } else if rest.starts_with("ON (solved)") {
            "on-solved"
        } else if rest.starts_with("ON (sidecar-override)") {
            "on-sidecar-override"
        } else {
            continue;
        };
        found = Some(token.to_string());
    }
    found.unwrap_or_else(|| "MISSING (no `alignment : ON/OFF` line in the log)".to_string())
}

/// The `workers ... : N chunks of <= M frames` fingerprint, for the failure
/// message only.
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
        .unwrap_or_else(|| "unknown".to_string())
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

        let scratch =
            std::env::temp_dir().join(format!("strehl-freeze-{}-{}", std::process::id(), r.id));
        let _ = std::fs::remove_dir_all(&scratch);
        std::fs::create_dir_all(&scratch).expect("creating the scratch directory");
        let out = scratch.join("render.tif");

        let before = entry_names(&stack_dir);

        let mut cmd = Command::new(env!("CARGO_BIN_EXE_strehl"));
        cmd.args(r.argv(&stack_dir, &out));
        for name in RENDER_ENV {
            cmd.env_remove(name);
        }
        // Nothing this test runs may cache into the capture library, and the
        // shared user cache is another agent's mutable state. Both are pointed
        // at scratch as a belt-and-braces second line behind the row's own mode.
        cmd.env("STREHL_CACHE_DIR", scratch.join("cache"));
        for (k, v) in r.env() {
            cmd.env(k, v);
        }
        let output = cmd
            .output()
            .unwrap_or_else(|e| panic!("running `{}`: {e}", env!("CARGO_BIN_EXE_strehl")));
        let log = String::from_utf8_lossy(&output.stderr).into_owned();

        let after = entry_names(&stack_dir);
        assert_eq!(
            before,
            after,
            "\n\nHERMETICITY FAILURE for `{}`.\n\
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
            "\n\nThe frozen render for `{}` FAILED TO RUN (exit {:?}).\n\
             This is not a moved hash -- the command did not complete.\n\n\
             Command:\n{}\n\nLog:\n{log}\n",
            r.id,
            output.status.code(),
            r.command(&stack_dir, &out)
        );

        let (got_hash, got_bytes) = hash_file(&out);
        let got_mode = alignment_mode(&log);
        let got_workers = workers_line(&log);

        if got_hash == r.sha256 && got_bytes == r.bytes && got_mode == r.alignment_mode {
            println!(
                "freeze `{}` HOLDS: {} ({} bytes, alignment {}, {})",
                r.id, r.sha256, r.bytes, got_mode, got_workers
            );
            let _ = std::fs::remove_dir_all(&scratch);
            continue;
        }

        // Keep the artifact: the first thing anyone will want is to diff it.
        panic!(
            "{}",
            moved_report(
                r,
                &stack_dir,
                &out,
                &got_hash,
                got_bytes,
                &got_mode,
                &got_workers
            )
        );
    }
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
