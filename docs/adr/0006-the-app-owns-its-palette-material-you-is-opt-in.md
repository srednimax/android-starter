# The app owns its palette; Material You is opt-in

## Context

Material 3 offers dynamic colour: on Android 12+ the scheme is derived from the user's wallpaper.
It looks excellent, it is one line to enable, and it is the default in most templates.

It also means **nothing on Android 12+ reads the app's own colour scheme at all**. If dynamic colour
is on by default, the palette you designed is invisible on almost every device that runs the app.

Separately, a light/dark override is not a Compose-only problem. The window background is painted
from the XML theme *before* Compose composes anything, and the system-bar scrim is a `values-night/`
colour resolved at inflation. Both follow Android's own configuration. So a Compose-only override
leaves them following the **phone** while the app follows the **user** — visible on API 26–28, where
there is no system dark mode to have agreed with by accident.

## Decision

**Dynamic colour defaults off**, behind a Settings toggle. The app's own scheme is what a user sees
unless they ask otherwise.

**The scheme is generated, not hand-picked.** `scripts/gen_scheme.py` derives ~36 Material roles from
four brand seeds using Material's own tonal-palette construction (CAM16/HCT), and prints a contrast
report. The seeds are the judgement; the roles are arithmetic.

**Light/dark is moved in two places, and both are load-bearing:** `AppTheme` picks the Compose scheme,
and `applyThemeMode` calls `AppCompatDelegate.setDefaultNightMode` to move the *configuration*, so the
window and the bars agree.

**Colours come from `MaterialTheme`, never literals.** Spacing comes from `theme/Spacing.kt`.

## Alternatives

**Dynamic colour on by default.** Free, pretty, and makes the app's identity invisible where it
matters. Also makes any contrast guarantee unverifiable — you cannot check a palette you do not
control.

**Hand-pick the roles.** Breaks the fixed tonal relationship each role holds with its family, and the
failure surfaces as a contrast bug on one screen out of thirty rather than as a visible mistake in
the palette file.

**Compose-only dark mode.** Leaves the window background and the bar scrim following the phone.

## Consequences

- `theme/Color.kt` is generated. Never edit a role; edit the seeds and re-run.
- `applyThemeMode` must be called from `MainApplication.onCreate` — before any Activity exists, so
  the first window is right — *and* from the Settings toggle. It is process-wide and process-only:
  AppCompat persists an application locale but not a night mode, which is why `AppPreferences` stores
  it and why the call is repeated on every cold start.
- The startup theme is read with one blocking `DataStore` read, deliberately. A `Flow` collected in a
  composition arrives a frame late, which is a visible light flash on every cold start for a user who
  chose dark.
- The system-bar **scrim** lives in four `colors.xml` qualifiers, not in a style. `night` outranks
  `vN` in Android's qualifier precedence, so `values-night/` would beat `values-v29/` on an API 29+
  phone in dark mode; `values-night-v29/` is what settles it, and a `<style>` cannot merge across
  qualified files the way one `<color>` reference can.
