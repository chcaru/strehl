import pathlib, sys
p = pathlib.Path(r"C:\dev\strehl-out\M114-ca-verify\wt-tan\crates\strehl-core\src\optics.rs")
src = p.read_text(encoding="utf-8")

def splice(text, anchor, new, where):
    n = text.count(anchor)
    if n != 1:
        sys.exit("ANCHOR NOT UNIQUE (%d occurrences): %r" % (n, anchor))
    return text.replace(anchor, new if where == "replace" else new + anchor, 1)

A1 = "        let s = 1.0 + eps;\n"
TAN = (
    "        if p.key.ends_with(\"-tangential-placebo\") {\n"
    "            // M114 PLACEBO, NEVER COMMITTED. Multiply by the COMPLEX (1 + i*eps)\n"
    "            // instead of the real (1 + eps). The extra displacement relative to\n"
    "            // the uncorrected pull is a_old*i*eps*z rather than a_old*eps*z:\n"
    "            // IDENTICAL magnitude |a||eps||z| at every point, rotated 90 degrees.\n"
    "            // Same gather, same kernel, same resampled sensel count, zero radial\n"
    "            // correction. This is the resampler control the `zero` arm cannot be.\n"
    "            return Similarity {\n"
    "                a: Cx::new(t.a.re - eps * t.a.im, t.a.im + eps * t.a.re),\n"
    "                b: Cx::new(t.b.re - eps * t.b.im + tx, t.b.im + eps * t.b.re + ty),\n"
    "            };\n"
    "        }\n"
)
src = splice(src, A1, TAN, "before")

A2 = "pub const CA_ENV: &str = \"STREHL_FIX_CA\";\n"
CONST = (
    "/// M114 PLACEBO, NEVER COMMITTED. Same eps, rotated 90 degrees.\n"
    "pub const A7C2_TANGENTIAL_PLACEBO: OpticalProfile = OpticalProfile {\n"
    "    key: \"a7c2-fe100gm-2xtc-x4cpl-tangential-placebo\",\n"
    "    translation: (0.0, 0.0),\n"
    "    ..A7C2_FE100GM_2XTC_X4CPL\n"
    "};\n\n"
)
src = splice(src, A2, CONST, "before")

A3 = "    Err(CaConfigError::UnknownProfile { key: raw.to_string() })\n"
BRANCH = (
    "    if raw == A7C2_TANGENTIAL_PLACEBO.key {\n"
    "        return Ok(Some(&A7C2_TANGENTIAL_PLACEBO));\n"
    "    }\n"
)
src = splice(src, A3, BRANCH, "before")

p.write_text(src, encoding="utf-8")
print("patched ok; tangential branch present:", src.count("-tangential-placebo"))
