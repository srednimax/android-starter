# Phase N — *(what is true when it closes, in words a user would recognise)*

<!--
    The shape of a `phase-N.md`. Copy it to `phase-N.md` the day the phase opens, not before
    (PLAN.md), and delete every comment as its section fills in. It is the shape the first app built
    from this template arrived at over six phases rather than one it was handed: every section below
    is here because a phase without it went wrong in a way the section would have caught.

    Long on purpose. A phase file is written before the code, argued in full once, and then read one
    section at a time while building. The waste to avoid is re-deriving a decision mid-build, not
    words on this page.
-->

Sequence lives in [`PLAN.md`](PLAN.md); the live worklist lives in [`DOD.md`](DOD.md). *(Name the
ADRs this phase relies on or reopens, and what [`CONTEXT.md`](../CONTEXT.md) is owed — a new term, or
"nothing, and why".)*

**What closing this phase means.** *(One paragraph: the app as it is today, the app after this phase,
and the difference stated as something a device can be asked about.)*

*(If `PLAN.md`'s paragraph for this phase is already wrong — an item shipped early, one turned out to
be something else — say so here, first. Planning a phase is when that is found.)*

---

## 0. What this phase inherits

*(What earlier phases left that this one leans on or has to work around: a mechanism, a device
finding, a promise already made in copy or in the listing. The asymmetry that shapes the phase usually
lives here — "this ask can be read back and that one cannot", "this path is covered by a test and that
one only by the phone".)*

## What is in, and what is deliberately not

**In:** *(one paragraph.)*

**Not in, and each with a reason rather than a phase:**

- *(Item.)* *(Why it is out: a refusal, a dependency on something outside this phase, or cost against
  what it buys. "Later" is not a reason.)*

*(The tempting one — the item that looks like a free upgrade — gets its own paragraph, because it is
the one a later session will try to add back.)*

---

## Checkpoints

*(Each checkpoint leaves the app working, and ships its copy complete in every shipped language —
`scripts/translation-gate.py` enforces that at merge. The commit type column is what release-please
reads, so it decides whether this phase cuts a release at all.)*

| | Checkpoint | Merges | Depends on |
| --- | --- | --- | --- |
| **A** | **The gate** — *(the one question that could veto the rest)* | *(often no commit: the verdict is a reading)* | — |
| **B** | *(…)* | `feat:` | A |

*(A paragraph per non-obvious ordering. **Put the gate first** — a gate taken after the work answers the
same question a week later, with that week's work already written on a bet. If two halves of a
checkpoint cost wildly different amounts, they are two checkpoints — `PLAN.md` rule 2 applies here
too.)*

---

## 1. The gate: *(the question)*

*(Only if the phase has something that could veto it — a platform behaviour nobody has measured, a
pipeline path never exercised. Most phases worth a file have one.)*

### The question, in the form that can be measured

*(Not "does scheduling work" but "does an inexact alarm start a foreground service at 22:00 with the
app swiped away, on this ROM". A question that cannot be answered by a command is not a gate yet.)*

### The apparatus

*(What takes the reading, and where it lives — developer-only surface goes under `app/src/debug/`,
never behind `BuildConfig.DEBUG` in `main/`.)*

### The verdicts, decided now rather than argued about later

*(Two or three outcomes, and what the phase does under each — **written before the reading is taken**.
Deciding after is how a bad result gets argued into a good one.)*

1. *(Outcome.)* → *(what happens.)*
2. *(Outcome.)* → *(what happens.)*

### The verdict, taken *(date)*

*(Which one, the reading behind it, and anything it found that neither verdict anticipated.)*

## 2. *(A section per piece of work)*

*(The shape, the rule it follows, the call sites, and what the user sees. A table for anything a
reader would otherwise have to re-derive — a state crossed with a moment, an ask crossed with its
phase (`PLAN.md` rule 4). The copy, in English, at the end of the section it belongs to.)*

---

## Tests

*(`PLAN.md` rule 3's second clause: a pure function that computes or bounds a safety value gets its
test in the phase that introduces it. Name each one and the direction it fails in. Device behaviour is
not listed here; it is a reading.)*

## Documents this phase amends

*(ADRs, `CONTEXT.md`, the privacy policy, the listing, `docs/play-app-content.md`. A phase that adds a
permission, a stored key or a new surface owes at least one of them, and the pipeline will not notice.)*

## Known gaps, deliberately

- *(A gap, why it is accepted, and what closing it would cost. Named here so a reader does not have to
  find the ADR to learn it.)*

## Readings

`PLAN.md` rule 3: filled in as the phase runs, from the device, with the command that read it — not
"it looked right". Derivations are proven by a test, not recorded here.

*(Name the device state a reading depends on and how it is set — a screen timeout, an autostart grant
that lapses, a battery exemption. `CLAUDE.md`'s environment notes list the readings that look like a
pass and are nothing at all.)*

| # | Reading | Command | Result |
| --- | --- | --- | --- |
| R1 | *(what is being asked)* | *(the exact command)* | **(what it said)** *(date)* |

*(A reading that could not be taken says so, with why and what answered the question instead. A
reading struck because it was the wrong question is struck here, not deleted.)*
