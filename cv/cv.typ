// ==========================================================================
// CV Glue File
// Controls section ordering, filtering rules, and data → display mapping.
// Data lives in data/; visual style lives in style.typ.
//
// Build:  python3 build.py              (full CV)
//         python3 build.py --years 5    (last 5 years)
// ==========================================================================

#import "style.typ": *

// --- Load data ------------------------------------------------------------
#let personal = yaml("data/personal.yml")
#let data = json("_generated/cv-data.json")

// --- Year filter ----------------------------------------------------------
// Pass --input years=5 via Typst (the build.py script handles this).
#let years-param = sys.inputs.at("years", default: none)
#let current-year = datetime.today().year()
#let cutoff-year = if years-param != none { current-year - int(years-param) } else { 0 }

// Helper: should an item be included given its year?
// Items with no year or year >= cutoff are included.
#let include-by-year(year-str) = {
  if year-str == "" or year-str == none { return true }
  let y = int(year-str)
  y >= cutoff-year
}

// Helper: should a position/role be included?
// Include if it's current (no end year) or overlaps the cutoff window.
#let include-by-range(start-str, end-str) = {
  if cutoff-year == 0 { return true }
  if end-str == "" or end-str == none { return true }  // current role
  int(end-str) >= cutoff-year
}

// Punctuation helpers (strings only; avoids double periods or ".?")
#let ends-punct(s) = s.ends-with(".") or s.ends-with("?") or s.ends-with("!") or s.ends-with("–") or s.ends-with("-")
#let with-period(s) = if ends-punct(s) { s } else { s + "." }
#let period-if-needed(s) = if ends-punct(s) { "" } else { "." }
#let join-sentences(items) = {
  let cleaned = items.filter(i => i != "" and i != none)
  cleaned.map(i => with-period(i)).join(" ")
}
#let format-year-range(start, end) = {
  if end == "" or end == none { start + "–" } else { start + "–" + end }
}

// ==========================================================================
// PAGE SETUP
// ==========================================================================
#show: cv-page-setup.with(personal.name)

// ==========================================================================
// HEADER
// ==========================================================================
#text(size: cv-name-size, weight: "regular", personal.name)
#v(0.3em)

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  [
    #link(personal.affiliation_url)[#personal.affiliation] \
    #link(personal.university_url)[#personal.university] \
    #personal.address \
    #personal.city
  ],
  [
    Email: #link("mailto:" + personal.email)[#raw(personal.email, lang: none)] \
    Web: #link(personal.web)[#raw(personal.web, lang: none)]
  ],
)

#v(0.5em)

// ==========================================================================
// ACADEMIC POSITIONS
// ==========================================================================
#v(0.35em)
= Academic Positions

#for p in data.positions {
  let year-range = format-year-range(p.start_year, p.end_year)
  let dept = if p.department != "" { ", " + p.department } else { "" }
  let entry-text = join-sentences((p.title + dept, p.institution, year-range))
  cv-entry[#entry-text]
}

// ==========================================================================
// EDUCATION
// ==========================================================================
= Education

#for e in data.education {
  let year-range = format-year-range(e.start_year, e.end_year)
  let entry-text = join-sentences((e.degree + " " + e.field, e.institution, year-range))
  cv-entry[#entry-text]
}

// ==========================================================================
// OTHER ROLES
// ==========================================================================
= Other Roles

#for r in data.roles {
  if include-by-range(r.start_year, r.end_year) {
    let year-range = format-year-range(r.start_year, r.end_year)
    let org-text = if r.url != "" { link(r.url, r.organization) } else { r.organization }
    cv-entry[
      #r.role#period-if-needed(r.role)
      #org-text#period-if-needed(r.organization)
      #year-range.
    ]
  }
}

// ==========================================================================
// RESEARCH
// ==========================================================================
= Research

// --- Peer Reviewed Articles -----------------------------------------------
== Peer Reviewed Articles

#{
  let articles = data.publications.filter(p => p.type == "article")
  // Sort: accepted first (status != ""), then by year descending
  let articles = articles.sorted(key: p => {
    let y = if p.year != "" { int(p.year) } else { 9999 }
    -y  // negative for descending sort
  })
  // Apply year filter (but always include accepted/forthcoming)
  let articles = articles.filter(p =>
    p.status == "accepted" or include-by-year(p.year)
  )

  for pub in articles {
    let year-display = if pub.status == "accepted" { "(accepted)" } else { "(" + pub.year + ")" }

    // Build venue info
    let venue = {
      let parts = ()
      if pub.journal != "" { parts.push(emph(pub.journal)) }
      if pub.volume != "" {
        let vol-str = pub.volume
        if pub.number != "" { vol-str = vol-str + "(" + pub.number + ")" }
        parts.push(vol-str)
      }
      if pub.pages != "" { parts.push(pub.pages) }
      parts.join(", ")
    }

    // Title with link
    let title-display = if pub.url != "" {
      link(pub.url)[#pub.title]
    } else {
      pub.title
    }

    bib-entry[
      #with-period(pub.authors_display) #year-display.
      #title-display#period-if-needed(pub.title)
      #venue.
      #if pub.note != "" {
        linebreak()
        emph(pub.note)
      }
    ]
  }
}

// --- Book Chapters --------------------------------------------------------
== Book Chapters

#{
  let chapters = data.publications.filter(p => p.type == "incollection")
  let chapters = chapters.filter(p => include-by-year(p.year))

  for pub in chapters {
    let title-display = if pub.url != "" {
      link(pub.url)[#pub.title]
    } else {
      pub.title
    }

    let in-book = if pub.booktitle != "" {
      [in #emph(pub.booktitle)]
    } else { [] }

    let editor-str = if pub.editor != "" {
      [, edited by #pub.editor]
    } else { [] }

    bib-entry[
      #with-period(pub.authors_display) (#pub.year).
      #title-display,
      #in-book#editor-str.
    ]
  }
}

// --- Work in Progress -----------------------------------------------------
== Work in Progress

#for w in data.wip {
  let title-display = if w.url != "" {
    link(w.url)[#w.title]
  } else {
    w.title
  }
  cv-entry[#with-period(w.authors) #title-display#period-if-needed(w.title)]
}

// --- Other Writing --------------------------------------------------------
#{
  let writing = data.other_writing
  let writing = writing.filter(w => include-by-year(w.year))
  let writing = writing.sorted(key: w => -int(w.year))

  if writing.len() > 0 {
    [== Other Writing]
    for w in writing {
      let title-display = if w.url != "" {
        link(w.url)[#w.title]
      } else {
        w.title
      }
      bib-entry[#with-period(w.authors_display) (#w.year). #title-display#period-if-needed(w.title) #emph(w.venue).]
    }
  }
}

// ==========================================================================
// INVITED PRESENTATIONS
// ==========================================================================
== Invited Presentations

#{
  let invited = data.presentations.filter(p => p.type == "invited")
  let invited = invited.filter(p => include-by-year(p.year))

  // Group by title, preserving order of first appearance
  let seen-titles = ()
  let title-order = ()
  for p in invited {
    if p.title not in seen-titles {
      seen-titles.push(p.title)
      title-order.push(p.title)
    }
  }

  for title in title-order {
    let venues = invited.filter(p => p.title == title)
    // Sort venues by year descending
    let venues = venues.sorted(key: v => -int(v.year))
    let venue-strs = venues.map(v => v.venue + ", " + v.year)

    cv-entry[
      #stack(
        spacing: cv-leading,
        [#with-period(title)],
        [#cv-sublist(venue-strs)],
      )
    ]
  }
}

// --- Selected Conference Presentations ------------------------------------
/*
#{
  let confs = data.presentations.filter(p => p.type == "conference")
  let confs = confs.filter(p => include-by-year(p.year))

  if confs.len() > 0 {
    [== Selected Conference Presentations]

    // Group by title
    let seen-titles = ()
    let title-order = ()
    for p in confs {
      if p.title not in seen-titles {
        seen-titles.push(p.title)
        title-order.push(p.title)
      }
    }

    for title in title-order {
      let venues = confs.filter(p => p.title == title)
      let venues = venues.sorted(key: v => -int(v.year))
      let venue-strs = venues.map(v => v.venue + " " + v.year)
      let venues-text = venue-strs.join(", ") + "."
      let entry-text = join-sentences((title, venues-text))
      cv-entry[#entry-text]
    }
  }
}
*/

// ==========================================================================
// TEACHING EXPERIENCE
// ==========================================================================
= Teaching Experience

#{
  // Group courses by institution, build prose paragraphs
  let courses = data.teaching.filter(c => include-by-range(c.start_year, c.end_year))

  // Get unique institutions in order
  let seen-inst = ()
  let inst-order = ()
  for c in courses {
    if c.institution not in seen-inst {
      seen-inst.push(c.institution)
      inst-order.push(c.institution)
    }
  }

  for inst in inst-order {
    let inst-courses = courses.filter(c => c.institution == inst)
    let is-current = inst-courses.any(c => c.end_year == "")

    let grad = inst-courses.filter(c => c.level == "graduate").map(c => c.course)
    let ugrad = inst-courses.filter(c => c.level == "undergraduate").map(c => c.course)

    let verb = if is-current { "teach" } else { "taught" }
    let at-str = "At " + inst + " I " + verb + " "

    let parts = ()
    if grad.len() > 0 {
      let noun = if grad.len() == 1 { "a graduate course" } else { "graduate courses" }
      parts.push(noun + " on " + grad.join(", ", last: " and "))
    }
    if ugrad.len() > 0 {
      let noun = if ugrad.len() == 1 { "an undergraduate course" } else { "undergraduate courses" }
      parts.push(noun + " on " + ugrad.join(", ", last: " and "))
    }

    let sentence = at-str + parts.join(" and ") + "."
    cv-entry[#with-period(sentence)]
  }
}

// ==========================================================================
// GRANTS & AWARDS
// ==========================================================================
= Grants & Awards

#{
  let grants = data.grants
  let grants = grants.filter(g => include-by-year(g.year))
  // Sort by year descending
  let grants = grants.sorted(key: g => -int(g.year))

  for g in grants {
    // Format amount with comma separators
    let amount-str = if g.amount != "" {
      let amt = int(g.amount)
      let formatted = if amt >= 1000 {
        let thousands = calc.floor(amt / 1000)
        let remainder = calc.rem(amt, 1000)
        if remainder == 0 {
          str(thousands) + ",000"
        } else {
          // Zero-pad remainder to 3 digits (e.g. 50 -> "050")
          let r = str(remainder)
          let r = if r.len() == 1 { "00" + r } else if r.len() == 2 { "0" + r } else { r }
          str(thousands) + "," + r
        }
      } else {
        str(amt)
      }
      " $" + formatted
    } else { "" }
    let co-str = if g.co_investigators != "" {
      " (with " + g.co_investigators + ")"
    } else { "" }
    let entry-text = g.title + co-str + ", " + g.funder + ", " + g.year + amount-str
    let entry-text = with-period(entry-text)
    cv-entry[#entry-text]
  }
}

// ==========================================================================
// SERVICE
// ==========================================================================
= Service

== Administrative Positions

#for a in data.admin_positions {
  let year-range = format-year-range(a.start_year, a.end_year)
  let entry-text = join-sentences((a.role, a.unit, year-range))
  cv-entry[#entry-text]
}

== Peer Reviews

// peer_reviews.csv is loaded into data but intentionally not rendered here;
// structured data is kept for potential future use (e.g. a reviewer appendix).
#cv-entry[Lots]

== Other Service

#{
  let services = data.service
  let services = services.filter(s => {
    if s.year == "" or s.year == none { true }
    else { include-by-year(s.year) }
  })

  for s in services {
    let desc = if s.url != "" {
      link(s.url, s.description)
    } else {
      s.description
    }
    let suffix = if s.year != "" { ", " + s.year } else { "" }
    let desc-str = s.description + suffix
    let entry-text = if s.url != "" {
      [#link(s.url, s.description)#suffix]
    } else {
      [#s.description#suffix]
    }
    cv-entry[#entry-text#period-if-needed(desc-str)]
  }
}
