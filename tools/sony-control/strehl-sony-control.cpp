// SPDX-License-Identifier: MIT OR Apache-2.0
// Original SDK client. Sony's headers and runtime are external dependencies.
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/vfs.h>
#include <unistd.h>
#endif
#include <filesystem>
#include <cstdlib>
#include <cctype>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <map>
#include <mutex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include "CameraRemote_SDK.h"
#include "IDeviceCallback.h"
#include "card-capture.h"

namespace sdk = SCRSDK;
using Clock = std::chrono::steady_clock;
using namespace std::chrono_literals;

#ifdef _WIN32
static std::string utf8(const wchar_t* value) {
    if (!value) return {};
    const int n = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
    if (!n) throw std::runtime_error("UTF-8 conversion failed");
    std::string result(static_cast<size_t>(n), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value, -1, result.data(), n, nullptr, nullptr);
    result.pop_back();
    return result;
}
#else
static std::string utf8(const char* value) { return value ? value : ""; }
#endif
static std::string quote(const std::string& value) {
    const char hex[] = "0123456789abcdef";
    std::string result = "\"";
    for (unsigned char c : value) {
        if (c == '\\' || c == '"') { result += '\\'; result += static_cast<char>(c); }
        else if (c < 32) { result += "\\u00"; result += hex[c >> 4]; result += hex[c & 15]; }
        else result += static_cast<char>(c);
    }
    return result + '"';
}
static void check(sdk::CrError error, const char* operation) {
    if (error) {
        std::ostringstream message;
        message << operation << " failed: SDK 0x" << std::hex << error;
        throw std::runtime_error(message.str());
    }
}
static void emit(const std::string& fields) {
    std::cout << "{\"ok\":true," << fields << "}" << std::endl;
}
static void emit_error(const std::exception& error) {
    std::cout << "{\"ok\":false,\"error\":" << quote(error.what()) << "}" << std::endl;
}
static uint64_t number(const std::string& input) {
    if (input.empty() || input.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("Expected an unsigned decimal integer");
    return std::stoull(input);
}
static std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> result;
    std::istringstream stream(line);
    std::string field;
    while (std::getline(stream, field, '\t')) result.push_back(field);
    return result;
}
// Live-view JPEGs travel only through the private pipe, never a file/download API.
static std::string base64(const unsigned char* data, size_t size) {
    static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve((size + 2) / 3 * 4);
    for (size_t i = 0; i < size; i += 3) {
        const uint32_t word = (uint32_t(data[i]) << 16) |
            (i + 1 < size ? uint32_t(data[i + 1]) << 8 : 0) |
            (i + 2 < size ? uint32_t(data[i + 2]) : 0);
        out += alphabet[(word >> 18) & 63]; out += alphabet[(word >> 12) & 63];
        out += i + 1 < size ? alphabet[(word >> 6) & 63] : '=';
        out += i + 2 < size ? alphabet[word & 63] : '=';
    }
    return out;
}

// The SDK returns the JPEG body separately from the receive allocation. It can
// follow a transport header; neither pointer equality nor offset zero is required.
static std::string preview_jpeg(const unsigned char* buffer, size_t capacity,
                                const unsigned char* image, size_t bytes) {
    const auto begin = reinterpret_cast<uintptr_t>(buffer);
    const auto address = reinterpret_cast<uintptr_t>(image);
    const bool in_buffer = buffer && image && address >= begin && address - begin <= capacity;
    const auto offset = in_buffer ? static_cast<size_t>(address - begin) : capacity;
    if (!in_buffer || bytes < 4 || bytes > capacity - offset)
        throw std::runtime_error("Invalid live-view payload range (buffer " + std::to_string(capacity) +
            ", offset " + (in_buffer ? std::to_string(offset) : "outside") +
            ", image bytes " + std::to_string(bytes) + ")");
    if (image[0] != 0xff || image[1] != 0xd8)
        throw std::runtime_error("Live-view payload is not JPEG (offset " + std::to_string(offset) +
            ", image bytes " + std::to_string(bytes) + ")");
    return base64(image, bytes);
}

static unsigned preview_self_test() {
    // A deliberate non-JPEG header reproduces the original incorrect-base test.
    std::vector<unsigned char> storage(2048, 0);
    const unsigned char jpeg[] = {0xff, 0xd8, 0xff, 0xd9};
    std::copy(std::begin(jpeg), std::end(jpeg), storage.begin() + 128);
    if (preview_jpeg(storage.data(), storage.size(), storage.data() + 128, 4) != "/9j/2Q==")
        throw std::runtime_error("Offset JPEG regression failed");
    if (preview_jpeg(jpeg, sizeof(jpeg), jpeg, sizeof(jpeg)) != "/9j/2Q==")
        throw std::runtime_error("Zero-offset JPEG regression failed");
    unsigned rejected = 0;
    const auto refuse = [&](const unsigned char* image, size_t bytes) {
        try { preview_jpeg(storage.data(), storage.size(), image, bytes); }
        catch (const std::runtime_error&) { ++rejected; return; }
        throw std::runtime_error("Invalid preview range was accepted");
    };
    refuse(nullptr, 4);
    refuse(storage.data() + 128, 0);
    refuse(storage.data() + 128, 3);
    refuse(storage.data() + 128, storage.size());
    refuse(storage.data() + storage.size(), 4);
    refuse(storage.data(), 4);
    if (rejected != 6) throw std::runtime_error("Preview rejection controls failed");
    return rejected + 2;
}

static const std::map<std::string, CrInt32u> properties = {
#define PROP(name) {#name, sdk::CrDeviceProperty_##name}
    PROP(FocusMode), PROP(FocusModeSetting), PROP(FocusPositionSetting),
    PROP(FocusPositionCurrentValue), PROP(DriveMode), PROP(FileType),
    PROP(StillImageStoreDestination), PROP(RemoteSaveImageSize),
    PROP(RAW_FileCompressionType), PROP(FocusBracketShotNumber),
    PROP(FocusBracketFocusRange), PROP(FocusBracketOrder),
    PROP(FocusBracketShootingStatus), PROP(MediaSLOT1_WritingState),
    PROP(MediaSLOT1_Status), PROP(MediaSLOT1_RemainingNumber),
    PROP(FNumber), PROP(ShutterSpeed), PROP(IsoSensitivity),
    PROP(ExposureProgramMode), PROP(BatteryRemain), PROP(PreAF),
    PROP(LensModelName), PROP(LensVersionNumber), PROP(USBPowerSupply),
    PROP(LiveViewStatus), PROP(LiveView_Image_Quality), PROP(Focus_Magnifier_Setting)
#undef PROP
};
static const std::set<std::string> writable = {
    "FocusMode", "DriveMode", "FileType", "StillImageStoreDestination",
    "FocusBracketShotNumber", "FocusBracketFocusRange",
    "FocusBracketOrder", "LiveView_Image_Quality", "RAW_FileCompressionType", "RemoteSaveImageSize"
};

struct Events : sdk::IDeviceCallback {
    std::atomic<bool> connected{false};
    std::atomic<CrInt32u> error{0};
    std::atomic<CrInt32u> focus_result{0};
    std::mutex mutex;
    std::atomic<uint64_t> captured_events{0};
    std::atomic<uint64_t> unexpected_downloads{0};
    bool host_mode = false;
    std::vector<std::string> downloads;
    std::vector<CrInt32u> warnings;
    void OnConnected(sdk::DeviceConnectionVersioin) override { connected = true; }
    void OnDisconnected(CrInt32u e) override { connected = false; if (e) error = e; }
    void OnError(CrInt32u e) override { error = e; }
    void OnCompleteDownload(CrChar* filename, CrInt32u) override {
        if (!host_mode) { ++unexpected_downloads; return; }
        std::lock_guard<std::mutex> lock(mutex);
        downloads.push_back(utf8(filename));
    }
    void OnWarning(CrInt32u code) override {
        if (code == sdk::CrNotify_Captured_Event) ++captured_events;
        if (code == sdk::CrWarning_FocusPosition_Result_OK ||
            code == sdk::CrWarning_FocusPosition_Result_NG ||
            code == sdk::CrWarning_FocusPosition_Result_Invalid) focus_result = code;
        std::lock_guard<std::mutex> lock(mutex);
        warnings.push_back(code);
    }
};

// Copy numeric allowed values while the SDK property owns its buffers.
static std::vector<uint64_t> values(const sdk::CrDeviceProperty& p) {
    const auto kind = static_cast<unsigned>(p.GetValueType()) & 0xFFF;
    if (kind < 1 || kind > 4) return {};
    const size_t width = size_t{1} << (kind - 1);
    const auto size = p.GetSetValueSize() ? p.GetSetValueSize() : p.GetValueSize();
    const auto data = p.GetSetValueSize() ? p.GetSetValues() : p.GetValues();
    std::vector<uint64_t> result;
    if (!data || size % width) return result;
    for (size_t i = 0; i < size; i += width) {
        uint64_t value = 0;
        std::memcpy(&value, data + i, width);
        result.push_back(value);
    }
    return result;
}
static void validate_value(const sdk::CrDeviceProperty& p, uint64_t value) {
    const auto allowed = values(p);
    const auto type = static_cast<unsigned>(p.GetValueType());
    if (!p.IsSetEnableCurrentValue()) throw std::runtime_error("Property is not writable in the current camera state");
    if (p.GetCode() == sdk::CrDeviceProperty_Focus_Magnifier_Setting) {
        if (std::none_of(allowed.begin(), allowed.end(), [value](uint64_t item) { return (item >> 32) == (value >> 32); }))
            throw std::runtime_error("Camera does not advertise this focus magnification");
        return;
    }
    if ((type & sdk::CrDataType_RangeBit) && allowed.size() == 3) {
        if (value < allowed[0] || value > allowed[1] ||
            (allowed[2] && (value - allowed[0]) % allowed[2]))
            throw std::runtime_error("Value is outside the camera's advertised range");
    } else if ((type & sdk::CrDataType_ArrayBit) && !allowed.empty() &&
               std::find(allowed.begin(), allowed.end(), value) == allowed.end()) {
        throw std::runtime_error("Value is not in the camera's advertised choices");
    }
}

class Camera {
    sdk::CrDeviceHandle handle = 0;
    Events events;
    struct Saved { CrInt32u code; sdk::CrDataType type; uint64_t value; std::string name; };
    std::vector<Saved> saved;
    bool focus_saved = false;
    uint64_t initial_focus = 0;
    bool uncertain = false;
    std::filesystem::path raw_directory;
    void alive() {
        check(events.error.load(), "Camera callback");
        if (!events.connected) throw std::runtime_error("Camera disconnected");
    }
    sdk::CrDeviceProperty get(CrInt32u code) {
        alive();
        sdk::CrDeviceProperty* raw = nullptr;
        CrInt32 count = 0;
        check(sdk::GetSelectDeviceProperties(handle, 1, &code, &raw, &count), "GetSelectDeviceProperties");
        if (!raw || count != 1) {
            if (raw) sdk::ReleaseDeviceProperties(handle, raw);
            throw std::runtime_error("Camera does not expose this property");
        }
        sdk::CrDeviceProperty copy = raw[0];
        sdk::ReleaseDeviceProperties(handle, raw);
        return copy;
    }
    uint64_t current(CrInt32u code) {
        auto p = get(code);
        if (!p.IsGetEnableCurrentValue()) throw std::runtime_error("Property is not currently readable");
        return p.GetCurrentValue();
    }
    void set_checked(CrInt32u code, uint64_t value) {
        auto p = get(code);
        if (p.IsGetEnableCurrentValue() && p.GetCurrentValue() == value) return;
        validate_value(p, value);
        p.SetCurrentValue(value);
        check(sdk::SetDeviceProperty(handle, &p), "SetDeviceProperty");
        auto end = Clock::now() + 5s;
        do {
            std::this_thread::sleep_for(100ms);
            const auto readback = current(code);
            if (readback == value) return;
            if (code == sdk::CrDeviceProperty_Focus_Magnifier_Setting &&
                (readback >> 32) == (value >> 32) &&
                ((value >> 32) == 0 || (value & 0xffffffffULL) == 0xffffffffULL)) return;
        } while (Clock::now() < end);
        throw std::runtime_error("Property write did not read back within 5 seconds");
    }
public:
    explicit Camera(sdk::ICrCameraObjectInfo* info) {
        check(sdk::Connect(info, &events, &handle, sdk::CrSdkControlMode_Remote,
                           sdk::CrReconnecting_OFF), "Connect");
        auto end = Clock::now() + 15s;
        while (!events.connected && !events.error && Clock::now() < end)
            std::this_thread::sleep_for(50ms);
        if (!events.connected) {
            if (handle) { sdk::Disconnect(handle); sdk::ReleaseDevice(handle); handle = 0; }
            check(events.error.load(), "Connect callback");
            throw std::runtime_error("Connection timeout; check USB Remote Shoot and Sony USB driver");
        }
    }
    void host_memory(const std::string& path) {
#ifdef _WIN32
        (void)path;
        throw std::runtime_error("RAM-only host capture requires the Linux Pi service");
#else
        raw_directory = std::filesystem::canonical(path);
        struct statfs info{};
        if (statfs(raw_directory.c_str(), &info) != 0 || info.f_type != 0x01021994)
            throw std::runtime_error("Host RAW directory must be on tmpfs; refusing disk-backed RAW storage");
        if (!std::filesystem::is_empty(raw_directory))
            throw std::runtime_error("Unsent RAW data is still in RAM; recover it before reconnecting");
        auto native = raw_directory.native();
        std::string prefix = "STREHL";
        check(sdk::SetSaveInfo(handle, native.data(), prefix.data(), 1), "SetSaveInfo RAM destination");
        events.host_mode = true;
#endif
    }
    ~Camera() {
        if (handle) {
            try { restore(); } catch (...) {}
            sdk::Disconnect(handle);
            auto end = Clock::now() + 3s;
            while (events.connected && Clock::now() < end) std::this_thread::sleep_for(50ms);
            sdk::ReleaseDevice(handle);
        }
    }
    void disable_live_view() {
        check(sdk::SetDeviceSetting(handle, sdk::Setting_Key_EnableLiveView,
                                   sdk::CrDeviceSetting_Disable), "Disable SDK live view");
    }
    void live_view(bool enabled) {
        alive();
        check(sdk::SetDeviceSetting(handle, sdk::Setting_Key_EnableLiveView,
            enabled ? sdk::CrDeviceSetting_Enable : sdk::CrDeviceSetting_Disable), "Set live view");
    }
    std::string preview() {
        alive();
        sdk::CrImageInfo info;
        check(sdk::GetLiveViewImageInfo(handle, &info), "GetLiveViewImageInfo");
        const auto size = info.GetBufferSize();
        if (!size || size > 16 * 1024 * 1024) throw std::runtime_error("Live view unavailable or exceeds 16 MiB");
        std::vector<unsigned char> buffer(size);
        sdk::CrImageDataBlock block;
        block.SetData(buffer.data()); block.SetSize(size);
        check(sdk::GetLiveViewImage(handle, &block), "GetLiveViewImage");
        const auto bytes = block.GetImageSize();
        const auto jpeg = preview_jpeg(buffer.data(), buffer.size(), block.GetImageData(), bytes);
        return "\"frame\":" + std::to_string(block.GetFrameNo()) +
            ",\"width\":" + std::to_string(info.GetWidth()) +
            ",\"height\":" + std::to_string(info.GetHeight()) +
            ",\"jpeg\":" + quote(jpeg);
    }
    void magnify(uint64_t ratio_tenths, uint64_t x, uint64_t y) {
        if (uncertain) throw std::runtime_error("Previous camera operation uncertain");
        if (ratio_tenths > 1000 || x > 639 || y > 479) throw std::runtime_error("Invalid magnifier position or ratio");
        const auto code = sdk::CrDeviceProperty_Focus_Magnifier_Setting;
        auto p = get(code);
        if (!p.IsGetEnableCurrentValue()) throw std::runtime_error("Cannot snapshot focus magnifier");
        if (std::none_of(saved.begin(), saved.end(), [code](const Saved& s) { return s.code == code; }))
            saved.push_back({code, p.GetValueType(), p.GetCurrentValue(), "Focus_Magnifier_Setting"});
        // Sony requires a ratio-only update before placing the newly sized box.
        set_checked(code, (ratio_tenths << 32) | 0xffffffffULL);
        if (!ratio_tenths) return;
        std::this_thread::sleep_for(200ms);
        CrInt32u live_code = sdk::CrLiveViewProperty_Focus_Magnifier_Position;
        sdk::CrLiveViewProperty* raw = nullptr;
        CrInt32 count = 0;
        check(sdk::GetSelectLiveViewProperties(handle, 1, &live_code, &raw, &count), "Get magnifier frame bounds");
        // CrMagPosInfo consists of six UINT32 fields in this documented order.
        CrInt32u frame[6]{};
        const bool valid = raw && count == 1 && raw[0].IsGetEnableCurrentValue() &&
            raw[0].GetFrameInfoType() == sdk::CrFrameInfoType_Magnifier_Position &&
            raw[0].GetValue() && raw[0].GetValueSize() >= sizeof(frame);
        if (valid) std::memcpy(frame, raw[0].GetValue(), sizeof(frame));
        if (raw) sdk::ReleaseLiveViewProperties(handle, raw);
        if (!valid || !frame[1] || !frame[3] || frame[1] > 65535 || frame[3] > 65535 ||
            frame[4] > frame[1] || frame[5] > frame[3])
            throw std::runtime_error("Camera magnification enabled, but its frame bounds are unavailable; use the camera to position it");
        const uint64_t px = std::clamp(x * frame[1] / 639, uint64_t(frame[4] / 2), uint64_t(frame[1] - (frame[4] + 1) / 2));
        const uint64_t py = std::clamp(y * frame[3] / 479, uint64_t(frame[5] / 2), uint64_t(frame[3] - (frame[5] + 1) / 2));
        set_checked(code, (ratio_tenths << 32) | (px << 16) | py);
    }
    std::string property(const std::string& name) {
        auto p = get(properties.at(name));
        std::ostringstream out;
        out << "{\"code\":" << p.GetCode() << ",\"type\":" << p.GetValueType()
            << ",\"readable\":" << (p.IsGetEnableCurrentValue() ? "true" : "false")
            << ",\"writable\":" << (p.IsSetEnableCurrentValue() ? "true" : "false")
            << ",\"value\":";
        if (!p.IsGetEnableCurrentValue()) out << "null";
        else if (p.GetValueType() == sdk::CrDataType_STR)
            out << quote(utf8(reinterpret_cast<const CrChar*>(p.GetCurrentStr())));
        else out << p.GetCurrentValue();
        out << ",\"allowed\":[";
        auto allowed = values(p);
        for (size_t i = 0; i < allowed.size(); ++i) { if (i) out << ','; out << allowed[i]; }
        out << "]}";
        return out.str();
    }
    std::string status() {
        std::string result = "\"properties\":{";
        bool first = true;
        for (const auto& entry : properties) {
            if (!first) result += ',';
            first = false;
            result += quote(entry.first) + ':';
            try { result += property(entry.first); }
            catch (const std::exception& e) { result += "{\"error\":" + quote(e.what()) + '}'; }
        }
        return result + '}';
    }
    void set(const std::string& name, uint64_t value) {
        if (uncertain) throw std::runtime_error("Previous operation uncertain; close and inspect the camera");
        if (!writable.count(name)) throw std::runtime_error("Property is not in this helper's write allowlist");
        if (name == "StillImageStoreDestination" && value != (events.host_mode ?
            sdk::CrStillImageStoreDestination_HostPC : sdk::CrStillImageStoreDestination_MemoryCard))
            throw std::runtime_error("Storage destination does not match the selected capture backend");
        const auto code = properties.at(name);
        auto p = get(code);
        if (!p.IsGetEnableCurrentValue()) throw std::runtime_error("Cannot snapshot original setting");
        // The owner's card-only preference persists; never restore a host destination.
        if (name != "StillImageStoreDestination" &&
            std::none_of(saved.begin(), saved.end(), [code](const Saved& s) { return s.code == code; }))
            saved.push_back({code, p.GetValueType(), p.GetCurrentValue(), name});
        set_checked(code, value);
    }
    std::string focus(uint64_t value, uint64_t settle_ms, bool restoring = false) {
        if (uncertain && !restoring) throw std::runtime_error("Previous operation uncertain; close and inspect the camera");
        if (value > 65535 || settle_ms < 100 || settle_ms > 30000)
            throw std::runtime_error("Focus must be 0..65535; settle must be 100..30000 ms");
        if (current(sdk::CrDeviceProperty_FocusMode) != sdk::CrFocus_MF)
            throw std::runtime_error("Focus commands require MF mode");
        const auto before = current(sdk::CrDeviceProperty_FocusPositionCurrentValue);
        if (!focus_saved && !restoring) {
            initial_focus = before;
            focus_saved = true;
            // Restore also temporarily needs Single drive, including direct protocol use.
            const auto drive_code = sdk::CrDeviceProperty_DriveMode;
            if (std::none_of(saved.begin(), saved.end(), [drive_code](const Saved& s) { return s.code == drive_code; })) {
                auto drive = get(drive_code);
                saved.push_back({drive_code, drive.GetValueType(), current(drive_code), "DriveMode"});
            }
        }
        auto p = get(sdk::CrDeviceProperty_FocusPositionSetting);
        validate_value(p, value);
        events.focus_result = 0;
        p.SetCurrentValue(value);
        uncertain = true;
        check(sdk::SetDeviceProperty(handle, &p), "FocusPositionSetting");
        auto end = Clock::now() + 10s;
        while (!events.focus_result && Clock::now() < end) { alive(); std::this_thread::sleep_for(25ms); }
        const auto code = events.focus_result.load();
        const bool noop = !code && before == value && current(sdk::CrDeviceProperty_FocusPositionCurrentValue) == value;
        if (code != sdk::CrWarning_FocusPosition_Result_OK && !noop) {
            uncertain = true;
            throw std::runtime_error("Focus completion failed or timed out; no exposure taken");
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(settle_ms));
        const auto after = current(sdk::CrDeviceProperty_FocusPositionCurrentValue);
        uncertain = false;
        return "\"requested\":" + std::to_string(value) + ",\"before\":" + std::to_string(before) +
            ",\"readback\":" + std::to_string(after) + ",\"completion\":" +
            quote(noop ? "unchanged-readback-no-event" : "sony-focus-complete") +
            ",\"settle_ms\":" + std::to_string(settle_ms);
    }
    std::string capture(uint64_t count, uint64_t timeout_s) {
        if (uncertain) throw std::runtime_error("Previous operation uncertain; close and inspect the camera");
        if (count < 1 || count > 299 || timeout_s < 5 || timeout_s > 3600)
            throw std::runtime_error("Invalid capture count or timeout");
        if (current(sdk::CrDeviceProperty_StillImageStoreDestination) != sdk::CrStillImageStoreDestination_MemoryCard)
            throw std::runtime_error("Capture requires SD-card-only saving; no exposure taken");
        const auto drive = current(sdk::CrDeviceProperty_DriveMode);
        if ((count == 1 && drive != sdk::CrDrive_Single) ||
            (count > 1 && (drive != sdk::CrDrive_FocusBracket ||
             current(sdk::CrDeviceProperty_FocusBracketShotNumber) != count)))
            throw std::runtime_error("Drive mode / native bracket count does not match requested capture");
        if (current(sdk::CrDeviceProperty_FocusMode) != sdk::CrFocus_MF ||
            current(sdk::CrDeviceProperty_FileType) != sdk::CrFileType_Raw)
            throw std::runtime_error("Capture requires MF and RAW-only file type");
        if (current(sdk::CrDeviceProperty_MediaSLOT1_Status) != sdk::CrSlotStatus_OK ||
            current(sdk::CrDeviceProperty_MediaSLOT1_WritingState) != sdk::CrMediaSlotWritingState_NotWriting)
            throw std::runtime_error("SD card is missing, unavailable or busy; no exposure taken");
        if (current(sdk::CrDeviceProperty_FocusBracketShootingStatus) != sdk::CrFocusBracket_NotShooting)
            throw std::runtime_error("Focus bracket is already active; no exposure taken");
        const auto remaining_before = current(sdk::CrDeviceProperty_MediaSLOT1_RemainingNumber);
        if (remaining_before < count) throw std::runtime_error("SD card reports insufficient remaining capacity");
        if (events.unexpected_downloads) throw std::runtime_error("Unexpected host download; sequence stopped");
        const auto baseline = events.captured_events.load();
        // Set uncertainty before issuing S2. Never retry a shutter after timeout.
        uncertain = true;
        const auto started = Clock::now();
        const auto down = sdk::SendCommand(handle, sdk::CrCommandId_Release, sdk::CrCommandParam_Down);
        std::this_thread::sleep_for(50ms);
        const auto up = sdk::SendCommand(handle, sdk::CrCommandId_Release, sdk::CrCommandParam_Up);
        check(down, "Release down");
        check(up, "Release up");
        CardCaptureGate gate(count, timeout_s * 1000);
        for (;;) {
            alive();
            const auto card_status = current(sdk::CrDeviceProperty_MediaSLOT1_Status);
            const auto writing = current(sdk::CrDeviceProperty_MediaSLOT1_WritingState);
            if (writing != sdk::CrMediaSlotWritingState_NotWriting && writing != sdk::CrMediaSlotWritingState_ContentsWriting)
                throw std::runtime_error("Unknown SD card writing state; sequence stopped");
            const auto bracket = current(sdk::CrDeviceProperty_FocusBracketShootingStatus);
            if (bracket != sdk::CrFocusBracket_NotShooting && bracket != sdk::CrFocusBracket_Shooting)
                throw std::runtime_error("Unknown focus bracket state; sequence stopped");
            const auto elapsed = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - started).count());
            const CardCaptureState state{events.captured_events.load() - baseline,
                writing == sdk::CrMediaSlotWritingState_ContentsWriting,
                bracket == sdk::CrFocusBracket_Shooting, card_status == sdk::CrSlotStatus_OK,
                events.unexpected_downloads.load() != 0};
            if (gate.ready(state, elapsed)) {
                if (current(sdk::CrDeviceProperty_StillImageStoreDestination) != sdk::CrStillImageStoreDestination_MemoryCard)
                    throw std::runtime_error("Storage destination changed during capture; sequence stopped");
                const auto remaining_after = current(sdk::CrDeviceProperty_MediaSLOT1_RemainingNumber);
                uncertain = false;
                // Camera events/status are not a readback or checksum of the SD files.
                return "\"destination\":\"memory-card\",\"captured_events\":" + std::to_string(count) +
                    ",\"card_state\":\"not-writing\",\"bracket_idle\":true," +
                    "\"completion\":\"camera-events-and-card-idle\",\"file_verification\":\"not-performed\",\"files\":[]," +
                    "\"remaining_before\":" + std::to_string(remaining_before) +
                    ",\"remaining_after\":" + std::to_string(remaining_after) +
                    ",\"elapsed_ms\":" + std::to_string(elapsed);
            }
            std::this_thread::sleep_for(100ms);
        }
    }
    std::string capture_host(uint64_t timeout_s) {
        if (!events.host_mode || uncertain || timeout_s < 5 || timeout_s > 3600)
            throw std::runtime_error("Host capture is unavailable or an earlier exposure is uncertain");
        // The Rust owner bounds completed files awaiting upload. The SDK still
        // downloads exactly one exposure at a time and advances its filename.
        if (current(sdk::CrDeviceProperty_StillImageStoreDestination) != sdk::CrStillImageStoreDestination_HostPC ||
            current(sdk::CrDeviceProperty_DriveMode) != sdk::CrDrive_Single ||
            current(sdk::CrDeviceProperty_FocusMode) != sdk::CrFocus_MF ||
            current(sdk::CrDeviceProperty_FileType) != sdk::CrFileType_Raw ||
            current(sdk::CrDeviceProperty_RAW_FileCompressionType) != sdk::CrRAWFile_LossLessL)
            throw std::runtime_error("Capture requires host-only, single drive, MF and Lossless Compressed RAW L");
        if (std::filesystem::space(raw_directory).available < 256ULL * 1024 * 1024)
            throw std::runtime_error("RAM buffer has less than 256 MiB free; no exposure taken");
        { std::lock_guard<std::mutex> lock(events.mutex); events.downloads.clear(); }
        const auto baseline = events.captured_events.load();
        uncertain = true;
        const auto started = Clock::now();
        const auto down = sdk::SendCommand(handle, sdk::CrCommandId_Release, sdk::CrCommandParam_Down);
        std::this_thread::sleep_for(50ms);
        const auto up = sdk::SendCommand(handle, sdk::CrCommandId_Release, sdk::CrCommandParam_Up);
        check(down, "Release down"); check(up, "Release up");
        for (;;) {
            alive();
            std::vector<std::string> files;
            { std::lock_guard<std::mutex> lock(events.mutex); files = events.downloads; }
            const auto captured = events.captured_events.load() - baseline;
            if (files.size() > 1 || captured > 1)
                throw std::runtime_error("Unexpected extra capture/download; RAM files retained");
            if (files.size() == 1) {
                auto file = std::filesystem::path(files.front());
                if (file.is_relative()) file = raw_directory / file;
                file = std::filesystem::canonical(file);
                auto extension = file.extension().string();
                std::transform(extension.begin(), extension.end(), extension.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
                if (file.parent_path() != raw_directory || extension != ".ARW" ||
                    !std::filesystem::is_regular_file(file) || std::filesystem::file_size(file) < 1024)
                    throw std::runtime_error("Invalid completed RAW download; files retained");
                if (current(sdk::CrDeviceProperty_StillImageStoreDestination) != sdk::CrStillImageStoreDestination_HostPC)
                    throw std::runtime_error("Storage destination changed during host capture");
                uncertain = false;
                return "\"destination\":\"host-ram\",\"completion\":\"sdk-download-complete\",\"path\":" +
                    quote(file.string()) + ",\"bytes\":" + std::to_string(std::filesystem::file_size(file)) +
                    ",\"captured_events\":" + std::to_string(captured) + ",\"raw_compression\":\"lossless-l\"";
            }
            if (Clock::now() - started > std::chrono::seconds(timeout_s))
                throw std::runtime_error("RAW download timed out; shutter will not be retried; inspect retained RAM files");
            std::this_thread::sleep_for(50ms);
        }
    }
    std::string restore() {
        std::vector<std::string> failures;
        // A timed-out exposure may still be running. Do not move the lens then.
        if (uncertain) return "\"restored\":false,\"reason\":\"Operation uncertain; settings retained for manual inspection\"";
        if (focus_saved) {
            try { set_checked(sdk::CrDeviceProperty_DriveMode, sdk::CrDrive_Single); focus(initial_focus, 500, true); focus_saved = false; }
            catch (const std::exception& e) { failures.push_back(std::string("focus: ") + e.what()); }
        }
        if (uncertain) return "\"restored\":false,\"reason\":\"Focus restoration uncertain; inspect camera manually\"";
        // Restore bracket values while the bracket drive is available, before restoring drive.
        // Original bracket order is restored after shot count (0 -> - -> + forces count=3).
        const auto restore_one = [&](const std::string& name) {
            for (const auto& item : saved) if (item.name == name) {
                try { set_checked(item.code, item.value); }
                catch (const std::exception& e) { failures.push_back(item.name + ": " + e.what()); }
            }
        };
        if (std::any_of(saved.begin(), saved.end(), [](const Saved& s) { return s.name == "FocusBracketOrder"; })) {
            try { set_checked(sdk::CrDeviceProperty_DriveMode, sdk::CrDrive_FocusBracket); }
            catch (const std::exception& e) { failures.push_back(e.what()); }
            restore_one("FocusBracketShotNumber");
            restore_one("FocusBracketFocusRange");
            restore_one("FocusBracketOrder");
        }
        for (auto it = saved.rbegin(); it != saved.rend(); ++it) {
            if (it->name.rfind("FocusBracket", 0) == 0) continue;
            try { set_checked(it->code, it->value); }
            catch (const std::exception& e) { failures.push_back(it->name + ": " + e.what()); }
        }
        saved.clear();
        std::string result = std::string("\"restored\":") + (failures.empty() ? "true" : "false") + ",\"failures\":[";
        for (size_t i = 0; i < failures.size(); ++i) { if (i) result += ','; result += quote(failures[i]); }
        return result + ']';
    }
    std::string warning_list() {
        std::lock_guard<std::mutex> lock(events.mutex);
        std::string result = "\"warnings\":[";
        for (size_t i = 0; i < events.warnings.size(); ++i) { if (i) result += ','; result += std::to_string(events.warnings[i]); }
        events.warnings.clear();
        return result + ']';
    }
};

int main(int argc, char** argv) {
    bool initialized = false;
    sdk::ICrEnumCameraObjectInfo* inventory = nullptr;
    int result = 0;
    try {
        if (argc == 2 && std::string(argv[1]) == "self-test") {
            if (base64(reinterpret_cast<const unsigned char*>(""), 0) != "" ||
                base64(reinterpret_cast<const unsigned char*>("f"), 1) != "Zg==" ||
                base64(reinterpret_cast<const unsigned char*>("fo"), 2) != "Zm8=" ||
                base64(reinterpret_cast<const unsigned char*>("foo"), 3) != "Zm9v")
                throw std::runtime_error("Live-view base64 self-test failed");
            // Exercise the installed SDK's data-pointer accessor without Init,
            // enumeration or a camera. Never assume a fixed transport-header size.
            std::vector<unsigned char> receive(2048, 0);
            sdk::CrImageDataBlock image;
            image.SetSize(static_cast<CrInt32u>(receive.size())); image.SetData(receive.data());
            const auto address = reinterpret_cast<uintptr_t>(image.GetImageData());
            const auto begin = reinterpret_cast<uintptr_t>(receive.data());
            if (address < begin || address - begin > receive.size() - 4)
                throw std::runtime_error("SDK preview pointer outside receive buffer");
            const auto offset = static_cast<size_t>(address - begin);
            receive[offset] = 0xff; receive[offset + 1] = 0xd8;
            receive[offset + 2] = 0xff; receive[offset + 3] = 0xd9;
            if (preview_jpeg(receive.data(), receive.size(), image.GetImageData(), 4) != "/9j/2Q==")
                throw std::runtime_error("SDK image-pointer regression failed");
            emit("\"test\":\"sd-card-completion-gate\",\"assertions\":" + std::to_string(card_capture_self_test()) +
                 ",\"preview_assertions\":" + std::to_string(preview_self_test() + 1) +
                 ",\"sdk_image_pointer_offset\":" + std::to_string(offset));
            return 0; // No SDK initialization, enumeration or camera connection.
        }
        const bool host = argc == 3 && std::string(argv[1]) == "serve-host";
        if (!host && (argc != 2 || (std::string(argv[1]) != "list" && std::string(argv[1]) != "serve")))
            throw std::runtime_error("Usage: strehl-sony-control.exe list|serve|self-test (USB a7C II only)");
        initialized = sdk::Init(0);
        if (!initialized) throw std::runtime_error("Sony SDK initialization failed");
        check(sdk::EnumCameraObjects(&inventory, 3), "EnumCameraObjects");
        std::vector<sdk::ICrCameraObjectInfo*> matches;
        std::string list = "\"sdk_version\":" + std::to_string(sdk::GetSDKVersion()) + ",\"cameras\":[";
        const auto count = inventory ? inventory->GetCount() : 0;
        for (CrInt32u i = 0; i < count; ++i) {
            auto info = const_cast<sdk::ICrCameraObjectInfo*>(inventory->GetCameraObjectInfo(i));
            const auto model = utf8(info->GetModel());
            const auto transport = utf8(info->GetConnectionTypeName());
            if (i) list += ',';
            list += "{\"model\":" + quote(model) + ",\"transport\":" + quote(transport) + '}';
            if (model == "ILCE-7CM2" && info->GetIdType() == sdk::CAMERAOBJECTID_TYPE_USB) matches.push_back(info);
        }
        list += ']';
        if (std::string(argv[1]) == "list") emit(list);
        else {
            if (matches.size() != 1) throw std::runtime_error("Connect exactly one ILCE-7CM2 via USB Remote Shoot; found " + std::to_string(matches.size()));
            Camera camera(matches.front());
            camera.disable_live_view();
            if (host) camera.host_memory(argv[2]);
            emit(list + ",\"ready\":true,\"capture_destination\":" + quote(host ? "host-ram" : "memory-card") + ",\"capture_protocol\":2,\"live_view_protocol\":1,\"host_pipeline_protocol\":1");
            std::string line;
            while (std::getline(std::cin, line)) {
                try {
                    auto args = split(line);
                    if (args.empty()) throw std::runtime_error("Empty command");
                    std::string response;
                    if (args[0] == "status" && args.size() == 1) response = camera.status();
                    else if (args[0] == "liveview" && args.size() == 2 && number(args[1]) <= 1) { camera.live_view(number(args[1]) == 1); response = "\"live_view\":" + std::string(number(args[1]) ? "true" : "false"); }
                    else if (args[0] == "preview" && args.size() == 1) response = camera.preview();
                    else if (args[0] == "magnify" && args.size() == 4) { camera.magnify(number(args[1]), number(args[2]), number(args[3])); response = "\"magnifier\":true"; }
                    else if (args[0] == "set" && args.size() == 3) { camera.set(args[1], number(args[2])); response = "\"property\":" + camera.property(args[1]); }
                    else if (args[0] == "focus" && args.size() == 3) response = camera.focus(number(args[1]), number(args[2]));
                    else if (args[0] == "capture" && args.size() == 3) response = camera.capture(number(args[1]), number(args[2]));
                    else if (args[0] == "capture-host" && args.size() == 2) response = camera.capture_host(number(args[1]));
                    else if ((args[0] == "restore" || args[0] == "quit") && args.size() == 1) response = camera.restore();
                    else throw std::runtime_error("Unknown command or wrong argument count");
                    emit(response + ',' + camera.warning_list());
                    if (args[0] == "quit") break;
                } catch (const std::exception& e) { emit_error(e); }
            }
        }
    } catch (const std::exception& e) { emit_error(e); result = 1; }
    if (inventory) inventory->Release();
    if (initialized) sdk::Release();
    return result;
}
