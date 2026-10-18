#!/bin/bash
# Read-only snapshot. Reports unavailable probes; does not install or configure.
set -u
probe() {
  printf '\n$'
  printf ' %q' "$@"
  printf '\n'
  "$@" || printf 'UNAVAILABLE/FAILED (exit %s)\n' "$?"
}
if [[ "$(uname -s)" != Darwin ]]; then
  printf 'This audit is for macOS.\n' >&2
  exit 1
fi
probe sw_vers
probe uname -m
probe sysctl -n hw.memsize hw.ncpu hw.model machdep.cpu.brand_string
probe df -h . /
# Filter disk output to avoid unnecessary hardware identifiers.
for location in . /; do
  printf '\nFilesystem for %s:\n' "$location"
  device=$(df -P "$location" | awk 'NR == 2 {print $1}')
  if disk_info=$(diskutil info "$device" 2>&1); then
    printf '%s\n' "$disk_info" | awk '/File System Personality|Type \(Bundle\)|Free Space/'
  else
    printf 'UNAVAILABLE/FAILED: %s\n' "$disk_info"
  fi
done
probe xcode-select -p
probe xcodebuild -version
probe xcodebuild -checkFirstLaunchStatus
probe xcrun --show-sdk-version
probe clang --version
probe git --version
probe python3 --version
for tool in fetch gclient gn ninja autoninja; do
  command -v "$tool" || printf '%s: absent from PATH\n' "$tool"
done
printf '\nSnapshot only; inspect failures above. No Chromium build was attempted.\n'
