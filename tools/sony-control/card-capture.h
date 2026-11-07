// SPDX-License-Identifier: MIT OR Apache-2.0
#pragma once
#include <cstdint>
#include <stdexcept>

// Counts camera capture events, not downloaded files. An initially idle card is
// insufficient: all expected events must arrive, then card/bracket stay idle.
struct CardCaptureState {
    uint64_t captured_events;
    bool card_writing;
    bool bracket_active;
    bool card_ok;
    bool unexpected_download;
};

class CardCaptureGate {
    uint64_t expected;
    uint64_t deadline_ms;
    uint64_t quiet_since = 0;
    bool quiet = false;
public:
    CardCaptureGate(uint64_t count, uint64_t timeout_ms) : expected(count), deadline_ms(timeout_ms) {}
    bool ready(const CardCaptureState& state, uint64_t elapsed_ms) {
        if (state.unexpected_download) throw std::runtime_error("Unexpected host download; SD-card-only sequence stopped");
        if (!state.card_ok) throw std::runtime_error("SD card error; sequence stopped");
        if (state.captured_events > expected) throw std::runtime_error("More camera capture events than requested; sequence stopped");
        if (elapsed_ms >= deadline_ms)
            throw std::runtime_error("Capture/card-ready timeout; inspect SD card; shutter will not be retried");
        if (state.captured_events == expected && !state.card_writing && !state.bracket_active) {
            if (!quiet) { quiet = true; quiet_since = elapsed_ms; }
            if (elapsed_ms - quiet_since >= 1000) return true;
        } else quiet = false;
        return false;
    }
};

inline unsigned card_capture_self_test() {
    unsigned assertions = 0;
    const auto require = [&](bool condition) {
        ++assertions;
        if (!condition) throw std::runtime_error("SD-card completion self-test failed");
    };
    CardCaptureGate single(1, 5000);
    require(!single.ready({0, false, false, true, false}, 0));
    require(!single.ready({0, false, false, true, false}, 1500));
    require(!single.ready({1, true, false, true, false}, 1600));
    require(!single.ready({1, false, false, true, false}, 1800));
    require(!single.ready({1, false, false, true, false}, 2799));
    require(single.ready({1, false, false, true, false}, 2800));
    CardCaptureGate burst(9, 10000);
    require(!burst.ready({8, false, false, true, false}, 1000));
    require(!burst.ready({9, false, true, true, false}, 2000));
    require(!burst.ready({9, false, false, true, false}, 3000));
    require(!burst.ready({9, true, false, true, false}, 3900));
    require(!burst.ready({9, false, false, true, false}, 4000));
    require(!burst.ready({9, false, false, true, false}, 4999));
    require(burst.ready({9, false, false, true, false}, 5000));
    const CardCaptureState invalid[] = {
        {0, false, false, true, false}, // no capture event despite idle status
        {2, false, false, true, false}, // extra event
        {1, false, false, false, false}, // card error
        {1, false, false, true, true}, // any unexpected host image
        {1, true, false, true, false}, // never finishes card write
        {1, false, true, true, false} // never finishes bracket
    };
    for (const auto& state : invalid) {
        CardCaptureGate gate(1, 5000);
        bool rejected = false;
        try { gate.ready(state, 5000); } catch (const std::runtime_error&) { rejected = true; }
        require(rejected);
    }
    return assertions;
}
