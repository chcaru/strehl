# M186 — M10 definition audit

**PARTIALLY DEFINED — M10 remains definition-blocked; M166 overstates closure.**

## Q1 — citation audit

| Citation | Ruling | Audit |
|---|---|---|
| `M166:23-25` | **MISQUOTED** | It says: “The current M10 card therefore remains **ILL-DEFINED**. **If M160 adopts** the complete specification below, the definition is closed”; the execution phrase is present, but closure is conditional. |
| `M166:112-139` | **VERIFIED** | Claimed file/payload details are present. |
| `M166:181-188`; `:324-350` | **VERIFIED** | Claimed rules are present; see Q2 defects. |
| `M166:243-280`; `:467-497` | **VERIFIED** | Claimed populations/rules are present. |
| `M166:454-465` | **VERIFIED** | Claimed reduction/bar are present. |
| `M166:112-139,628,630,632` as “compute-bound/no camera” | **MISS** | They list missing items but never classify scheduling. |
| `M166:626-631` as wholly capture-bound | **MISQUOTED** | `:629` says, “If it cannot be certified, a fresh planar unit is required,” expressly leaving an existing-capture certification route. |
| `M160:99` | **VERIFIED** | It says `(e)` and “first non-substitutable blocker” in M160's taxonomy. |
| `M166:634` as “tonight” | **MISS** | Actual: “Until all rows are supplied, M10 has neither `PASS` nor `FAIL`.” No tonight/staffing claim occurs there. |
| Scorecard `:815`, `:849`, `:1783-1788`, `:2111` | **VERIFIED** | All four passages exist. |
| Replacement cites `M166:104-634`, `:622-634` | **VERIFIED** | Ranges contain those sections. |

## Q2 — operative-definition test

- **Target-valid — (B).** Candidate-valid fraction; truth-only quotas; all targets denominator; `>=0.99`; any required-population miss fails. But “unsigned 256-bit” gives no SHA-256 byte order (a probe selected x=`03,05,07` big-endian versus `02,00,07` little-endian), and origin divisor `N` is never bound. Independent checkers can differ.
- **Stored encoding — (B).** Three files/cells plus manifest; zero violations; any listed mismatch fails. But no manifest JSON schema, hash algorithm/encoding, or exact contract-failure-to-verdict mapping exists. Independent writers/checkers need not interoperate.
- **Flat-null — (A).** Signed `e_step` nearest-rank `q.975-q.025`; each 1,000-pixel site and pooled 20,000; candidate-valid range/fixed validity denominator; `<=0.5` and validity `>=0.99`; any site/pooled-confidence miss fails.
- **Synthetic confusion/boundary — (B).** The quantities, 20-instance quotas, fixed denominators, `confusion<=0.01`, bias `<=0.5`, and p95 `<=1.0` failures are specified. The renderer/surface algorithm, PRNG-to-seed mapping, scored seed, and affine-certificate acceptance procedure are not; two compliant instruments can give different verdicts.

## Q3 — commit

`832a2e8561352037be5e2a180034e00b09131cf5` exists, is an ancestor of `HEAD`, and adds only the 671-line M166 file (blob `455ed4f4…`). Byte-safe `git cat-file` via Python found: blob 36,616 bytes/671 LF/0 CRLF/SHA-256 `2873276f…`; working copy 37,287 bytes/671 CRLF; CRLF-normalized bytes equal the blob and `git diff 832a2e85 -- <file>` exits 0. Thus the proposal is committed, but it explicitly awaits adoption.

## Q4 — compute/capture split

| Work | My class | M166 match? |
|---|---|---|
| Product planes/writer | compute | yes |
| Manifest schema/producer and integrated checker | definition then compute | omitted/overstated |
| Hidden synthetic renderer/truth/checker controls | definition then compute, no camera | partly |
| Fresh ruler/metrology | capture + metrology | yes |
| Physical per-frame focus map | capture/metrology (adapter code is compute) | partly |
| Local/repeat physical truth sigma/draws | capture for values; compute for machinery | partly |
| Flat truth | external-certification/metrology + compute on existing battery, **or** fresh capture if certification fails | no: not intrinsically capture-bound |

No admitted flat certificate exists; compute completion cannot yield tonight's score.

## Q5 — holdout/burn

Build with synthetic fixtures and spent slide/ruler material; no clean capture is required. The ISO-100 battery is a clean registered holdout. Input-only decoding/site-manifest construction is allowed; rendering a candidate product or reading any output/metric burns its subject/session, so do not use it for development. The register calls old rulers clean, but the current scorecard says **BURNED**; battery is unaffected.

## Q6 — replacement text

M166's proposed `:815` (verbatim):

> | M10 | Physical depth product | **DEFINED; UNMEASURED — MISSING PHYSICAL TRUTH AND PRODUCT.** M166 freezes the product, populations, reductions, seven retained value bars, two boundary vetoes, and M163's five uncertainty vetoes. No score exists until the required truth, product, and integrated checker exist (`docs/research/M166-m10-definition-repair.md:104-634`). |

M166's proposed `:849` (verbatim):

> | M10 | **DEFINED; (e)** | Immediate blocker: compute-bound depth/uncertainty/validity output and integrated checker. Later evidence blockers are fresh ruler truth, focus-axis mapping, flat truth, local/repeat truth uncertainty, and hidden synthetic truth. Until all exist, M10 is `UNMEASURED`, not `FAIL` (`docs/research/M160-amendment6-reachability.md:99`; `docs/research/M166-m10-definition-repair.md:622-634`). |

Paste-ready `:815`:

> | M10 | Physical depth product | **PARTIALLY DEFINED; DEFINITION BLOCKED.** M166 fixes flat/most validity rules, but quota byte order, origin `N`, manifest hashes/schema, and the synthetic instrument remain open. Provisional bars remain: valid `>=99%`; rank `>=0.99`; median error `<=0.5` step; p95 `<=1.0` step; slope error `<=5%`; flat span `<=0.5` step; confusion `<=1%`; boundary bias `<=0.5` and p95 `<=1.0` step; uncertainty coverage `[0.93,0.97]`, at least 9/10 variance ratios in `[0.90,1.10]`, and reported-half-width median `<=0.5`/p95 `<=1.0` step. No M10 verdict exists. |

Paste-ready `:849`:

> | M10 | **PARTIALLY DEFINED; (b)(c)** | Remaining definition blockers are quota/hash ordering, origin divisor, the product-manifest contract, and the hidden synthetic instrument. Product/checker implementation is compute work; fresh ruler/focus/repeat truth is capture/metrology work; existing-battery certification may avoid fresh flat capture. M10 has no verdict. |

Paste-ready `:1783-1788`:

> **Definition status: PARTIALLY DEFINED after M163 and M166.** M163 fixes uncertainty scoring; M166 fixes flat/most validity reductions, but is a proposal pending adoption and leaves quota/hash ordering, origin divisor, manifest hashes/schema, and synthetic renderer/seed/certificate open. The downstream draft remains non-operative; no M10 verdict may be issued until those choices are frozen before candidate output.

Paste-ready `:2111`:

> | M10 | Physical depth accuracy | **DEFINITION BLOCKED after partial M166 repair** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | Manifest/hash and synthetic-instrument choices remain open; product, checker, and physical truth are absent. No M10 verdict exists. |

Divergences: `PARTIALLY DEFINED` follows the implementer-equivalence defects; `(b)(c)` preserves this scorecard's legend (`(e)` means measurable now, unlike M160's taxonomy); all old numbers are retained explicitly; `DEFINITION BLOCKED`, not `UNMEASURED` or `FAIL`, applies until adoption and closure.