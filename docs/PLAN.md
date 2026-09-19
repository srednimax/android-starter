# Roadmap

Sequence and status only. The reasoning behind a decision lives in [`docs/adr/`](adr/); the words
live in [`CONTEXT.md`](../CONTEXT.md); commands, layout and house rules live in
[`CLAUDE.md`](../CLAUDE.md).

**This file is the record, not the worklist.** What is still open — the boxes to tick, with the
device state and the commands to read it — lives in [`DOD.md`](DOD.md), which stays short enough to
open every session. Read the phase you are in here; read `DOD.md` to know what to do next.

**A phase being planned or built gets its own file** — `phase-N.md` beside this one — so working on
it costs the phase rather than the whole history. This file stays deliberately thin: one paragraph
per phase, no task lists. The detail is written when the phase opens, not now. The app this template
was extracted from and the first app built from it settled on exactly this split independently.

<!--
    A skeleton. Replace the phases with yours; keep the three rules at the bottom unless you have a
    reason, because each of them was paid for by an app built from this template.
-->

## Status

- [ ] **Phase 0** — Skeleton: the placeholder domain gone, the palette and the mark chosen
- [ ] **Phase P** — The pipeline: repository setup, upload key, Play entry, secrets, a green internal upload
- [ ] **Phase 1** — *(the smallest version of the app's one mechanism, working on the phone)*
- [ ] **Phase 2** — *(safe to hand to a stranger)* ← **the door: closed testing opens here**
- [ ] **Phase N** — Ship shape: listing, screenshots, the App content answers

---

## Rules that cut across every phase

### 1. Decide where the door is, early

**The door** is the first build a stranger installs — closed testing, for a new personal Play
account. Everything that reaches a tester's phone is harder to change afterwards: a stored key, a
permission, a `minSdk`, the `applicationId`. So name the phase the door sits after, and write down what
it freezes. The closed-test window is calendar time and other people's replies, so later phases can
run while it waits.

### 2. When the two halves of a phase cost wildly different amounts, they are two phases

The first app built from this template split every one of its middle phases along cost or along
kind, because in each case a bundle of a cheap item with an expensive one — or a feature with the
safety work it depends on — hid which half was blocking. However neatly one sentence describes both, two costs are two phases.

### 3. A phase proves itself on the phone, not in a test

Every phase ends with readings taken off a real device and written into its `phase-N.md`, with the
command that produced them. A green test run says the code does what the test asked; the phone says
what the ROM allowed. Vendor ROMs are where those two part company.

---

## Phase 0 — Skeleton

*(one paragraph)*

## Phase P — The pipeline

*(one paragraph — `DOD.md`'s "Before the first upload" is most of it)*

## Not in this plan

*(what the app will deliberately never do, so a phase cannot quietly grow it back)*
