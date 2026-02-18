// ==========================================================================
// CV Style Configuration
// Change fonts, colors, and spacing here without touching data or structure.
// ==========================================================================

// --- Fonts ----------------------------------------------------------------
// Use Minion Pro explicitly (system-installed).
// Fallbacks: common macOS serif fonts.
#let cv-fonts = ("Minion Pro", "Palatino", "Palatino Linotype", "Times New Roman", "Times")
#let cv-font-size = 10.75pt
#let cv-leading = 0.64em
#let cv-sub-leading = cv-leading

// --- Sizes ----------------------------------------------------------------
#let cv-name-size = 24pt
#let cv-section-size = 14pt
#let cv-subsection-size = 12pt

// --- Colors ---------------------------------------------------------------
#let cv-link-color = rgb("#1a365d")       // dark navy for links
#let cv-rule-color = luma(170)            // light gray for section rules
#let cv-header-color = luma(80)           // page header text (name on pg 2+)
#let cv-footer-color = luma(140)          // page number color

// --- Spacing & Layout -----------------------------------------------------
#let cv-rule-weight = 0.4pt
#let cv-page-margin = (left: 1in, right: 1in, top: 1.1in, bottom: 1in)
#let cv-entry-spacing = 0.9em            // vertical space between CV entries
#let cv-bib-hanging = 1.5em              // hanging indent for bibliography
#let cv-sub-bullet = "–"
#let cv-sub-bullet-gap = 0.4em

// ==========================================================================
// Style Functions (called by cv.typ — modify appearance here)
// ==========================================================================

/// Render a section heading (level 1)
#let section-heading(title) = {
  // Cancel the trailing spacing from the previous entry so the rule
  // is evenly spaced above/below across sections.
  v(-cv-entry-spacing)
  v(0.45em)
  line(length: 100%, stroke: cv-rule-weight + cv-rule-color)
  v(0.45em)
  text(
    size: cv-section-size,
    weight: "semibold",
    tracking: 0.03em,
    smallcaps(title),
  )
  v(0.15em)
}

/// Render a subsection heading (level 2)
#let subsection-heading(title) = {
  v(0.25em)
  text(size: cv-subsection-size, weight: "semibold", title)
  v(0.1em)
}

/// A standard CV entry (positions, education, grants, etc.)
#let cv-entry(body) = {
  block(
    above: cv-entry-spacing,
    below: cv-entry-spacing,
    body,
  )
}

/// A bibliography entry with hanging indent
#let bib-entry(body) = {
  block(
    above: cv-entry-spacing,
    below: cv-entry-spacing,
    par(hanging-indent: cv-bib-hanging, body),
  )
}

/// Indented sub-bullets (used for venues/locations under a main entry)
#let cv-sublist(items) = {
  pad(
    left: 1.6em,
    stack(
      spacing: cv-sub-leading,
      ..items.map(i => grid(
        columns: (auto, 1fr),
        gutter: cv-sub-bullet-gap,
        [#align(top, text(cv-sub-bullet))],
        [#i],
      )),
    ),
  )
}

/// Apply the CV page setup: page geometry, fonts, heading styles, link colors.
/// Call this as a show rule: `#show: cv-page-setup.with("Name")`
#let cv-page-setup(name, body) = {
  set page(
    paper: "us-letter",
    margin: cv-page-margin,
    header: context {
      if counter(page).get().first() > 1 {
        align(right, text(size: 9pt, fill: cv-header-color, style: "italic", name))
      }
    },
    footer: context {
      align(center, text(size: 8pt, fill: cv-footer-color, counter(page).display()))
    },
  )

  set text(font: cv-fonts, size: cv-font-size, lang: "en")
  set par(leading: cv-leading, justify: false)

  // Heading show rules
  show heading.where(level: 1): it => section-heading(it.body)
  show heading.where(level: 2): it => subsection-heading(it.body)

  // Links
  show link: set text(fill: cv-link-color)

  body
}
