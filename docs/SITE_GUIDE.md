# Feed. Form. Flow. website guide

This is the maintained guide to the three public pages in `docs/`. Read it
before changing their design, copy, navigation, screenshots, metadata or
deployment. The CSS remains the source of truth for exact implemented values;
this guide records why those values and structures were chosen.

This guide describes the current site and its intended direction. It is not a
request to make every possible improvement at once. When a decision changes,
update the implementation and this guide together.

## Pages and responsibilities

| Public page | Purpose | Main files |
| --- | --- | --- |
| `feedformflow.ca/` | An editorial hub that introduces Hui Jun Chew, points to writing and presents the two tools | `docs/index.html`, `docs/home.css` |
| `feedformflow.ca/encalc/` | A detailed explanation of ENCalc for people deciding whether and how to use it | `docs/encalc/index.html`, `docs/site.css` |
| `feedformflow.ca/btfcalc/` | A detailed explanation of BTFCalc for people deciding whether and how to use it | `docs/btfcalc/index.html`, `docs/site.css` |

The landing pages are plain HTML and CSS with no site generator or client-side
framework. `docs/favicon.svg` supplies the shared icon. The two `card.png`
files are social-sharing images; `docs/_card-source.html` is their editable
source and is intentionally excluded from search indexing.

The hosted Streamlit calculators at `encalc.feedformflow.ca` and
`btfcalc.feedformflow.ca` are separate applications. Their interfaces show the
tools themselves, but they are not visual templates for the static landing
pages. Streamlit supplies its own component system and theme controls. The
landing pages should share the broader Feed. Form. Flow. identity without
copying the calculator interface.

The homepage and product pages have different jobs. The homepage may use a
more expressive composition because it establishes the identity of Feed. Form.
Flow. The product pages need a quieter reading structure because they carry
clinical scope, privacy, data and workflow information. Coherence comes from
the palette, typography, geometry and interaction rules rather than from making
all three pages share one layout.

## Preferred visual character

The site should feel professionally credible at first glance and quietly
distinctive on closer inspection. A healthcare professional should find it
clear and trustworthy, while someone attentive to design should notice that
the geometry, alignment and colour relationships were considered.

The requested Frank Gehry influence is subtle. It appears through shifted
planes, slight rotation and the tension between clean rectangular surfaces.
The layered homepage hero is the clearest expression of it. The rest of the
page uses clean lines and stable alignment so that the gesture retains its
effect. Cards and body sections should remain still.

The visual identity should avoid these directions:

- generic newspaper or magazine templates;
- spreadsheet, dashboard or administrative-interface styling;
- a conventional corporate landing page made distinctive only by jewel tones;
- decorative lines or shapes that look attached after the layout was finished;
- large areas of claret that compete with the blue and mustard system;
- excessive animation, exaggerated rotation or literal deconstructivist forms;
- pill-shaped controls and very soft cards that weaken the rectangular
  structure.

Fun should come from proportion, colour placement and one or two controlled
geometric moves. It should not depend on novelty copy, icons or ornamental
effects.

## Current coherence and known gap

ENCalc and BTFCalc are visually coherent with each other because they share the
same stylesheet, masthead, reading column, section bands and interaction
patterns. The homepage belongs to the same family through its typography and
palette, but it is deliberately wider and more expressive.

The largest unfinished inconsistency is theme behaviour. The product pages use
`prefers-color-scheme` and follow the device's light or dark preference. The
homepage currently forces light mode. None of the three pages has a manual
theme control.

Light mode is the current reference for comparing the three landing-page
designs. A browser using a dark device preference will render the product pages
in dark mode while leaving the homepage light; screenshots made in that state
show the implementation gap rather than the intended visual comparison. Label
dark-mode captures explicitly and do not use them as the primary reference for
the landing-page identity.

The intended improvement is a shared **System / Light / Dark** control that:

- appears on all three pages;
- persists the visitor's choice across pages and later visits;
- defaults to the device setting when no choice has been saved;
- applies a designed dark palette to the homepage rather than mechanically
  inverting its colours;
- retains readable contrast and visible focus in every mode.

Until that work is implemented and tested, do not describe the static site as
having switchable dark mode.

## Colour system

Blue and mustard lead the website. Claret connects the site to the calculators
and supplies a smaller accent. The colours should retain consistent jobs so
that variety does not become noise.

| Token | Current value | Intended use |
| --- | --- | --- |
| Blue | `#245B78` | Primary identity, homepage hero, headings, links and the ENCalc card rule |
| Mustard | `#D9A62E` | Structural accent, hero backing plane, section spines, buttons, rules and the BTFCalc card rule |
| Claret | `#A4243A` | Section numbers, tool names, clinical cautions and limited identity accents |
| Homepage paper | `#FAFAFA` | Neutral homepage ground |
| Product-page ground | `#FCFAF9` | Slightly warm reading ground for product explanations |
| Ink | `#292526` | Main text |
| Soft ink | `#5E5558` | Supporting text and metadata |
| Pale blue | `#F3F8FA` | Light ENCalc card and quiet blue backgrounds |
| Pale yellow | `#FFF9E8` | Homepage introduction, BTFCalc card and quiet yellow backgrounds |

Mustard works best as a surface, rule or button. It should not be used for body
text on the light ground because the contrast is weak. Claret should not be
used for general Writing headings; it belongs to controlled accents and the
tool identity. When a card has a coloured top rule, the rule should match the
card's colour family.

The blue foreground hero with a mustard backing plane is the settled homepage
choice. A mustard foreground made the page read like retail branding, so that
arrangement should not be restored casually. The mustard final period in the
hero title is intentional.

`docs/site.css` contains a separate dark palette for the product pages. Its
lighter blue, warmer mustard and softened claret preserve the same hierarchy on
a dark ground. Future homepage dark-mode work should begin with those
relationships, but it may need different surface values because the homepage
uses layered cards and a large hero.

## Typography

All three pages use the operating system's sans-serif stack. The site does not
depend on a remote font, which keeps loading fast and makes the clinical pages
feel direct. Hierarchy comes from size, weight, line height and colour.

The homepage uses a large, tightly spaced hero title, medium-weight section
headings and restrained body sizes. The product pages use a readable body size
and a narrow measure for long explanations. Section numbers `01`, `02` and
`03` must remain the same size and weight.

Avoid shrinking the whole page to create more margin. The current homepage
width and type sizes were evaluated together. If the outer margins change,
review line lengths, the hero title and the tool cards as one composition.

## Homepage composition

The homepage header carries Hui Jun Chew's name at the left and LinkedIn and
GitHub at the right. The page is short enough that internal section links are
unnecessary. The hero title itself supplies the publication identity.

The hero consists of a blue foreground plane over an offset mustard plane.
Both are rectangular with modest corner rounding. The slight rotation and the
small hover movement belong only to this feature. Reduced-motion preferences
must continue to disable that movement.

The short professional introduction sits below the hero in a pale yellow
surface. It is outside Writing, Tools and About because it introduces the whole
site. Writing explains the public thinking-and-doing space on Substack; About
explains the professional point of view. Those sections should not repeat the
same paragraph in different words.

At wide sizes, each body section has its number and title in a left column and
its content in a right column. Writing and About have separate mustard spines.
Tools deliberately has no spine because the two card rules provide its visual
structure. The text beside a spine is inset enough that it does not appear to
touch the line.

The tool cards sit side by side on wide screens and stack on narrow screens.
ENCalc uses a pale blue surface with a blue top rule; BTFCalc uses a pale yellow
surface with a mustard top rule. Both tool names use claret, and both primary
buttons use mustard. Cards have small rounded corners and a strong rectangular
shape. They do not move on hover.

The footer uses a mustard top rule. Its closing phrase is "Working and writing
about foods, healthcare and technology".

## Product-page composition

ENCalc and BTFCalc are detailed product-explanation pages. Their copy and
screenshots are deliberate and should be preserved unless a specific factual,
clinical or usability reason requires a change. Do not solve a visual problem
by rewriting these pages.

The text, masthead and footer share a `41rem` reading column. On wider screens,
that column is anchored to a `4rem` left rail. Screenshots may extend to
`72rem`, but they begin on the same left edge so the page retains a strong
alignment. On narrow screens, the rail disappears and the normal gutter
protects the content.

The product pages use pale blue and pale yellow section bands, a blue primary
call to action, mustard for the final call-to-action button and claret for
clinical cautions. Their screenshots show the current tools and should be
replaced only when the product interface has materially changed. Calculator
screenshots document the Streamlit product; they do not determine the landing
page's layout or component styling. Capture the calculator in an intentional,
identified theme rather than allowing an unnoticed device setting to choose
the appearance.

The current homepage mockup is not a replacement visual system for these
pages. The product pages should gain shared identity details carefully while
remaining readable explanations rather than becoming oversized promotional
pages.

## Links, controls and motion

Homepage text links do not use arrows. Their hover state is a solid underline
that includes the complete linked text. Primary tool buttons do not gain a red
or claret outline on hover.

Product-page calls to action currently retain a simple right arrow because the
arrow belongs to the action label rather than decorating every link. Ordinary
product-page links remain underlined.

Interactive targets should remain at least `44px` high where practical. Focus
must be visible, keyboard order must follow document order, and skip links must
remain functional. New motion must respect `prefers-reduced-motion`.

## Copy and content guardrails

- Preserve the existing ENCalc and BTFCalc copy and screenshots unless there
  is a specific reason to change them.
- Keep the homepage concise. It is an editorial hub rather than a third
  product-explanation page.
- First-person writing is appropriate because the site represents an
  individual practitioner. Avoid awkward top-of-page bylines such as "By Hui
  Jun Chew, registered dietitian."
- The Writing section links directly to Feed. Form. Flow. on Substack. It does
  not fetch RSS, and it does not duplicate or automatically feature individual
  posts.
- The absence of featured posts is deliberate. Reintroduce them only if there
  is a clear editorial reason and a maintainable update process.
- Preserve the distinction between public thinking, practical work and the
  tools themselves. Do not reduce the Substack to generic "long-form writing."
- Keep the clinical scope, privacy and product-data statements accurate. These
  are functional content rather than marketing copy.

## Visual history to review

Review these commits before changing the product-page layout. They show which
decisions were tested and which direction became current:

- `c98145f` rebuilt the three-page site, established the sans-serif hierarchy,
  accessibility baseline, screenshots and product-page content order.
- `9720566` aligned masthead, prose, media and footer to one left edge.
- `6bf1519` tested a centred `41rem` reading column with wide screenshot
  breakouts.
- `646c82d` settled the current left-anchored reading column and added the two
  orientation screenshots.

The sequence matters because the middle commits are explorations rather than
four simultaneous rules. The current product layout follows `646c82d` and
later screenshot updates. The current homepage design was implemented in
`11c6880` and then simplified in `b270f2d` when the RSS dependency and featured
articles were removed.

## Publishing and domain configuration

The `Feed Form Flow website` workflow in `.github/workflows/site.yml` uploads
`docs/` and deploys it with GitHub Pages whenever relevant files reach `main`.
It can also be run manually. The workflow does not contact Substack.

GitHub Pages is configured through repository settings with
`feedformflow.ca` as the custom domain. Because deployment uses a custom GitHub
Actions workflow, a checked-in `CNAME` file is not required.

The current DNS arrangement is:

| Record | Host | Target |
| --- | --- | --- |
| `A` | root/blank | `185.199.108.153` |
| `A` | root/blank | `185.199.109.153` |
| `A` | root/blank | `185.199.110.153` |
| `A` | root/blank | `185.199.111.153` |
| `CNAME` | `www` | `greywhitebinary.github.io` |

These are GitHub's published Pages records as configured on 18 September 2026.
Check GitHub's current documentation before recreating them in the future.
Porkbun labels the destination field **Target**.

The root domain uses DNS records rather than URL forwarding. GitHub serves the
site at `feedformflow.ca` and redirects the project `github.io` address to the
custom domain. The `www` name redirects to the root domain.

The existing `encalc` and `btfcalc` Porkbun records point to
`uixie.porkbun.com` for their separate forwarding arrangements. Do not remove
or replace them while changing the root or `www` records. Preserve existing
email, verification and `_acme-challenge` records as well.

GitHub manages the site's HTTPS certificate. DNS changes can be cached after
the authoritative records are correct, so allow time for caches and certificate
provisioning before changing working records again.

Canonical URLs, Open Graph URLs, structured data and `docs/robots.txt` use
`https://feedformflow.ca`. Keep those values aligned if the public domain ever
changes.

## Maintenance checklist

Before editing:

1. Read this guide and inspect all three rendered landing pages in the same
   theme. Use light mode as the current reference.
2. Determine whether the change belongs to the editorial homepage, both
   product pages or the actual calculator applications.
3. Review the visual-history commits when changing product-page layout.
4. Preserve deliberate copy and screenshots unless the task specifically
   requires changing them.

After editing:

1. Preview the site through a local web server rather than opening the HTML as
   a file.
2. Check the homepage and both product pages at narrow and wide widths.
3. Check light and dark product-page rendering separately and label comparison
   screenshots with the mode used. Once the shared theme control exists, check
   all three pages in System, Light and Dark.
4. Confirm that keyboard focus, skip links, hover states and `44px` controls
   still work.
5. Check internal links, image paths, canonical metadata and JSON-LD.
6. Confirm that the product pages have no unexpected copy or screenshot
   changes.
7. Update this guide when a settled design, content, domain or deployment
   decision changes.
