# Definition of done — what is still open

The **live checklist**. Keep it short: when an item closes, tick it, write the *result* into whatever
long-form record you keep, and delete the detail from here. A session should be able to pick up the
work by reading this file alone.

## The standing schema gate — never ticked, checked at every bump

**An update must migrate an existing install without losing anything** (ADR-0001). This item does not
close. Whenever `APP_SCHEMA_VERSION` changes, all five hold before the release goes out:

1. `MIGRATION_x_y` written **and registered in** `APP_MIGRATIONS` for every step. A migration Room
   never runs is not a migration, and nothing about the build complains.
2. The exported `app/schemas/*/N.json` committed — every later migration is transcribed from it,
   never from the entity classes.
3. `SchemaGateTest` extended, so the **launch gate** is proven to let the upgrade through. Every
   migration test opens the database directly and walks past that gate; this assertion is the only
   thing standing in front of it.
4. A migration test proving the **rows survive** — read values back, do not merely assert nothing
   threw. `runMigrationsAndValidate` compares *shapes* and is blind to a table emptied by a cascading
   `DROP`.
5. **An actual upgrade watched on a phone**: install the previous build, put real data in it, install
   the new one over the top, confirm the app opens and the data is there.
   `./gradlew assembleDebug -PreleaseShapedDebug` is how to do this without touching a Play install —
   it is minified *and* `BuildConfig.DEBUG == false`, so migrations are registered rather than the
   destructive fallback. ⚠️ **Both halves are load-bearing**: a plain debug build takes the fallback
   and proves the opposite of what you wanted.

`scripts/schema-gate.py` enforces 1–3 mechanically in CI. Items 4 and 5 are yours.

## Before the first upload

- [ ] **Replace the placeholder mark.** `art/mark.py`, then `python3 art/make-launcher-icon.py` and
      `make-feature-graphic.py`. Record the provenance in `art/README.md` — where the art came from is
      the thing most likely to block a first upload, and it is discovered late.
- [ ] **Replace the placeholder domain.** `data/ItemEntity.kt` and `ui/items/`.
- [ ] **Choose the palette.** Four seeds in `scripts/gen_scheme.py`, regenerate `theme/Color.kt`,
      read the contrast report it prints on stderr.
- [ ] **Write the listing.** `docs/store-listing.md` — every heading in it is parsed by a script.
- [ ] **Write the privacy policy** and confirm GitHub Pages is serving `docs/`. Play requires a
      *hosted* URL, and an offline app has no server of its own.
- [ ] **Create the upload keystore, outside the repo**, and put its four values in
      `local.properties`. Back it up somewhere that is not this machine: losing it means never being
      able to update the app on Play again.
- [ ] **Set up the GitHub repository** — `python3 scripts/repo-setup.py` does the ruleset, the
      merge setting and Pages; the release-please PAT is the one step it cannot do, and without it
      no release PR is ever opened. *Setting up a new repository* in [`RELEASING.md`](RELEASING.md).
      **None of this is inherited from the template** — GitHub copies files, never settings — and
      the build stays green while it is all still undone.
- [ ] **Set the five Play secrets and create the service account** (`docs/RELEASING.md`) — the
      service account is the one step CI cannot do for itself.
- [ ] **Decide the `applicationId` deliberately.** It is fixed the moment the Play entry is created —
      not renameable, not transferable without losing every install and review.

## Standing checks that never close

- [ ] **Every release: run the artifact checks on the built AAB**, not on the source.
      `aab-permissions.py` is the one that finds what a *dependency* merged into your manifest —
      a permission you never declared, or a `uses-feature` that quietly filters the app off devices.
- [ ] **Every release: read the release notes gate's output** rather than trusting it passed.
- [ ] **Every dependency bump: re-run `licensee`.** The build fails on an unallowed licence, which is
      the point — but the fix is two things, the allowlist *and* the bundled text.
- [ ] **Test the release-shaped build on a device.** A missing R8 keep rule does not crash; it makes
      a feature silently stop working.
