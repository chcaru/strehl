use super::*;
#[path = "override-fixture.rs"]
mod override_fixture;

#[test]
fn explicit_override_consumer_contract() {
    override_fixture::run(
        "merge_cmd::measured_component_override_tests::explicit_override_consumer_contract",
        "candidate",
    );
}
