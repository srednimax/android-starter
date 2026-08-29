# Versioning & releasing

Versions are automated from git — you never hand-edit them. This mirrors what
`standard-version` does in the JS world, adapted to Android's two version fields.

## The two Android version fields (they are not the same thing)

| Field | Type | Who sets it | What it is |
| --- | --- | --- | --- |
| `versionCode` | `Int` | **git commit count**, computed in `app/build.gradle.kts` | The build's true identity. Must strictly increase or the installer/Play Store refuses it. Not semver. |
| `versionName` | `String` | **release-please**, from Conventional Commits | The `1.4.2` semver users see. The one you think of as "the version". |

Both are derived; neither is edited by hand.

## Writing commits (this is the part that requires discipline)

Every commit subject must be a [Conventional Commit](https://www.conventionalcommits.org):

```
<type>[optional scope][!]: <description>
```

- `feat: …`  → next release bumps the **minor** (1.0.0 → 1.1.0)
- `fix: …`   → next release bumps the **patch** (1.0.0 → 1.0.1)
- `feat!: …` or a `BREAKING CHANGE:` footer → bumps the **major** (1.0.0 → 2.0.0)
- `docs / style / refactor / perf / test / build / ci / chore` → no version bump, but `chore`/`docs` etc. still show in history

A committed hook (`.githooks/commit-msg`) rejects messages that don't match, so a
bad message can't sneak in. **Activate it once after cloning:**

```bash
git config core.hooksPath .githooks
```

(It's plain shell — no husky/Node. Bypass in an emergency with `git commit --no-verify`.)

The same setting turns on `.githooks/pre-push`, which prints what the branch still
owes the translation gate before you push. It is **advisory and cannot fail a push**:
completeness is a merge boundary, not a work boundary, and a branch mid-translation is
ordinary. It exists only so you hear it in a second rather than
from CI four minutes later. Silent when there is nothing outstanding.

## How a release happens

1. You push normal Conventional Commits to `main`.
2. The **Release Please** GitHub Action keeps a PR open titled like
   `chore(main): release 1.1.0`. That PR bumps `versionName` and updates
   `CHANGELOG.md` — the changelog is generated from your commit subjects.
3. When you want to cut the release, **merge that PR**. release-please then tags
   the repo (`v1.1.0`) and creates a GitHub Release. Merge whenever you like;
   nothing ships until you do.

Config lives in `release-please-config.json` + `.release-please-manifest.json`
(the manifest holds the current version — release-please rewrites it).

### Merge pull requests with **rebase**, never a merge commit

The repo allows rebase merging only, and that setting is load-bearing for the
changelog rather than a matter of taste.

GitHub writes the PR title into a merge commit's *body*. `conventional-commits-parser`
strips the `Merge pull request #N from …` header and parses what follows as the
commit — so a PR titled `feat: …` whose branch also carries that `feat: …` commit
is counted **twice**, and the release notes list the feature twice. That is exactly
what 1.1.0's first draft did, for all five of its features; the four `fix:` entries
escaped only because those PR titles happened to be `chore:` or plain prose, which
is luck, not a rule.

Rebase replays the branch commits onto `main` with no merge commit in between, so
every conventional subject is counted exactly once and each commit keeps its own
changelog line. Squash would also de-duplicate, but it folds a PR's individual
subjects into a single entry taken from the PR title — and this repo writes a
meaningful subject per commit (PR #72 alone contributed three separate `fix:`
lines), so squashing would throw away detail the changelog exists to carry.

There is no release-please option for this. The merge strategy *is* the fix, which
is why it is enforced by the repo setting instead of by remembering.

## Release notes are a merge gate, not an afterthought

`scripts/notes-gate.py` runs in CI on every pull request, beside the schema and translation gates. It
asserts one thing: the newest `### x.y.z` under `## Release notes` in
[`store-listing.md`](store-listing.md) is the `versionName` about to ship.

It exists because `play-metadata.py` uploads **the newest notes it finds** and nothing else consults
them. Bump `versionName` without moving the notes and the previous release's text goes up attached to
the new build, with nothing to notice it. That is how **1.9.0 reached production describing 1.8.0** on
2026-08-26 — a note predating the timeline, multi-photo trays, kilogram entry and the light/dark
override. ⚠️ **Play does not allow release notes to be edited on a live release**, so the correction
could not be made where it was needed; it waited for the next upload.

The gate is invisible on ordinary branches — `versionName` is still the last released version and the
notes already match. It fails on **release-please's PR**, which is the one moment the two are allowed
to disagree and the last moment it is free to fix.

**When nothing owner-visible changed, satisfying it is a rename, not a rewrite.** Move the heading to
the new version and say why the bodies stand unchanged; 1.8.0 is the worked example. The gate reads
the heading, so "these notes still hold" stays a decision someone made rather than the default.

```bash
python3 scripts/notes-gate.py            # the gate itself
python3 scripts/notes-gate.py --report   # what does this branch owe?
```

It also checks what the notes must satisfy to be usable at all: a note for every locale the AAB
carries, and every one inside Play's 500 characters.

## Checking the artifact before it reaches Play

`bundleRelease`, never `assembleRelease` — Play wants an AAB and an AAB can't be
`adb install`ed, so the only build ever put on the phone is the one Play delivers.
Then read the version fields back **out of the artifact**, not out of the config
that was supposed to produce it:

```bash
./gradlew bundleRelease
python3 scripts/aab-version.py        # versionCode/versionName vs. git
python3 scripts/aab-permissions.py    # the <uses-permission> set, vs. an allowlist
python3 scripts/aab-locale.py         # every string of every shipped locale, vs. the resource table
python3 scripts/aab-reflection.py     # the classes only the manifest names, vs. what R8 left in the dex
keytool -printcert -jarfile app/build/outputs/bundle/release/app-release.aab
```

All four scripts **exit non-zero** rather than printing and leaving you to read.
Each exists because the corresponding claim was once wrong in an artifact while
every source-side check was green: `versionCode` 1 on a signed bundle (3a), Polish
missing from the build that went up (fixed in 1.0.1), a permission set that had
quietly grown from two to six (found at 4h), and R8 shrinking away the no-arg
constructor of a class only the manifest names, which disabled the guided document
scanner without raising anything (10c). The pattern is the same every time — the
config said one thing, the artifact said another, and nothing compared them.

`aab-reflection.py` is the newest and the one whose failure is quietest, because
its subject never crashes: a class discovered by `Class.forName` and built with a
no-arg constructor just isn't there, and the framework that wanted it carries on
without it. It reads the classes to check **out of the manifest** — every
`<meta-data>` whose value marks one — rather than from a list that would go stale,
and looks each up in the dex. `aab-permissions.py` does the other half of the
same job: it asserts no `android:screenOrientation` survives into the artifact, so
a dependency bump cannot quietly re-lock the screen. (A library AAR pinning its own
delegate activity to portrait is a real Play policy finding, and it is invisible in
your own source.)

Don't reach for `aapt2 dump xmltree` here. An AAB stores its manifest as
**protobuf**, not the binary XML aapt2 reads, so it prints nothing and exits `0` —
it doesn't fail, it just declines to answer. That silence is how a release
produced a *signed* bundle carrying `versionCode` 1 and didn't find out until
later. `scripts/aab-version.py` decodes the protobuf and asserts the count matches
`git rev-list --count HEAD`.

## Reaching Play automatically (internal testing)

`.github/workflows/publish-play.yml` builds and uploads to the **internal testing** track
when a **GitHub Release is published** — that is, when you merge the release-please PR.
Nothing uploads on a bare push to `main`, so cutting a version is still a deliberate act;
this only removes the hand-build that used to follow it.

What the workflow does, in order: full checkout (`fetch-depth: 0`, because `versionCode`
is the commit count), materialise the upload key from secrets, `bundleRelease`, run all
four `aab-*.py` artifact checks, print the signing certificate, upload the AAB **and its
R8 mapping**, keep both as a build artifact for 90 days, delete the key.

The mapping matters from 1.9.0: R8 is on, so without it every Play crash report is
obfuscated frames.

### The five secrets this workflow needs

Four for the upload key, one for Play. `RELEASE_PLEASE_TOKEN` is a sixth, needed
earlier and by a different workflow — see *Setting up a new repository*. Set them under *Settings → Secrets and variables →
Actions*:

| Secret | What it is |
| --- | --- |
| `UPLOAD_KEYSTORE_BASE64` | the keystore file itself, base64: `base64 -w0 /path/to/upload.jks` |
| `UPLOAD_STORE_PASSWORD` | same value as `upload.storePassword` in `local.properties` |
| `UPLOAD_KEY_ALIAS` | same value as `upload.keyAlias` |
| `UPLOAD_KEY_PASSWORD` | same value as `upload.keyPassword` |
| `PLAY_SERVICE_ACCOUNT_JSON` | the whole service-account JSON, pasted as-is |

⚠️ **The keystore is still never committed** — this changes where a copy *lives*, not the
rule. The one on disk stays outside the repo (ADR-0005); base64 in a GitHub secret is a
second copy, and losing control of it means resetting the upload key. That is recoverable
(Google holds the permanent app-signing key) but it is not free.

### Creating the service account — the part that is not in this repo

Once, by hand, and it is the only step CI cannot do for itself:

1. Google Cloud console → the project linked to your Play developer account → **enable the
   Google Play Android Developer API**.
2. **IAM & Admin → Service Accounts → Create**. No project roles are needed; its authority
   comes from Play, not from GCP.
3. On that account, **Keys → Add key → JSON**. The file downloads once — that is the
   `PLAY_SERVICE_ACCOUNT_JSON` value.
4. Play Console → **Users and permissions → Invite new user**, the service account's email.
   Grant it **Release to testing tracks** on this app (your `applicationId`)
   and nothing wider. It does not need production rights to do this job.

Propagation between Play and the API is not instant — a permission granted in the Console
can take a few minutes to be visible to the API, so a first run that 401s is worth simply
re-running before debugging it.

### Why internal, and what it does not prove

Internal processes in minutes with no Google review, which is what makes it a sane
automatic target. ⚠️ **It is not the track for an upgrade proof.** An internal-track
install demands an uninstall on the device where a closed-track one updates in place, so a
build that arrives this way cannot stand in for "an existing owner's install survived the
update". Promoting to closed or production stays a Console decision, made by a human.

## Going to production (manual, gated, staged)

`.github/workflows/publish-play-production.yml` — **Run workflow**, never automatic. It is the only
path that can reach every owner, so it carries three independent brakes:

1. **You trigger it.** `workflow_dispatch` only; no push, tag or schedule reaches it.
2. **You approve it.** The job declares `environment: production`. ⚠️ **Add yourself as the sole
   required reviewer on that environment in repo settings** — without a reviewer configured the
   environment is just a label and gates nothing.
3. **Staged rollout.** `rollout` defaults to `0.1`, so a bad build reaches a tenth of installs and
   you widen from the Console once it looks clean.

And a fourth for the first run: **`dry_run` defaults to true**, which passes `--validate_only` —
Play validates the whole edit and discards it. Nothing publishes, nothing is sent for review. Untick
it when you mean it.

### It promotes; it does not build

The artifact that reaches production is the **exact one `publish-play.yml` already put on the
internal track** — same bytes, same signature, the copy you actually tested. This workflow never
runs `bundleRelease` and never materialises the upload key, because it has nothing to sign.

Rebuilding here was the original shape and it could not have worked. `versionCode` is the commit
count, so rebuilding a released tag reproduces a code Play has already accepted on internal, and
Play refuses a **new upload** of a versionCode it has seen:

```
[!] Google Api Error: Invalid request - Version code 423 has already been used.
```

Two tracks *sharing* a versionCode is not the problem — that is precisely what promotion produces,
and it is why promoting by hand in the Console never hit this. The refusal is about uploading the
same code twice. `--skip_upload_aab` / `--skip_upload_apk` are what turn the supply call into a
promotion: it moves the release already sitting on `from_track` instead of looking for a binary.

| Input | Default | What it does |
| --- | --- | --- |
| `track` | `production` | destination — also `beta` / `alpha` |
| `from_track` | `internal` | source track holding the build being promoted |
| `rollout` | `0.1` | fraction of users; `1.0` is everyone |
| `version_code` | *(blank)* | which build to promote; blank asks Play what is on `from_track` |
| `update_listing` | `false` | push descriptions + screenshots as well |
| `dry_run` | `true` | validate against Play, commit nothing |

**The versionCode comes from Play, not from git.** Every other workflow derives it from the commit
count, and doing that here is wrong in a way that looks right: the count describes the *checkout*,
while a promotion is about a build uploaded earlier. They agree only while `main` still points at the
release tag, and stop agreeing the moment anything else merges — which is a normal state to be in and
produces `Track 'internal' doesn't have any releases`, an error about the version filter that reads
like an error about the track. So the workflow asks the source track what it is holding. Any ref
works, and there is no dialog field to get right.

⚠️ A **halted** release is not promotable — Play hides the Promote button and the API will not
report it. Resume it in the Console first.

### One edit, one review

The bundle, the release notes and — when `update_listing` is on — the descriptions and screenshots
all go up in a **single** `supply` invocation, which is a single Play edit. Play reviews an *edit*,
not a field, so that is **one** review cycle. Uploading the build now and fixing the listing after is
two edits, two reviews and two waits.

Release notes always accompany the build; they are scoped to a version and mean nothing without it.
`update_listing` governs only the descriptions, screenshots and graphics.

### Why fastlane here and Python everywhere else

`scripts/play-metadata.py` renders `docs/store-listing.md` into the tree `supply` expects, at run
time, and it is gitignored — the markdown stays the only authored copy, so a listing change is still
one reviewable diff. What `supply` is bought for is one specific transaction: replacing a listing's
screenshots means **deleting the old set before uploading the new one**, and first-time code that
dies between those steps leaves the public listing with no screenshots at all. That is worth someone
else's mileage. Ruby is confined to this workflow; the internal-track one never loads the `Gemfile`.

⚠️ **Changelog files are named by `versionCode`, not semver** — `409.txt`, not `1.9.0.txt`. supply
keys notes to the build, and a name Play cannot match is ignored in silence rather than rejected.

## Setting up a new repository (once)

**None of this is inherited.** GitHub's template mechanism copies files and nothing else: no
rulesets, no branch protection, no secrets, no Pages setting, no merge-strategy preference. A repo
created from the template starts with `main` wide open and every item below undone — and the build
stays green throughout, so nothing tells you. The first symptom is a release PR that never appears,
which reads like a broken template rather than an unconfigured repository.

Most of it is one command:

```bash
python3 scripts/repo-setup.py --dry-run   # what it would change, and what is already right
python3 scripts/repo-setup.py             # do it
```

It creates the `main: require CI` ruleset with the right check names, sets rebase-only merging,
enables Pages from `docs/`, and reports which secrets are still missing. It is idempotent — run it
again after any manual change and it reports what is already correct rather than fighting you. It
verifies the required check names against `ci.yml` first, because a required check that CI never
publishes leaves every PR stuck at *"Expected — waiting for status to be reported"* with no way out
but deleting the ruleset.

**The one step it cannot do is the token.** GitHub has no API for minting a personal access token,
so do this by hand, first:

1. https://github.com/settings/personal-access-tokens/new — fine-grained, *Only select
   repositories* → this one, and exactly two permissions: **Contents: read and write**,
   **Pull requests: read and write**. (`Metadata: read-only` is added automatically; leave it.)
   The token's *name* is an account-unique label of your choosing and has nothing to do with the
   secret name — reuse across repos is impossible, so name it for the repo it serves.
2. `gh secret set RELEASE_PLEASE_TOKEN --repo <owner>/<repo>` and paste the value.

Without it `release-please.yml` fails in about seven seconds with `Input required and not supplied:
token`, and no release PR is ever opened.

What the script sets, and why each one matters, is in the sections above: **rebase-only merging**
(*Merge pull requests with rebase*), **the `main` ruleset** — no bypass actors, requiring both CI
contexts, and note how it interacts with the token, since a release PR opened by `GITHUB_TOKEN`
gets zero CI jobs and this rule then blocks its merge permanently — and **Pages**, because Play
demands a *hosted* privacy-policy URL and an app with no backend has no server of its own.

The **five Play secrets** (table above) are the exception: wanted at the first upload, not before.

### The template repository does not version itself

`release-please.yml` carries `if: github.event.repository.is_template != true`. The template ships
no app, so a release PR on it bumps a `versionName` nothing consumes and then fails the notes gate —
correctly, since that gate demands Play release notes for a version that will never reach Play.

**A repo generated from the template is not itself a template**, so the condition is false there and
release-please runs in full: release PR, `CHANGELOG.md`, the `versionName` bump, the tag, the GitHub
Release and the Play upload. Nothing is disabled downstream, and there is nothing for `bootstrap.py`
to rewrite.

## Gotchas

- **`versionCode` in CI debug builds is `1`.** GitHub's checkout is shallow, so the
  commit count can't be read. That's fine for debug. For a *release* build, do a full
  checkout (`fetch-depth: 0`) or build locally so the count is real.
- **The release workflow needs a `RELEASE_PLEASE_TOKEN` secret** — a fine-grained PAT
  with *contents: write* and *pull-requests: write* on this repo. The built-in
  `GITHUB_TOKEN` can't be used: GitHub won't run workflows on a PR that `GITHUB_TOKEN`
  opened, so the release PR's CI sits at `action_required` with zero jobs, and the
  `main: require CI` ruleset (no bypass actors) then blocks the merge forever. If the
  secret is missing or expired, the workflow fails and no release PR appears at all.
- **We start at `0.1.0`** on purpose — an app is pre-1.0 until you decide it is not.
  While the major is `0`, release-please stays in pre-release: `fix:` → `0.1.1`,
  `feat:` → `0.2.0`, and even a breaking `feat!:` bumps the *minor* (`0.2.0`), it
  does **not** auto-jump to `1.0.0`.
- **Cutting `1.0.0`** is a deliberate act: put a footer in a commit body —

  ```
  feat: the last thing 1.0 was waiting on

  Release-As: 1.0.0
  ```

  — and the next release PR targets `1.0.0`.
