// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.compose.compiler) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.spotless)
}

// Compose-specific ktlint tweaks. Passed via editorConfigOverride rather than .editorconfig
// because Spotless's ktlint step doesn't reliably pick up rule toggles from the file — the
// override map is the documented, dependable path. Everything else (indent, line width) still
// comes from .editorconfig.
val ktlintRules =
    mapOf(
        // @Composable / @Preview functions are PascalCase by convention — don't flag them.
        "ktlint_function_naming_ignore_when_annotated_with" to "Composable,Preview",
        // Don't force single-declaration files to be renamed after the declaration.
        "ktlint_standard_filename" to "disabled",
    )

// Spotless = Prettier's Kotlin equivalent. Applied to every module from the root so
// `./gradlew spotlessApply` (format, like `prettier --write`) and `./gradlew spotlessCheck`
// (verify, for CI) behave identically across all source files.
spotless {
    kotlin {
        target("**/*.kt")
        targetExclude("**/build/**/*.kt")
        ktlint(libs.versions.ktlint.get()).editorConfigOverride(ktlintRules)
    }
    kotlinGradle {
        target("**/*.gradle.kts")
        ktlint(libs.versions.ktlint.get()).editorConfigOverride(ktlintRules)
    }
}
