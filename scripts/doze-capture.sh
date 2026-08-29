#!/usr/bin/env bash
# Capture the evidence from an overnight Doze run, read-only, in one command.
#
# Run it with the phone plugged in and the shade UNTOUCHED. Plugging in after the
# fire time cannot affect what already fired; swiping the shade destroys the
# notification record, and every hour of ordinary use pushes the fire time closer
# to falling out of the batterystats and logcat ring buffers. So: plug in, run
# this, then use the phone however you like.
#
#   ./scripts/doze-capture.sh [output-dir]
set -euo pipefail

# Read from the one place the toolchain keeps it, so a rename reaches this too.
PKG=$(python3 "$(dirname "$0")/project.py" | awk '/^DEBUG_APPLICATION_ID/{print $2}')
DB=$(python3 "$(dirname "$0")/project.py" | awk '/^DATABASE_FILE/{print $2}')
OUT="${1:-doze-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"

if ! adb shell true >/dev/null 2>&1; then
  echo "No device. Plug the phone in and accept the USB debugging prompt." >&2
  exit 1
fi

# Volatile first — these are the ring buffers that lose the fire time as the day goes on.
adb shell dumpsys batterystats --history  > "$OUT/batterystats-history.txt"
adb logcat -d -b main -b system -b events > "$OUT/logcat.txt"
adb shell dumpsys notification --noredact > "$OUT/notification.txt"

# Then the stable ones.
adb shell dumpsys alarm                   > "$OUT/alarm.txt"
adb shell dumpsys jobscheduler            > "$OUT/jobscheduler.txt"
adb shell dumpsys deviceidle              > "$OUT/deviceidle.txt"
adb shell dumpsys battery                 > "$OUT/battery.txt"
adb shell cmd appops get "$PKG" SCHEDULE_EXACT_ALARM > "$OUT/appops.txt"

# The database says what the app believed; the dumps say what Android did. Both, or
# neither explains the other. The WAL is not optional — without it courses look absent.
for f in "$DB" "$DB-wal" "$DB-shm"; do
  adb exec-out run-as "$PKG" cat "databases/$f" > "$OUT/$f" 2>/dev/null || true
done

date -Is > "$OUT/captured-at.txt"
echo "Captured to $OUT/"
grep -c "pkg=$PKG" "$OUT/notification.txt" 2>/dev/null \
  | xargs -I{} echo "  {} live notification records for the app"
