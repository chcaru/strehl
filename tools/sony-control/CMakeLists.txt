cmake_minimum_required(VERSION 3.21)
project(strehl_sony_control LANGUAGES CXX)
if(NOT WIN32)
  message(FATAL_ERROR "This prototype currently targets the Windows x64 Sony SDK")
endif()
if(NOT EXISTS "${SONY_SDK_ROOT}/app/CRSDK/CameraRemote_SDK.h")
  message(FATAL_ERROR "SONY_SDK_ROOT must name the extracted SimpleCli directory")
endif()
add_executable(strehl-sony-control strehl-sony-control.cpp card-capture.h)
target_compile_features(strehl-sony-control PRIVATE cxx_std_17)
target_compile_definitions(strehl-sony-control PRIVATE UNICODE _UNICODE NOMINMAX)
target_compile_options(strehl-sony-control PRIVATE /W4 /WX /utf-8 /guard:cf)
target_include_directories(strehl-sony-control SYSTEM PRIVATE "${SONY_SDK_ROOT}/app/CRSDK")
target_link_libraries(strehl-sony-control PRIVATE "${SONY_SDK_ROOT}/external/crsdk/Cr_Core.lib")
set_target_properties(strehl-sony-control PROPERTIES
  MSVC_RUNTIME_LIBRARY MultiThreaded
  RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/../bin")
add_custom_command(TARGET strehl-sony-control POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory "${SONY_SDK_ROOT}/external/crsdk" "$<TARGET_FILE_DIR:strehl-sony-control>"
  COMMAND ${CMAKE_COMMAND} -E copy "${SONY_SDK_ROOT}/README.md" "$<TARGET_FILE_DIR:strehl-sony-control>/sony-sdk-notices.md")
