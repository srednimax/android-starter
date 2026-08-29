# R8 rules for the release build.
#
# It deliberately contains **no keep rules**, and that is a finding rather than an omission. Every
# reflection-shaped thing in this app is already covered by a rule that some library ships, and the
# evidence is in the build's own output rather than in a habit:
#
#   app/build/outputs/mapping/release/configuration.txt   every rule R8 actually ran with
#   app/build/outputs/mapping/release/mapping.txt         what was renamed, and to what
#   app/build/outputs/mapping/release/usage.txt           what was removed
#
# What was checked here, and what covers it:
#
#   * **The manifest's classes.** AGP generates `aapt_rules.txt` from the merged manifest, which
#     covers the application, the activity, every receiver and provider — and `android:backupAgent`,
#     so `AppBackupAgent` is kept without a rule here. Worth confirming rather than assuming: its
#     failure mode is a backup that silently does nothing.
#
#   * **Workers, across versions.** `androidx.work` ships `-keepnames class * extends
#     androidx.work.ListenableWorker`, which is the rule that matters most: WorkManager persists the
#     worker's *class name* in its own database, so a sweep enqueued by 1.0 must still resolve after
#     the update to 1.1. `-keepnames` is what makes the name stable release to release.
#
#   * **Room.** `-keep class * extends androidx.room.RoomDatabase` plus R8's own handling of the
#     `Class.forName(… + "_Impl")` lookup. `AppDatabase_Impl` stays unrenamed. The DAOs are renamed,
#     which is fine — nothing looks them up by name.
#
#   * **kotlinx.serialization** — the backup manifest and every Nav3 route key. The library ships R8
#     rules preserving the `Companion` field and the `serializer()` method, which is the reflective
#     path `serializer(KClass)` takes. Renaming the *classes* is harmless: a `@Serializable` class's
#     `serialName` is a string literal baked in at compile time, so the JSON in a user's archive does
#     not change shape when R8 renames the class that reads it.
#
#   * **Enums stored by name** — the house rule, and the one that could silently rewrite history.
#     R8 renames the constant *fields* but never the name string handed to the enum constructor,
#     because `Enum.valueOf` reads it; `.name` is therefore unchanged. **No rule can pin this**: the
#     usual `-keepclassmembers enum *` keeps field *names*, which is not what `.name` returns. It is
#     a property of how R8 works, so prove it by behaviour on the phone as well as by grepping the
#     compiled dex for the constants themselves.
#
# ---------------------------------------------------------------------------
# The rule to follow when this file changes
# ---------------------------------------------------------------------------
#
# **Add a keep only with the mapping or usage output that shows something was renamed or removed.**
# A rule added on suspicion can never be removed later, because nobody can prove it was doing
# nothing — and a keep file accumulated that way is why so many apps ship almost unminified.
#
# The failure to expect from a *missing* rule is not a crash. It is a feature that silently stops
# working: an exception caught by a fallback path, a reflective lookup returning null and the code
# taking the other branch. Test the release build on a device, not just the debug one.
#
# `./gradlew assembleDebug -PreleaseShapedDebug` builds the debug variant through R8 with these
# rules, keeping the debug applicationId — which is how you find this out before uploading.
