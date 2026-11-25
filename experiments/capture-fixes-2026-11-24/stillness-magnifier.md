# The stillness check and the camera magnifier

2026-11-25. The owner reported that the stillness check (plan Q7) "stopped working all of a
sudden" with "Setting 0xd254 did not read back".

## Cause

0xd254 is the camera's focus magnifier: `ratio << 32 | x << 16 | y`, the centre in a 639 x 479
frame. The check asks for the camera's largest ratio centred on the subject box. The Pi bridge
then waited up to 3 s for the camera to read back exactly that value, and failed otherwise. A
failure in the magnifier action leaves the Pi in Fault, so the check went on failing until
Recover.

The camera does not take every centre. Probed on the rig at 11:51 by running the bridge
directly on the Pi (camera connected through the API, then disconnected, then the bridge's own
`magnify` and `status` commands; settings restored by its `quit`). MEASURED:

| Asked (ratio, x, y) | Reply | The camera reads |
| --- | --- | --- |
| 93, 320, 240 | ok | 93, 320, 240 |
| 93, 478, 53 (the owner's box centre) | did not read back | 93, 478, 59 |
| 93, 40, 240 | did not read back | 93, 73, 240 |
| 93, 320, 30 | did not read back | 93, 320, 59 |
| 93, 620, 460 | did not read back | 93, 567, 421 |
| 93, 300, 220 | ok | 93, 300, 220 |
| 0, 478, 53 (putting it back) | did not read back | 0, 478, 59 |
| 0, 320, 240 | ok | 0, 320, 240 |

The ratios on offer were 0, 10, 47 and 93 (tenths). At 9.3x the camera holds the centre
within x 73 to 567 and y 59 to 421 and moves a centre outside that range to the nearest edge.
It does the same with the magnifier off. The owner's subject box was at the top of the frame
(x 0.669 to 0.828, y 0.007 to 0.215, centre 478, 53), so the check failed both when it set the
magnifier and when it put it back. The check passed its rig test on 2026-11-24 because that
test used the frame's centre (320, 240). "All of a sudden" fits the subject box moving to the
frame's edge.

## Change

The bridge now takes the magnifier once its ratio reads back: the centre is the camera's
choice, and the check measures the sway wherever the view sits. Every other setting must
still read back exactly. A setting that does not read back now gives both values ("asked for
..., the camera reads ...").

The test `the_magnifier_is_taken_at_its_ratio_wherever_the_camera_keeps_the_centre`
(`crates/strehl-capture/src/ptp.rs`) uses the readbacks above. It tests the comparison
`took`, which `Camera::set` calls. The USB exchange itself is checked only on the rig.

## Rig checks after the change

The Pi was deployed with receipt `../capture-implementation-2026-11-20/install-1795636643.json`
(controller sha 608bca40..., unchanged; bridge a28a2932...; backup
`/root/strehl-before-round4-1795636643`). MEASURED on 2026-11-25:

- The bridge driven directly, each request from the magnifier off at (320, 240), then read at
  once and 2 s later: 9.3x at the owner's box (478, 53), at the far corner (620, 460), 4.7x and
  1.0x at the box, and 9.3x at (478, 59) were all taken in 0.12 to 0.19 s, the centre kept
  inside the range as before. From 9.3x at the centre to 9.3x at the box, the reply came in
  0.03 s, before the camera moved the centre (it read the new centre 2 s later). That is
  harmless: the check waits for live frames.
- Through the Pi API, the desktop's requests (9.3x and off at (478, 53), (620, 460) and
  (40, 240)), three rounds each: 18 of 18 ready in 0.2 to 0.5 s without live view; 18 of 18
  ready in 0.2 to 0.4 s with live view streaming (328 previews fetched meanwhile).
- One request failed: through the API about 10 s after connecting, 9.3x at (620, 460) from
  the magnifier off. The camera moved the centre to (567, 421) but stayed off for the 3 s
  ("asked for 0x5d026c01cc, the camera reads 0x23701a5"). Not repeated in the 36 requests
  above; not explained. As before, a failed magnifier request leaves the Pi in Fault until
  Recover.

The Pi resets the subject box to its default (0.1 to 0.9) on every connect and disconnect, so
the probes' reconnections reset the owner's box, as a camera power cycle does. Camera and light
were off and "manage power" on at the end.
