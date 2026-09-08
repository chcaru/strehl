# Prior work carried into the first native attempt

Root carries the actual dependency capture into the original real-stage
1200 CPU / 1800 wall / 4 GiB new files / 128 MiB metadata allowance. No native
attempt, RAW hash/decode, registration call or real render has occurred yet.

Capture was executed from committed `3bc87c03` using the actual released
argument vector in `runtime-capture-release-1.json`, SHA256
`7a2436afe602b2d53fdf95600e6285c26ca390a429cb5c6255b1be8206502a30`.
Root observed operating-system exit 0. The terminal result is 58,261 bytes,
SHA256 `0cb18db67c7a87674999f0714e964ff19883b43fbd88f7a2436b44d5c41e43fa`.

**MEASURED operational accounting:** the actual final stdout records 1.65625
CPU seconds including the terminal child Job's 0.4375 once. Root's independent
outer stopwatch records 1.7583753 wall seconds, including parent final output;
this larger outer value is carried instead of the internal 1.703 sample.
These are not performance measurements or calibration evidence.

**PROSPECTIVE CONSERVATIVE CHARGE:** one MiB is charged to both file and
metadata bytes for this capture's new metadata, release, preparation and
review evidence. The capture made no image or source-copy artifact. Before
native release preparation, enumerate the capture output with hidden files,
add its runtime JSON, outer console/exit/observation, capture release, capture
source/spec/reviews/preparers and this carry record, and require their total
extent to be below this charge. This reserve is not measured write I/O and is
never refunded. It covers the completed capture metadata, not later native
or coverage artifacts, which retain their own cumulative accounting.

`native-prior-work-1.json` contains exactly these four values. The native
preparer requires nonzero carried work, the actual capture independent read
and root's actual outer records before writing a release. This record does
not turn private commissioning into a real-stage measurement or reset any
earlier real-stage work.
