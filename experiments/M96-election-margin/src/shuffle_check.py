"""What permutations do M96's two shuffle streams actually produce?

Replicates the instrument's SplitMix64 + Fisher-Yates exactly, in Python, from
the seeds the binary uses, and asks whether the two arms of the paired null are
really two independent uniform permutations. Re-derived from the Rust source
rather than assumed.
"""

M = (1 << 64) - 1
SEED = 0x5EED_0001
PERMUTE_XOR = 0x1234_5678_9ABC_DEF0
PLACEBO_XOR = 0xA5A5_A5A5


class Rng:
    def __init__(self, seed: int) -> None:
        self.s = seed & M

    def next_u64(self) -> int:
        self.s = (self.s + 0x9E37_79B9_7F4A_7C15) & M
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58_476D_1CE4_E5B9) & M
        z = ((z ^ (z >> 27)) * 0x94D0_49BB_1331_11EB) & M
        return z ^ (z >> 31)

    def below(self, n: int) -> int:
        return self.next_u64() % n


def shuffle(order: list[int], seed: int) -> list[int]:
    v = list(order)
    r = Rng(seed)
    for i in range(len(v) - 1, 0, -1):
        j = r.below(i + 1)
        v[i], v[j] = v[j], v[i]
    return v


def fixed_points(p: list[int]) -> int:
    return sum(1 for i, x in enumerate(p) if i == x)


def displacement(p: list[int]) -> float:
    return sum(abs(i - x) for i, x in enumerate(p)) / len(p)


for n in (22, 33, 79, 100, 299):
    ident = list(range(n))
    a = shuffle(ident, SEED ^ PERMUTE_XOR)
    b = shuffle(a, SEED ^ PLACEBO_XOR)
    exp_disp = (n * n - 1) / (3.0 * n)
    print(f"N={n:4}  armA fixed {fixed_points(a):3}  meandisp {displacement(a):8.3f}"
          f"   armB fixed {fixed_points(b):3}  meandisp {displacement(b):8.3f}"
          f"   | uniform expectation: fixed 1.0, meandisp {exp_disp:8.3f}")

# The statistic that actually matters for rho: how far is each arm's ordering
# from the identity as a *set placement* problem? Sample many seeds to get the
# reference spread, so a single pair can be judged.
print()
print("reference spread of mean displacement over 4000 uniform shuffles (n=22):")
import random

random.seed(7)
ds = []
for _ in range(4000):
    p = list(range(22))
    random.shuffle(p)
    ds.append(displacement(p))
ds.sort()
print(f"  p01 {ds[40]:.3f}  p50 {ds[2000]:.3f}  p99 {ds[3960]:.3f}")
