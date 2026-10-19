# RAW decoder notice

The Strehl desktop and command-line executables link to **rawler 0.7.2**.
The decoder library and its use are covered by the **GNU Lesser General Public
License, version 2.1**. A verbatim copy is included as `LICENSE-LGPL-2.1`.

The dependency is obtained from its published crates.io package. Its exact
version and SHA-256 checksum are recorded in the accompanying `Cargo.lock`:

`04f4cc35c23969a4a834e0b117c7da41ace812eb9053b5effc3fc5c77d114677`

The Strehl source kit contains the application sources and build instructions
needed to rebuild and relink both executables, including with a modified
decoder. See `REBUILD.md` beside the executables or `docs/desktop-build.md`
inside the source kit. Keep the kit and this notice with distributed binaries.
The application sources remain available under MIT OR Apache-2.0.

Published dependency: <https://crates.io/crates/rawler/0.7.2>

License text: <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt>
