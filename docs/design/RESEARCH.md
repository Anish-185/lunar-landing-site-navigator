# What an award-calibre space site does (research, 15 Nov 2026)

## The bar

Awwwards juries score **Design 40 %, Usability 30 %, Creativity 20 %, Content 10 %**. Sites of the Day average ~7–8
across the four, and Usability is where flashy entries lose: slow first paint, a loader that never ends, unreadable
text over WebGL, broken mobile, missing focus states. A site that is 80 % as spectacular but loads in two seconds and
reads well on a phone beats one that is spectacular and frustrating.

## References studied (design language only; nothing copied)

Captured with Playwright (Chromium, software GL) at 1440×900 and 390×844 into `docs/design/refs/` (kept local and
gitignored: they are other people's work). Three WebGL-first sites never got past their loaders in software GL, which
is itself a finding: on a weak GPU, their visitors see a loader.

| # | Reference | What makes it work | What we take |
|---|---|---|---|
| 1 | **Igloo Inc** (Awwwards Site of the Year 2024) | One material (ice) carries the whole brand: the loader, the 3D, the transitions are all ice. A hairline progress glyph, no logo splash. Cool monochrome; type tiny and technical so the 3D is the hero. | One material for the whole site: for us, **low sunlight**. A loader that is a glyph of the concept, not a spinner. |
| 2 | **Lusion** (studio, many SOTDs) | Loader is a giant counter (078…); confidence through restraint: black, white, one bold typographic gesture. Cursor-reactive WebGL. | Treat the loader as a brand moment, but short. Cursor as an input to the scene (our cursor = the Sun). |
| 3 | **Messenger by Abeto** (SOTD) | A tiny planet you walk around; the whole site is one interactive object. Warm palette, soft light. | One memorable interactive object beats many effects: our relit pole. |
| 4 | **Varda Space** (SOTD) | Terrain relief lit at a low angle as a duotone background (orange/blue); a visible hairline grid that the layout snaps to; big confident grotesk headings; strict 12-column rhythm. | Grazing-light relief as the image language; a visible, disciplined grid; two colours that mean something. |
| 5 | **SpaceX: The Moon** | Full-bleed photography, one centred all-caps wordmark, nothing else. Extreme negative space, real imagery over illustration. | Let real NASA imagery and data be the hero; cut chrome. |
| 6 | **NASA Eyes on the Solar System** | Real ephemerides in real time; a "LIVE / REAL RATE" timeline; thin uppercase labels on orbits; data and scene are the same thing. | Our scene is real too: the Moon lit by the SPICE Sun for the scenario date; say so on screen. |
| 7 | **Axiom Space** | 3D station over Earth's limb, big light-weight sentence-case heading, generous left margin. | Light-weight display type in sentence case; limb light. |
| 8 | **First Men on the Moon** (Webby) | Minute-by-minute replay of real mission data; a single "GO!" call to action; mission-control voice. | Mission-control voice; the "go/no-go" vocabulary in the console. |
| 9 | **Awwwards "space" collection** | Common winning traits: dark canvas, one luminous accent, huge type, scroll-scrubbed 3D, glass panels with 1px borders, thin uppercase micro-labels. | Same discipline, but avoid the clichés (tracked uppercase labels everywhere, purple-blue gradients). |
| 10 | **ESA Moon / Planetary Society** | Content-first, readable, accessible, fast; dull but trustworthy. | The floor we must not fall below: readable captions, real sources, works without WebGL. |

Rocket Lab sat behind a bot challenge (no capture).

### Cross-cutting observations

- **Type pairing and scale:** winners use one display face at very large sizes (10–15 vw) and one quiet sans; display
  weight is usually regular or light, never hairline-thin at mid sizes. Body copy stays 16–18 px with a ~60–70
  character measure.
- **Grid and negative space:** a strict grid that is sometimes visible (hairlines, Varda); one idea per viewport.
- **Colour and light:** a near-black canvas and one luminous accent; light is rendered as a material (glows, rims,
  grazing relief), not as flat fills. Heavy drop shadows are absent; glass panels have a 1 px light border and an inner
  highlight.
- **Motion and easing:** expo/quint ease-outs; reveals are masks and wipes more than fades; scroll-scrubbed 3D; no
  linear motion except time; reduced-motion handled by the best ones.
- **Transitions:** the best sites never cut; the next section is revealed by something that moves (a wipe, a camera
  move, a colour change).
- **Loaders:** brand glyphs, short, sometimes a counter. The bad ones gate content for 5+ s.
- **Cursor and hover:** cursor-reactive light or distortion on desktop only; every link has a hover state that
  belongs to the concept (glow, underline draw).
- **Data:** shown as part of the scene (orbits, readouts) with mono numerals and quiet units.
- **Mobile:** the 3D is simplified, text never sits over busy imagery without a scrim, and interaction falls back to
  auto-play plus a drag.

## Ten principles we apply

1. **One material: low sunlight.** Every visual effect is light or shadow from a grazing Sun; nothing else decorates.
2. **One unforgettable interaction:** you are the Sun over the real polar terrain, with real cast shadows.
3. **Physics is the art direction:** the hero Moon is lit by the real Sun for the scenario date; colour means physics.
4. **One display face, large and confident** (Instrument Serif), one quiet sans (Geist), mono only for readouts.
5. **A strict 12-column grid** shared by the story and the console; copy in 5 columns, figures in 6.
6. **Transitions are terminators:** headings are revealed by a sweeping light edge, not faded in.
7. **Expo-out easing, 200–600 ms for UI**, longer only for the cinematic sweeps; never linear.
8. **Short loader as a brand glyph** (a sundial), skippable, failsafe after 3 s.
9. **Usability first:** content readable without WebGL, captions with a one-line takeaway, focus states, AA contrast,
   reduced motion, Lighthouse ≥ 85.
10. **Restraint:** no eyebrow labels, no gradient blobs, no cursor gimmick beyond a faint light; remove one accessory.
