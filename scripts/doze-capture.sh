#!/usr/bin/env bash
# Capture the evidence from an overnight Doze run, read-only, in one command.
#
# Run it with the notification shade UNTOUCHED: swiping it destroys the notification
# record, and every hour of ordinary use pushes the fire time closer to falling out of
# the batterystats and logcat ring buffers.
#
# The cable is a question rather than a habit. Plugging in after everything has fired
# cannot affect what already fired - but charging ends Doze instantly, so plugging in
# while a later alarm is still pending destroys the half of the run that has not
# happened yet. Capture over wireless adb (adb connect <phone>:5555) whenever that is
# the case; the guard at the end of this script says which case you are in.
#
#   ./scripts/doze-capture.sh [output-dir]
set -euo pipefail

# Read from the one place the toolchain keeps it, so a rename reaches this too.
PKG=$(python3 "$(dirname "$0")/project.py" | awk '/^DEBUG_APPLICATION_ID/{print $2}')
HAS_DB=$(python3 "$(dirname "$0")/project.py" | awk '/^HAS_DATABASE/{print $2}')
DB=$(python3 "$(dirname "$0")/project.py" | awk '/^DATABASE_FILE/{print $2}')
OUT="${1:-doze-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"

if ! adb shell true >/dev/null 2>&1; then
  echo "No device. Connect the phone (wireless adb if an alarm is still pending) and accept the USB debugging prompt." >&2
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

# usagestats outlives logcat by days and answers *whether* the app ran at all - which is
# the only question still answerable the morning after a night nobody captured. An app
# built from this template lost a whole night's run to exactly that, and this line is
# what would have saved it.
adb shell dumpsys usagestats              > "$OUT/usagestats.txt"

# The database says what the app believed; the dumps say what Android did. Both, or
# neither explains the other. The WAL is not optional — without it the app's most recent
# writes look absent. Skipped when the app has no database (scripts/project.py).
if [ "$HAS_DB" = "yes" ]; then
  for f in "$DB" "$DB-wal" "$DB-shm"; do
    adb exec-out run-as "$PKG" cat "databases/$f" > "$OUT/$f" 2>/dev/null || true
  done
fi

date -Is > "$OUT/captured-at.txt"
echo "Captured to $OUT/"
# `grep -c` exits 1 on a zero count, and `pipefail` + `set -e` would end the script here
# on the ordinary case of no notification - silently taking the guard below with it.
grep -c "pkg=$PKG" "$OUT/notification.txt" 2>/dev/null \
  | xargs -I{} echo "  {} live notification records for the app" || true

# Is the run actually over? Pending entries only - everything below "Removal history" is
# the past, and reading that as an armed alarm is the mistake this whole file is against.
PENDING=$(sed -n '1,/Removal history/p' "$OUT/alarm.txt" | grep -c "walarm\*:$PKG" || true)
if [ "${PENDING:-0}" -gt 0 ]; then
  echo "  $PENDING alarm(s) STILL PENDING for $PKG - the run is not over."
  echo "  Do not plug the phone in: charging ends Doze and voids what has yet to fire."
else
  echo "  nothing pending for $PKG - the run is complete, the cable is safe."
fi
