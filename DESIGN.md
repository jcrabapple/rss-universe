# Visual system

## Direction

An independent web field guide. The design uses the visual language of a practical reference index rather than a marketing landing page. Directory entries are ruled rows, not cards.

## Color

Cool paper neutrals, dark green-black ink, and a vermilion accent drawn from the RSS mark. Light and dark themes use the same roles through OKLCH custom properties. Body, secondary, accent, and metadata colors maintain at least 4.5:1 contrast against their surface.

## Typography

Fira Sans handles body copy and interface text. Fira Sans Condensed handles the masthead, cover headline, section titles, and entry names. Both families are embedded as WOFF2 data and licensed under the SIL Open Font License; see `FONT-LICENSES.txt`.

## Composition

- Compact utility bar with brand, update date, contents control on mobile, and theme control.
- Two-column cover on desktop with a direct headline and one RSS mark. The mark is omitted on mobile to prioritize the directory.
- Inline directory facts rather than metric boxes.
- Sticky contents rail beside the directory at widths above 820px.
- Native popover contents sheet at widths up to 820px, with explicit close, link dismissal, outside-click dismissal, and Escape support.
- Two-column entry rows on desktop: name and metadata, then description and domain. Single-column rows on mobile.

## Interaction

Links use underlines where their purpose needs emphasis. Hover never moves the layout. Keyboard focus uses a three-pixel accent outline. The contents rail tracks the visible section with `aria-current="location"`. The cover mark has one short clip reveal, disabled under reduced motion.

## Verification floor

Check 144 total entries and 135 unique entries, all fragment targets, matching title and domain destinations, dark-mode persistence, popover behavior, accessibility-tree visibility, contrast, and horizontal overflow at 1440px, 390px, and 320px.
