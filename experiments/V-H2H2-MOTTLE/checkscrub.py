import subprocess

out = subprocess.run(
    ["git", "show", "HEAD:crates/strehl-cli/tests/byte-freeze.rs"],
    capture_output=True,
    cwd=r"C:\dev\blog\death-of-software\projects\strehl",
)
b = out.stdout.decode("utf-8")
print("rc                       :", out.returncode)
print("STREHL_PYRAMID_SIGNIFICANCE in HEAD:", '"STREHL_PYRAMID_SIGNIFICANCE",' in b)
print("STREHL_SOFT_GATE            in HEAD:", '"STREHL_SOFT_GATE",' in b)
print("--merge estimator hardcoded        :", '"estimator".to_string(),' in b)
