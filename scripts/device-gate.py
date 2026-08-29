#!/usr/bin/env python3
"""What this phone will actually let the app do, read off the device rather than assumed.

**Why this exists.** An instrumented test proves the app schedules an alarm. It cannot prove the
phone will *run* it. Vendor Android — Xiaomi's HyperOS above all — adds a second layer of battery
and autostart policy on top of the platform's, and an app that passes every test can still go
completely silent on a real device. The readings below are the platform's own answers.

Three things it reads, and the reason each one matters:

  * **Autostart** (Xiaomi only). The load-bearing one. Without it the ROM **does not start the
    process for a broadcast at all** — not `MY_PACKAGE_REPLACED` after a real `adb install -r`, not
    an explicit `am broadcast` to a manifest receiver. `pidof` stays empty with `stopped=false`, and
    the broadcast is simply never delivered. With it granted, both work.

    It is a Settings toggle with **no appop and no readable per-app state**, and the grant **lapses
    on its own** — observed granted in the morning and gone by that evening, with neither `pm clear`
    nor a reinstall responsible. **Re-read it before any run that depends on it**; a run against an
    unknown autostart state proves nothing either way.

    The header count ("N apps can start in the background") is the only honest signal. A
    `uiautomator` dump's `checked` attribute reports false on every row, granted ones included.

  * **Battery optimisation.** Readable without any permission, which is why the app can lean on it
    and explain the state rather than guess.

  * **Pending alarms**, from `dumpsys alarm`. **Read the count and the instant, never the
    notification.** A notification is downstream of an alarm that fired; this only ever asks what is
    *armed*, which keeps it runnable at any hour of the day.

Usage:

    python3 scripts/device-gate.py                 # read everything
    python3 scripts/device-gate.py --autostart on  # set it, then re-read
    python3 scripts/device-gate.py --reboot        # reboot and wait for a human unlock

⚠️ **A reboot always needs a human to unlock the phone.** There is no way around it; the script
waits rather than pretending otherwise.

The driving vocabulary — `tap`, `swipe_to_end` and the rest — is imported from `edge-to-edge.py`
rather than copied. That file is the expensive asset here (`screenshots.py` does the same): its
`tap` already knows that some phones drop a bare `input tap`, that a screen still composing dumps as
an empty `ComposeView`, and that a needle has to be re-looked-for while the list is still moving.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# `edge-to-edge.py` is not an importable module name — the hyphen makes it un-`import`-able by the
# ordinary statement — so it is loaded by path. Exactly the dance `screenshots.py` does, and for the
# same reason: the alternative is a second copy of `tap` that will drift from the first.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402
_E2E = Path(__file__).resolve().parent / "edge-to-edge.py"
_spec = importlib.util.spec_from_file_location("e2e", _E2E)
e2e = importlib.util.module_from_spec(_spec)
sys.modules["e2e"] = e2e
_spec.loader.exec_module(e2e)

StepFailed = e2e.StepFailed

# The tag AlarmManager files an app's alarms under in `dumpsys alarm`. It is built from the
# **namespace**, not the applicationId — the two deliberately disagree — and the dumped line carries
# both: `*walarm*:<applicationId>/<namespace>.work.SomeReceiver`. Point this at your own receiver
# once you place an exact alarm; until then nothing reads it.
ALARM_TAG = f"{project.NAMESPACE}.work.AlarmReceiver"

# How long a write is given to reach the alarm before the reading is taken. **Fixed, and not a poll
# that stops when it likes the answer** — a retry-until-it-passes loop turns "the rebuild is slow"
# into "the rebuild happened", which is the one failure this whole file exists to catch. Generous
# enough for a Room write plus a Flow collection plus the AlarmManager round trip on a cold screen.
REBUILD_SETTLE = 2.5


# ------------------------------------------------------------------------------------------------
# Reading the alarm
# ------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AppAlarm:
    """One pending alarm as `dumpsys alarm` describes it."""

    orig_when: str  # "2026-08-20 03:00:00.000", the wall-clock instant it will fire at
    window: str  # "0" for the exact mechanism, "+38m55s" or similar for best-effort
    exact_reason: str  # "permission" when exact; absent (and so "") on the degraded path
    when_elapsed: str
    max_when_elapsed: str

    @property
    def exact(self) -> bool:
        """Whether this is `setExactAndAllowWhileIdle` rather than the degraded path.

        **The only pre-fire proof of which mechanism is armed** . `window=0` alone is not
        enough and neither is the appop: the pair `whenElapsed == maxWhenElapsed` is what says the
        OS has been given no latitude at all. The best-effort alarm reads a window of tens of
        minutes and a `maxWhenElapsed` that far ahead of its `whenElapsed`.
        """
        return self.window == "0" and self.when_elapsed == self.max_when_elapsed

    @property
    def at(self) -> str:
        """The fire instant to the minute — what a check compares against."""
        return self.orig_when[:16]


def app_alarms() -> list[AppAlarm]:
    """Every *pending* alarm this app has placed.

    **Everything above `Removal history:` is pending; everything below it has already gone.** That
    boundary is not cosmetic — the removal history holds every alarm this package has ever had
    cancelled, so a parser that reads the whole dump reports a dozen and calls the invariant broken.
    """
    out = e2e.shell("dumpsys alarm")
    lines = out.splitlines()
    end = next((i for i, line in enumerate(lines) if "Removal history:" in line), len(lines))

    found: list[AppAlarm] = []
    for i in range(end):
        if ALARM_TAG not in lines[i]:
            continue
        # The fields are spread over the three lines after the tag, so the block is read as one
        # string rather than field by field.
        block = "\n".join(lines[i : i + 6])
        orig = re.search(r"origWhen=([\d-]+ [\d:.]+)", block)
        window = re.search(r"\bwindow=(\S+)", block)
        reason = re.search(r"exactAllowReason=(\S+)", block)
        pair = re.search(r"\bwhenElapsed=(\S+)\s+maxWhenElapsed=(\S+)", block)
        found.append(
            AppAlarm(
                orig_when=orig.group(1) if orig else "?",
                window=window.group(1) if window else "?",
                exact_reason=reason.group(1) if reason else "",
                when_elapsed=pair.group(1) if pair else "?",
                max_when_elapsed=pair.group(2) if pair else "??",
            )
        )
    return found


# ------------------------------------------------------------------------------------------------
# The report
# ------------------------------------------------------------------------------------------------


@dataclass
class Report:
    """What every check writes into: one row per reading, and a pass/fail tally."""

    rows: list[dict] = field(default_factory=list)

    def record(self, check: str, step: str, expected: str, actual: str, ok: bool, note: str = "") -> None:
        self.rows.append(
            {"check": check, "step": step, "expected": expected, "actual": actual, "ok": ok, "note": note}
        )
        mark = "ok  " if ok else "FAIL"
        print(f"  [{mark}] {step:38s} expected {expected:22s} got {actual}" + (f"  ({note})" if note else ""))

    @property
    def failed(self) -> int:
        return sum(1 for row in self.rows if not row["ok"])


REPORT = Report()
_CHECK = "?"


def armed(step: str, at: str | None = None, *, exact: bool | None = None) -> list[AppAlarm]:
    """Assert exactly one pending alarm, optionally at a named minute.

    `at` is "YYYY-MM-DD HH:MM". Left out where the check is about the *count* rather than the
    instant, where "exactly one alarm survives" is the whole claim.
    """
    time.sleep(REBUILD_SETTLE)
    alarms = app_alarms()
    want = f"1 alarm{f' @ {at}' if at else ''}"
    if len(alarms) != 1:
        REPORT.record(_CHECK, step, want, f"{len(alarms)} alarms", False)
        return alarms
    got = alarms[0]
    ok = at is None or got.at == at
    if ok and exact is not None:
        ok = got.exact == exact
    REPORT.record(
        _CHECK,
        step,
        want,
        # The **date** as well as the time. Reading only `HH:MM` is what made a run near the seed's
        # own 20:00 slot unreadable: "20:00" and "08:00" were today's and tomorrow's, and which was
        # which was the entire question.
        f"1 alarm @ {got.at}",
        ok,
        f"{'exact' if got.exact else 'best-effort'}, window={got.window}",
    )
    return alarms


def disarmed(step: str) -> None:
    """Assert **no** pending alarm — the half of the invariant a stale alarm breaks silently."""
    time.sleep(REBUILD_SETTLE)
    alarms = app_alarms()
    REPORT.record(_CHECK, step, "0 alarms", f"{len(alarms)} alarms", len(alarms) == 0)


def observe(step: str, expected: str, actual: str, ok: bool, note: str = "") -> None:
    """Record something that is not an alarm count — a screen's words, a row count, a state."""
    REPORT.record(_CHECK, step, expected, actual, ok, note)


# ------------------------------------------------------------------------------------------------
# Driving vocabulary this file adds
# ------------------------------------------------------------------------------------------------


def visible() -> list[str]:
    """Every label the app is currently showing, structural nodes dropped.

    Used for the checks that are about *words on a screen* rather than an alarm — the blocked
    delivery line, the delete dialog's counts — where the assertion is "this sentence is on screen".
    """
    skip = {"View", "Button", "FrameLayout", "LinearLayout", "ComposeView", "ScrollView", "CheckBox"}
    return [n.label for n in e2e.dump_ui() if n.package == e2e.PACKAGE and n.label and n.label not in skip]


def on_screen(needle: str) -> bool:
    """Whether any label contains `needle`, case-insensitively. A question, never a tap."""
    return any(norm(needle) in norm(label) for label in visible())


def norm(text: str) -> str:
    """Times as a needle can spell them.

    The app formats a time of day with a **narrow no-break space** before AM/PM (U+202F) — the
    correct typography, and invisible in a terminal — so the chip an owner reads as "8:00 AM" is
    `8:00\u202fAM` in the dump and a needle typed with an ordinary space matches nothing. Both
    unusual spaces are folded here rather than in each needle, because a needle that has to be
    written with an escape in it is a needle someone will get wrong.
    """
    return text.replace("\u202f", " ").replace("\u00a0", " ").casefold()


def all_labels() -> list[str]:
    """Every label on a screen top to bottom, collected while scrolling to the end.

    **What a viewport-only read gets wrong here.** The Care tab's delivery line — the sentence this
    whole gate item is about — is composed *below* Routine care, so a dump of the tab as it opens
    does not contain it and `on_screen` answers False for a line that is plainly on the screen.
    Worse, the negative form of that check then passes for the same wrong reason, which is a cell
    that cannot fail.
    """
    seen: list[str] = []
    previous = ""
    for _ in range(e2e.TAP_SCROLL_CAP):
        for label in visible():
            if label not in seen:
                seen.append(label)
        current = e2e.screen_signature(e2e.dump_ui())
        if current == previous:
            break
        previous = current
        e2e.swipe_up()
    return seen


def anywhere(needle: str) -> bool:
    """Whether `needle` appears anywhere on a screen, scrolling to look. A question, never a tap.

    [on_screen] asks about the current viewport, which is the right question for a dialog and the
    wrong one for a row in a year-long list or a line under a tab's last section.
    """
    return any(norm(needle) in norm(label) for label in all_labels())


def delivery_line() -> str:
    """The Care tab's reminder-delivery sentence, whichever of the six it currently is.

    Recorded rather than merely matched, so a reading that fails says *which* state the app was in
    — the difference between "blocked" and "best-effort, battery" is the whole finding.
    """
    # The **longest** match, because the section this line sits under is headed *Reminders* and a
    # first-match read returns the heading — a one-word answer that looks like a state and is not.
    lines = [label for label in all_labels() if "reminder" in norm(label)]
    return max(lines, key=len) if lines else "(no delivery line)"


def matches(needle: str, *, exact: bool = False, scroll: bool = False) -> list:
    """Every distinct node containing `needle`, in the order the dump lists them.

    `exact` compares the node's **text** for equality instead, which is what tells a button apart
    from the dialog title above it: tapping a course's *Delete* opens *"Delete this course?"*, and a
    substring needle then matches the question rather than the answer. Every confirm below uses it.

    **`e2e.find` returns the smallest match and that is wrong here.** A course detail screen carries
    several *Delete* buttons; the smallest of them is whichever the
    font happened to lay out narrowest, which is not a choice at all. Document order is, because the
    screen's own actions are composed above its history — so index 0 is always the top one's.

    Nodes are de-duplicated by centre, since Compose publishes a merged node for a row as well as
    the leaf inside it and both match the same needle.
    """
    if scroll:
        # The same scroll-while-the-screen-is-still-moving loop `e2e.tap` uses, and it is needed for
        # the same reason: Home's *Archive* and *Delete* sit under the whole profile card, so a
        # single dump of the top of the screen reports them absent. The signature check is what
        # stops it swiping sixteen times on a screen that cannot scroll.
        previous = ""
        for attempt in range(e2e.TAP_SCROLL_CAP):
            here = matches(needle, exact=exact)
            if here:
                return here
            current = e2e.screen_signature(e2e.dump_ui())
            if attempt >= e2e.MIN_TAP_TRIES - 1 and current == previous:
                return []
            previous = current
            e2e.swipe_up()
        return []

    wanted = norm(needle)
    seen: dict[tuple[int, int], object] = {}
    for node in e2e.dump_ui():
        if node.package != e2e.PACKAGE or node.bounds.area <= 0:
            continue
        if exact:
            if norm(node.text) != wanted:
                continue
        elif wanted not in norm(node.text) and wanted not in norm(node.desc):
            continue
        centre = ((node.bounds.left + node.bounds.right) // 20, (node.bounds.top + node.bounds.bottom) // 20)
        if centre not in seen or node.bounds.area < seen[centre].bounds.area:
            seen[centre] = node
    return [seen[key] for key in sorted(seen, key=lambda k: (k[1], k[0]))]


def tap_node(node) -> None:
    """Tap a node already found, with the same look-again retry `e2e.tap` uses.

    The retry is not optional on this phone: exit status proves nothing about whether a tap landed,
    so the screen is asked instead.
    """
    x = (node.bounds.left + node.bounds.right) // 2
    y = (node.bounds.top + node.bounds.bottom) // 2
    before = e2e.screen_signature(e2e.dump_ui())
    for _ in range(3):
        e2e.shell(f"input touchscreen tap {x} {y}")
        e2e.settle(1.2)
        if e2e.screen_signature(e2e.dump_ui()) != before:
            return


def tap_nth(needle: str, index: int = 0, *, exact: bool = False, scroll: bool = True) -> None:
    """Tap the `index`-th node containing `needle`, top to bottom. See [matches]."""
    found = matches(needle, exact=exact, scroll=scroll)
    if index >= len(found):
        raise StepFailed(f"asked for match {index} of {needle!r}, found {len(found)}: {visible()[:20]}")
    tap_node(found[index])


def tap_exact(text: str, index: int = 0) -> None:
    """Tap a control whose label is exactly `text` — the confirm-button form of [tap_nth]."""
    tap_nth(text, index, exact=True)


def confirm(title: str, button: str) -> None:
    """Press `button` in the dialog headed `title`, and fail if that dialog is not up.

    **Position is the only thing that tells a dialog's button from the screen's own.** A course
    a detail screen can carry several *Delete* buttons; opening any of them raises a
    dialog whose confirm says *Delete* as well, and `uiautomator` hands back one flat tree with no
    reliable marker of which window a node came from. What is reliable is that a dialog's buttons
    are drawn **below its title**, so the confirm is the first exact match under it.

    Checking the title first is the other half: a tap that missed leaves the screen unchanged, and
    without this the next tap would hit the *screen's* Delete and destroy the wrong row — an
    unnoticed second delete looks exactly like a rebuild that did not run.
    """
    e2e.settle(0.8)
    # Never scrolling: a dialog is not a list, and a swipe aimed at one lands on the scrim behind it.
    heading = next((n for n in matches(title)), None)
    if heading is None:
        raise StepFailed(f"dialog {title!r} never opened; on screen: {visible()[:20]}")
    below = [n for n in matches(button, exact=True) if n.bounds.top > heading.bounds.top]
    if not below:
        raise StepFailed(f"dialog {title!r} has no {button!r} under it; on screen: {visible()[:20]}")
    tap_node(below[0])


def pick_time(hour: int, minute: int = 0) -> None:
    """Drive the Material time picker's clock dial, then OK.

    The dial publishes each position as a node described *"N hours"* / *"N minutes"*, which is the
    only reason this is drivable at all — there is no text field to type into unless the owner
    switches modes, and the mode toggle is one more thing to get wrong in nine locales. The hour
    ring is 24 positions here, so `hour` is 0–23 whatever the display format says.
    """
    e2e.settle(1.0)
    e2e.tap(f"{hour} hours")
    e2e.settle(0.8)
    e2e.tap(f"{minute} minutes")
    e2e.settle(0.8)
    e2e.tap("OK")
    e2e.settle(1.0)


SWITCH_ID = "com.android.settings:id/switchWidget"

AUTOSTART_ACTIVITY = "com.miui.securitycenter/com.miui.permcenter.autostart.AutoStartManagementActivity"

# The label HyperOS lists this build under. The debug build takes `applicationIdSuffix = ".debug"`
# and its own label, so it appears beside a Play install rather than replacing it —
# which is the whole point, and also why the needle has to be the longer of the two names.
AUTOSTART_LABEL = f"{project.APP_NAME} Debug"


def shell_ok(cmd: str) -> str:
    """`adb shell`, tolerating a non-zero exit.

    `e2e.shell` raises on one, which is right for the commands that ought to succeed and wrong for
    the ones whose *failure is the answer*: `pidof` exits 1 when the process is not running, which
    is precisely the reading the reboot check is taking.
    """
    import subprocess

    done = subprocess.run(["adb", "shell", cmd], capture_output=True, text=True)
    return done.stdout


def _system_xml() -> str:
    """A `uiautomator` dump as raw XML, for the screens that are not this app's.

    `e2e.dump_ui` filters to the app's own package, which is right everywhere else and useless here:
    the autostart list and the channel settings both belong to the OEM.
    """
    e2e.shell("uiautomator dump /sdcard/alarm-gate.xml")
    return e2e.adb("exec-out", "cat", "/sdcard/alarm-gate.xml")


def autostart_state() -> tuple[int, bool]:
    """The autostart screen's header count, and whether this build is in the allowed list.

    **The header is the only readable signal.** A `uiautomator` dump's `checked` attribute lies on
    this screen — every row reports false, granted ones included (read 2026-08-18) — so the
    state is inferred from the count in the heading and from which names appear above the
    "aren't allowed" divider. The screen also *keeps its scroll position* between visits, so it is
    wound back to the top before reading or the heading is simply not on screen.
    """
    # **Force-stopped rather than scrolled back to the top**, and that is a fix for damage this
    # helper did rather than a tidiness. The screen keeps its scroll position between visits, so the
    # heading needs the list wound back — but a swipe that ends near the top of the display pulls
    # the *notification shade* down instead once the list has nowhere left to go, and on a locked
    # phone the shade takes focus and will not give it back to `adb`. Restarting the activity from
    # cold puts it at the top with no swiping at all.
    e2e.shell("am force-stop com.miui.securitycenter")
    e2e.settle(1.0)
    e2e.shell(f"am start -n {AUTOSTART_ACTIVITY}")
    e2e.settle(3.5)
    xml = _system_xml()
    count = re.search(r'text="(\d+) apps can start', xml)
    allowed = xml.split("aren&#39;t allowed")[0] if "aren&#39;t allowed" in xml else xml.split("aren't allowed")[0]
    return (int(count.group(1)) if count else -1, f'text="{AUTOSTART_LABEL}"' in allowed)


def set_autostart(on: bool) -> bool:
    """Grant or revoke autostart for this build, by tapping its row's switch.

    **There is no appop for this.** `AUTO_START` is not in `cmd appops`' vocabulary — it is a
    Settings toggle and nothing else, which is why every previous run had to be set up by hand. The
    switch sits at the right edge of the row, so the tap is aimed at the row's vertical centre and
    the screen's right margin rather than at the label.
    """
    for _ in range(3):
        count, listed = autostart_state()
        if listed == on:
            return True
        # Wound back to the top by [autostart_state]; the row is found by scrolling down from there,
        # which reaches it whether it is in the allowed list or the long denied one below it.
        for _ in range(40):
            xml = _system_xml()
            row = re.search(
                rf'text="{re.escape(AUTOSTART_LABEL)}"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
            )
            if row:
                top, bottom = int(row.group(2)), int(row.group(4))
                width = re.search(r'bounds="\[0,0\]\[(\d+),(\d+)\]"', xml)
                right_margin = int(width.group(1)) - 130 if width else 1050
                e2e.shell(f"input touchscreen tap {right_margin} {(top + bottom) // 2}")
                e2e.settle(2.0)
                break
            # Downward through the list only. The upward direction is [autostart_state]'s problem
            # and it does not swipe at all any more.
            e2e.shell("input swipe 600 2000 600 900 250")
            e2e.settle(0.6)
        else:
            return False
    return autostart_state()[1] == on


def wait_for_unlock(timeout: float = 900.0) -> None:
    """Stop and ask a person to unlock the phone, then carry on when they have.

    **This device has a password and `adb` cannot get past it** — not `wm dismiss-keyguard`, not a
    swipe, not a power cycle. So a reboot is not a step a script may take and then continue through;
    it is a step that hands the run back to a person for a moment.

    Ploughing on instead is worse than stalling, because a locked phone refuses far more than taps
    and every refusal is misleading: `am start` answers `Error type 3 / Activity class ... does not
    exist` for an activity plainly in the resolver table, `adb install` answers
    `INSTALL_FAILED_USER_RESTRICTED` because its prompt cannot be shown, and `uiautomator dump`
    comes back empty. On 2026-08-19 those three cost a session's worth of chasing a package that was
    never broken. Asking the question first turns all of them into one known state.
    """
    if "isKeyguardShowing=false" in e2e.shell("dumpsys window | grep isKeyguardShowing"):
        return
    print("\n  ⏸  THE PHONE IS LOCKED — please unlock it. Waiting…", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if "isKeyguardShowing=false" in e2e.shell("dumpsys window | grep isKeyguardShowing"):
            print("  ▶  unlocked, carrying on", flush=True)
            # Held awake while on USB for the rest of the run, so the screen cannot lock itself
            # again halfway through the taps that follow and strand the check a second time.
            # `main` puts it back.
            e2e.shell("svc power stayon usb")
            e2e.settle(2.0)
            return
        time.sleep(5)
    raise StepFailed("the phone was never unlocked; the reboot arm cannot continue without it")


def reboot_and_wait(timeout: float = 180.0) -> float:
    """Reboot the phone and come back when it is up. Returns how long that took.

    **Nothing is launched afterwards, and that is the whole design of the check.** An alarm does not
    survive a reboot — `AlarmManager` forgets every one of them — so a pending alarm read after
    boot can only have been put there by `BootReceiver`. Touching the app first would arm it from
    the ordinary process-start path and prove nothing about the receiver.
    """
    started = time.time()
    e2e.adb("reboot")
    time.sleep(8)
    e2e.adb("wait-for-device")
    while time.time() - started < timeout:
        if e2e.shell("getprop sys.boot_completed").strip() == "1":
            # The receiver is not synchronous with `sys.boot_completed`: BOOT_COMPLETED is queued
            # behind the rest of the boot, and reading the alarm list too early reports an empty
            # one for a receiver that simply had not run yet — a false negative that looks exactly
            # like the finding.
            time.sleep(45)
            # Reading the alarm list needs no screen, but everything after it does — and the check
            # must not walk into a locked phone's misleading refusals. See [wait_for_unlock].
            return time.time() - started
        time.sleep(3)
    raise StepFailed(f"the phone never finished booting in {timeout:.0f}s")


def channel_importance(channel: str = "reminders") -> int:
    """One channel's importance as the framework holds it, or -1 if the channel is absent.

    Read from `dumpsys notification` rather than from the app, because the app's reading of it is
    the thing under test. `4` is the channel as created, `0` is `IMPORTANCE_NONE` — the owner having
    switched this one category off in system settings, which nothing in the app can ask back.

    The channel does not exist until the Care tab has been opened with a course on it: creating it
    lazily is deliberate, so a user for whom a feature is irrelevant never sees the row in their
    settings at all.
    """
    out = e2e.shell("dumpsys notification --noredact")
    found = re.search(rf"mId='{channel}'.{{0,200}}?mImportance=(-?\\d+)", out, re.S)
    return int(found.group(1)) if found else -1


def set_channel(on: bool, channel: str = "reminders") -> bool:
    """Switch one channel on or off through the phone's own settings screen.

    **There is no `adb` setter for this.** `cmd notification` can allow a listener, set DND and post
    a notification, but it cannot change a channel's importance — the only writer is the system
    settings screen, so the screen is what gets driven. `CHANNEL_NOTIFICATION_SETTINGS` opens
    straight onto the one channel, which keeps the drive to a single toggle rather than a walk
    through a package's whole notification tree.

    Verified from `dumpsys` after every attempt rather than from the switch's own `checked`
    attribute: this is the same phone whose autostart screen reports `checked=false` on every row
    including the granted ones, so a toggle's self-report is not evidence here.
    """
    want = 4 if on else 0
    for _ in range(3):
        if channel_importance() == want:
            return True
        e2e.shell(
            "am start -a android.settings.CHANNEL_NOTIFICATION_SETTINGS "
            f"--es android.provider.extra.APP_PACKAGE {e2e.PACKAGE} --es android.provider.extra.CHANNEL_ID {channel}"
        )
        e2e.settle(2.5)
        e2e.shell("uiautomator dump /sdcard/alarm-gate.xml")
        xml = e2e.adb("exec-out", "cat", "/sdcard/alarm-gate.xml")
        # The first `switchWidget` on the screen is *Show notifications*, the channel's own master
        # toggle. Named by resource id because this screen is the OEM's and its wording is not ours
        # to rely on — it happens to be English here and need not stay that way.
        node = re.search(rf'resource-id="{re.escape(SWITCH_ID)}"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
        if node is None:
            node = re.search(rf'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*?resource-id="{re.escape(SWITCH_ID)}"', xml)
        if node is None:
            return False
        left, top, right, bottom = (int(g) for g in node.groups())
        e2e.shell(f"input touchscreen tap {(left + right) // 2} {(top + bottom) // 2}")
        e2e.settle(2.0)
        e2e.shell("input keyevent KEYCODE_BACK")
        e2e.settle(1.0)
    return channel_importance() == want




def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--autostart", choices=["on", "off"], help="set Xiaomi's autostart and re-read it")
    parser.add_argument("--reboot", action="store_true", help="reboot and wait for the unlock")
    args = parser.parse_args()

    if args.autostart:
        set_autostart(args.autostart == "on")

    count, present = autostart_state()
    print(f"autostart screen present : {present}")
    print(f"apps allowed to autostart: {count}")
    print(f"battery optimised        : {shell_ok(f'dumpsys deviceidle whitelist | grep -c {PACKAGE}').strip()}")
    print(f"exact alarms permitted   : {'yes' if 'true' in shell_ok(f'dumpsys alarm | grep -A2 {PACKAGE}').lower() else 'unknown'}")
    print(f"alarms filed under tag   : {ALARM_TAG}")
    for alarm in app_alarms():
        print(f"  {alarm}")

    if args.reboot:
        reboot_and_wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
