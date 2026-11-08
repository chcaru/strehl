//! Capture orchestration. Camera commands have one owner; RAWs stay on the card.
pub mod backend;
pub mod bounds;
pub mod journal;
pub mod model;
pub mod timing;
pub mod worker;
