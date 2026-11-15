# Gnomon: art direction

## The one idea: LOW LIGHT

A gnomon is the pin of a sundial; it tells time by the shadow it throws. At the lunar south pole the whole landscape is a
sundial: the Sun never climbs more than about 1.5° (plus the terrain's own tilt), so every ridge throws a shadow tens of
kilometres long, and the shadows swing all the way round once a month. **Everything on the site is lit by that low,
grazing Sun.** Light is the content (where is it, how long does it last), so light is also the material of the design.

- **The terminator is the transition.** Chapters are separated by a moving light/shadow edge, not by hard cuts. Each
  chapter heading is revealed by a soft terminator sweeping across it, the way dawn crosses a crater rim.
- **Headings are lit by a grazing Sun.** Display type carries a gold-white highlight on the Sun's side that falls off
  into shadow on the far side, and a faint long shadow on the ground behind it. The Sun's azimuth advances as you
  scroll, so the light on the headings slowly swings round, exactly as it does at the pole.
- **You are the Sun (signature moment).** In the "Fly south" chapter the LOLA terrain of the whole polar cap is relit
  in real time with ray-marched cast shadows at a 1.5° Sun. On desktop the cursor *is* the Sun: move it round the pole
  and kilometre-long shadows swing with it, while the permanently shadowed crater floors stay black whatever you do.
  On touch, the Sun circles on its own (one lunar day in 20 s) and a drag takes over. This is the one thing people will
  remember, and it is the whole thesis of the product in five seconds.
- **The real Sun, not a pretty one.** The 3D Moon is lit from the Sun's actual direction on 18 Jan 2027 12:00 UTC (SPICE,
  DE440), so the terminator in the hero is physically right for the scenario the console opens on.

## Palette (tokens, shared by story site and app)

| Token | Hex | Meaning |
|---|---|---|
| `--space` | `#05060B` | space black, page background (slightly warm, not blue) |
| `--shadow` | `#0B0D17` | surfaces in shadow (cards, chart plots) |
| `--edge` | `rgba(232,228,216,.12)` | hairline borders, the grid |
| `--ink` | `#EDEAE2` | regolith-white text (warm, like sunlit dust) |
| `--ink-dim` | `#A3A09A` | secondary text (AA on `--space` and `--shadow`) |
| `--sun` | `#F4B860` | solar gold: the Sun, sunlight, primary action |
| `--sun-hot` | `#FFE9C2` | the Sun's core, highlights |
| `--earth` | `#6FB1FF` | Earth blue: link to Earth |
| `--terrain` | `#8C8A86` | terrain grey: skylines, relief |
| `--nebula` | `#7A5CFF` | nebula violet: used only as faint deep-space glow, never for data |
| `--alert` | `#FF5C5C` | failure, no-go |
| `--go` | `#6ED6B0` | go |

Colour is physics: gold always means the Sun, blue always means Earth, grey always means terrain, red always means
failure. Violet is atmosphere only.

## Type

- **Display: Instrument Serif** (OFL). Condensed, high contrast but with hairlines that survive at 1x; an
  engraved-instrument feel (sundial plates, star charts). Italic for the one emphasised phrase per heading.
- **Text and UI: Geist** (OFL). Neutral, crisp at small sizes, excellent tabular figures.
- **Numbers and readouts: Geist Mono** (OFL). Every measured number (degrees, hours, %, UTC) is set in mono with
  tabular figures; units in `--ink-dim` at 0.8em, so values read like an instrument panel.
- Scale (fluid, 1.25 minor third at small sizes opening to ~1.333 on desktop):
  display `clamp(4rem, 13vw, 12.5rem)` / h2 `clamp(2.6rem, 6vw, 5.5rem)` / h3 `1.6rem` / body `1.0625rem` /
  caption `.8125rem` / eyebrow `.75rem` mono uppercase +0.14em.
- `text-wrap: balance` on headings, `pretty` on body. Line heights: display .9, h2 1.0, body 1.6, caption 1.5.

## Layout

- 12-column grid, `--gutter: clamp(16px, 4vw, 64px)`, max content width 1440px; copy sits in columns 1–5, figures in
  6–12 (mirrored for alternation). Spacing scale 4/8/12/16/24/32/48/64/96/128/192 (`--s-1` … `--s-11`).
- No eyebrow labels above headings (reviewed against the frontend-design skill: tracked all-caps eyebrows and
  "01 — Name" markers are template chrome). Chapter names live once, in the progress rail on the right, where they do a
  job (navigation). Negative space is deliberate: one idea per viewport.
- Alignment: everything left-aligned to the grid; the only centred element is the loader.

## Motion language

- Easing: `--ease-out: cubic-bezier(.16, 1, .3, 1)` (expo-out: light arriving), `--ease-inout: cubic-bezier(.65, 0, .35, 1)`
  (the terminator sweeping). Never linear, except time itself (the Sun's path).
- Durations: UI 200–320 ms; reveals 600–900 ms with a 60 ms stagger per line; the terminator sweep 1200 ms; the loader
  at most 1.4 s and skippable.
- Scroll-linked motion only moves light and shadow (and the camera in the cosmos). Text never drifts while you read it.
- `prefers-reduced-motion`: no smooth scroll, no sweeps, everything visible and lit, the Sun on the pole map parks at a
  fixed azimuth with a slider to move it.

## Signature moments, in order of appearance

1. **Loader:** a sundial: a thin gnomon line casts a shadow that sweeps a quarter-circle while the data loads (CSS
   only), then the shadow becomes the hairline under the wordmark. Skippable (click/key), gone in under 1.4 s.
2. **Hero:** the real-lit Moon, a gold rim of sunlight on its limb, the wordmark lit from the same side.
3. **You are the Sun:** the relit pole with moving cast shadows (above).
4. **Chapter terminators:** each heading revealed by a sweeping light edge.
