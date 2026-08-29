# Two scheduling mechanisms, and only one of them is allowed to be precise

## Context

Android has two ways to make something happen later, and they are not interchangeable:

- **WorkManager** survives reboots and app updates, batches with other work, and is subject to Doze.
  It will run your job *eventually* — which for a daily nudge is exactly right, and for anything with
  a real deadline is not.
- **AlarmManager exact alarms** fire at the minute. They are lost on reboot, and since Android 14 at
  `targetSdk` 33+ the permission is **denied by default**.

Two more platform facts shape everything below:

- **`SCHEDULE_EXACT_ALARM` and `USE_EXACT_ALARM` are not alternatives.** The second is auto-granted
  and cannot be revoked, which sounds like the better deal until you read Play's policy: it is
  permitted only for apps whose core function is an alarm clock or a calendar. Declaring it in
  anything else puts the whole listing at risk to save one settings screen.
- **Vendor ROMs add a second layer of policy.** On Xiaomi's HyperOS, without *autostart* granted the
  ROM does not start the process for a broadcast at all — not `BOOT_COMPLETED`, not
  `MY_PACKAGE_REPLACED`, not an explicit `am broadcast` to a manifest receiver. Observed: a 03:00
  exact alarm landing at 06:50 without autostart, and on time in deep Doze with it.

## Decision

**One daily WorkManager sweep drives everything that is not time-critical.** It asks "what is due
today?" — derived from the data every time — and re-enqueues itself for tomorrow.

**Exact alarms are reserved for the things whose lateness has consequences**, declared with
`SCHEDULE_EXACT_ALARM`, and **the app assumes nothing about the grant**: it reads
`canScheduleExactAlarms()`, says which mechanism is actually in play, and falls back to
`setAndAllowWhileIdle` — late but real.

**Nothing persists a schedule.** Due dates are derived; the OS schedule was only ever a cache of that
derivation. So there is nothing per-item to cancel, orphan, or double-enqueue.

**Notification permission is asked from the app's own screen, never from a bare system dialog on
launch.** Android permits two denials before the dialog stops appearing for good, and there is one
place in the app that spends them.

## Alternatives

**One scheduled work item per reminder.** Sounds simpler and is not: every item is something to
cancel when the reminder is edited, to re-enqueue on boot, and to reconcile after a restore. Getting
any of those wrong produces a notification that fires twice, or one that stops firing with nothing to
show for it. A sweep has none of those states.

**A periodic work request.** WorkManager's minimum period is 15 minutes with a flex window it
chooses, so "every day at 09:00" is not expressible. A one-time request that enqueues the next one is
exact to the minute and survives being run late.

**Exact alarms for everything.** Spends a restricted permission, a battery-optimisation exemption and
the user's patience on nudges that do not need any of it. If everything is urgent, nothing is.

## Consequences

- `BootReceiver` and `PackageReplacedReceiver` exist and do almost nothing, deliberately. The update
  receiver is not optional: a schema-bumping update leaves the database at the old version until
  something opens it, and every background entry point correctly declines to work over one.
- A notification channel's importance is set at creation and **can only be lowered afterwards, by the
  user**. Creating a channel quiet is a decision with no second attempt.
- Testing any of this on a vendor ROM requires reading the autostart state first. A run against an
  unknown one proves nothing either way — `scripts/device-gate.py` reads it.
