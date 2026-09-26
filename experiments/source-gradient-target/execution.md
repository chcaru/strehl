# Execution notes

The first standalone build fails after16.672seconds with E0583: root's lib.rs
used Rust's implicit underscored module filename, while the independently
authored file correctly uses the project's kebab-case name. No test executed.
After the compiler exited, root adds the explicit path attribute and rebuilds.
No fixture, operator, threshold or scientific choice changes.
