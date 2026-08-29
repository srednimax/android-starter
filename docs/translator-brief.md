# Translator brief

Hand this to whoever translates the app — including yourself with a machine translator, which is a
legitimate first pass and never a last one.

**Sections 1 and 2 are yours to write** for this app. Everything from section 3 on is craft that
transfers between apps unchanged, and is the reason this file is worth having rather than a one-line
"please translate `strings.xml`".

Translate from **English only**, never from another translation: every interpretation the first
translator made gets compounded, silently.

## 1. What the app is, in one paragraph

<Write this. A translator who does not know what the app is *for* will produce fluent sentences that
are wrong about the thing. Say who uses it and in what situation — copy for someone worried at 2am
reads differently from copy for a productivity tool.>

## 2. The rules that outrank fluency

<Write these. They are the promises the copy makes that a translator must not soften, sharpen, or
"improve". Number them, and say what each one protects — a translator will follow a rule they
understand the reason for and will helpfully fix one they do not. Shapes that recur:

- *Never state something the app does not know.* Where a value is absent because nobody entered it,
  the copy says so — it does not say everything is fine.
- *The app observes; it never advises.* A verb that becomes an imperative in translation changes what
  the app claims to be, and in some domains that is a regulatory question rather than a stylistic one.
- *A unit that is always shown one way stays that way*, however unnatural it reads, because the whole
  point is that a small change stays visible.>

## 3. Register

Decide it once and write it down, because it is the thing a translator most needs told and most
often guesses.

- **Who the app addresses, and how formally.** Many languages force a choice English does not: `du`
  or `Sie`, `ty` or `Pan/Pani`, `tu` or `vous`. Pick one and hold it across every string.
- **Whether the app speaks as "we" or is invisible.** "We couldn't save that" and "That couldn't be
  saved" are different products.
- **Sentence case or title case** in buttons and headings. English tolerates both; most languages do
  not use title case at all, so a translated title-cased heading reads as a mistake.

## 4. Do not translate

Three kinds of string, marked `translatable="false"` in `strings.xml` so lint and the gate leave
them alone. If you find yourself wanting to translate one, that is worth a conversation rather than
an edit.

- **The app's own name.**
- **Language names in the switcher.** They are **endonyms** — each language named *in its own
  language*, in every locale — so someone who has landed in a language they cannot read can find
  their way out by a name they recognise. `settings_language_english` reads "English" in every file.
- **Brand names, and anything with a legal identity.** A product name that is the same in every
  market stays the same; translating it invents a different product.

### Things that look untranslatable and are not

- **Unit symbols.** SI symbols look invariant and are not: spacing, the decimal separator, and
  sometimes the symbol itself change by locale. Keep them in resources.
- **Numbers inside sentences.** Grouping and decimal separators are locale-specific. Never build a
  number into a string by hand.
- **Dates and times.** Format them through the platform, never by concatenating a resource.
- **Sample and debug data.** Not resources at all — they live in `src/debug/` and never ship.

## 5. Vocabulary

Keep a table here of **every English word that appears more than once**, with the target word for
each context. This is the single highest-value section of the file.

The trap it exists for: **one English word is often several target words.** English *Normal* covers
six different nouns in six different genders; a translator working string-by-string will produce a
different form each time, all of them defensible, and the app will look sloppy in a way no test
catches. Likewise *Name*: a person's given name and an organisation's name are different words in
most languages.

| English | Resource ids | Why they differ | Example |
| --- | --- | --- | --- |
| | | | |

Words that genuinely *are* one word everywhere — *Settings*, *Close*, *Edit*, *Delete* — belong in
the same table with a note saying so, otherwise someone will vary them for variety.

## 6. Traps

### 6.1 A substituted fragment has to fit its sentence

English composes freely because it barely inflects. `"in the last %1$s"` with `"30 days"` works;
the same substitution in an inflecting language needs the fragment in the right case, and the case
depends on the host sentence.

**Pre-inflect the fragment for its host, and say in a comment which host it belongs to.** If one
fragment is used by two hosts that need different cases, it needs to become two resources — that is a
code change, and it is cheaper to find now than after the translation.

### 6.2 The app knows nobody's gender

Not the user's, not the subject's, not any third party's. English hides this behind *they* and *you*.
Most other languages do not, and a translator forced to choose will pick one, producing copy that is
wrong for half the users and reads as an apology to the rest.

**Every string with a human doing something in it needs checking**, and the fix is usually to rewrite
the *English* into a form that does not need a gender — a noun phrase instead of a verb with a
subject. That is a change to the base language, made once, rather than a workaround in eight files.

### 6.3 Names the app cannot touch

Anything the user typed — a name, a label, a note — is substituted verbatim into a sentence. It
cannot be inflected, so the sentence has to be built so that it does not need to be. Watch for
possessives and for any preposition that would govern a case.

### 6.4 Plurals

**A count-dependent string is a `<plurals>`, never string concatenation, and never `if (n == 1)`.**

Which categories a language uses is **CLDR's** decision, not the translator's. English has `one` and
`other`; Polish has `one`, `few`, `many` and `other`; Arabic has six. Supplying only the English pair
in a language that needs four is a silently wrong app — `TranslationTest` fails the build on it,
which is the whole reason that test exists.

`%d` is not always the right placeholder either: some categories in some languages read better
without the number, and `quantity="one"` in Polish means *exactly* one, not "the singular".

### 6.5 Format arguments

- **Positional (`%1$s`), never bare (`%s`), whenever there is more than one.** Word order changes; a
  translator must be able to reorder the arguments, and bare placeholders make that impossible.
- **The same arguments must appear in every locale.** A missing one crashes at format time, on a
  screen you did not test in that language. `TranslationTest` checks this continuously.
- **A literal `%` must be escaped as `%%`.**

## 7. What happens to your draft

1. It goes into `res/values-<tag>/strings.xml`, or — while it is still a draft — into
   `translations/<tag>/` one directory up, which is staged and reported but **never shipped**.
2. `TranslationTest` checks it mechanically: format arguments, plural categories, orphans,
   untranslatable resources, array lengths. This runs on every build.
3. `scripts/translation-gate.py` checks it is *complete*, and that nothing has gone **stale** — the
   English changed and the translation did not. A stale translation is invisible to every other
   check: it parses, it carries its arguments, and it says something the app no longer means.
4. The language is offered to users only when its tag is added to `res/xml/locales_config.xml` and
   `AppLanguage`. Until then it exists and reaches nobody, which is the correct state for a draft.
