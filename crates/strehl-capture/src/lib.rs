//! Capture orchestration. One camera owner; explicit card or RAM-to-PC storage.
pub mod backend;
pub mod bounds;
pub mod capacity;
pub mod journal;
pub mod lan;
pub mod model;
pub mod ptp;
pub mod receiver;
#[path = "receiver-service.rs"]
pub mod receiver_service;
pub mod remote;
pub mod session;
pub mod timing;
pub mod transfer;
pub mod transport;
pub mod worker;
