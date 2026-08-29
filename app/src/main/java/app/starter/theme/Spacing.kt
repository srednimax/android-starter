package app.starter.theme

import androidx.compose.ui.unit.dp

/**
 * The six spacing steps, on a 4dp grid. No screen invents a seventh.
 *
 * A plain object rather than a CompositionLocal: these never vary by theme, by screen or by
 * device, so threading them through composition would buy nothing and cost a lookup at every call
 * site. Import and use directly.
 *
 * **The rhythm rule:** a section header sits [tight] (8dp) from its own content and [section]
 * (24dp) from whatever came before it. That 1:3 ratio is what makes a header read as attached
 * downward and detached upward. It is the most commonly broken thing in a hand-spaced UI — using
 * the same value above and below leaves the header floating between two sections, belonging to
 * neither.
 */
object Spacing {
    /** 4dp — within one thought: a value and its timestamp. */
    val hair = 4.dp

    /** 8dp — header to its content. Sibling cards in a list. Buttons in a row. */
    val tight = 8.dp

    /** 12dp — paragraphs inside a card. */
    val snug = 12.dp

    /** 16dp — screen edge. Card padding. */
    val base = 16.dp

    /** 24dp — end of a section to the next section's header. */
    val section = 24.dp

    /** 32dp — hero to the first section. Use it twice in an app, not twenty times. */
    val block = 32.dp
}
