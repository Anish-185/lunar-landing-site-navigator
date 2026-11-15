# Fresh-eyes jury

An independent reviewer (a separate Claude subagent briefed as an Awwwards juror, not the author) scored screenshots
of v1 (tag `v1-submittable`) and v2 (branch `design-v2`) against the references in RESEARCH.md. Awwwards weights:
Design 40 %, Usability 30 %, Creativity 20 %, Content 10 %. Lighthouse figures were given to it as measured facts.

## Scores

| Version | Design | Usability | Creativity | Content | Weighted |
|---|---|---|---|---|---|
| v1 | 6.3 | 6.5 | 6.0 | 7.5 | **6.42** |
| v2, round 1 | 7.4 | 7.0 | 7.6 | 8.0 | **7.38** |
| v2, round 2 (after fixes) | 7.9 | 7.6 | 7.9 | 8.2 | **7.84** |

Round 1 reasons (v2): "a coherent art direction (Instrument Serif headings with grazing-light gradient, gold = Sun,
mono readouts); 'Be the Sun' with real ray-marched shadows is a genuine signature moment; Lighthouse 100s; content rare
for the category (real numbers, sources, an honest 'checked against NASA' chapter)". Held back by: header collisions,
an empty hero, a broken Compare table, chapter dead space.

Round 2 reasons: "header backdrop fixes the collisions; the hero now carries the concept with the sunlit limb; real
Compare values add credibility; the relit pole and limb-lit hero form one clear opening act."

Verdict both rounds: **v2 is clearly better than v1 side by side, ready to merge.**

## Round 1 findings and what we did

| # | Finding | Action |
|---|---|---|
| 1 | Compare table showed "None" in every cell; bar labels rotated and clipped | **Root cause:** `pd.DataFrame({...Series...}, index=labels)` realigned Series with a 0..n index onto the label index, so every value became NaN (present since v1). Built from the label-indexed frame; regression test `test_compare_table_has_numbers_not_none`; horizontal wrapped bar labels; short column names; no highlight when a row ties |
| 2 | Text slides under the transparent header | Dark blurred backdrop that fades below the bar |
| 3 | Hero is a wordmark and a dot | The limb of a dark Moon with a rim of grazing sunlight at scroll 0 (CSS only, LCP unchanged) |
| 4 | Pole hint unreadable on lit terrain; stair-stepped shadows; "cursor" on touch | Glass panel behind the readout; scrim behind the copy; bilinear heights in the shadow march and a penumbra that grows with distance; touch copy "Drag around the pole" |
| 5 | Sun readout overlaps the paragraph | Readout moved into its own row above the panorama |
| 6 | Dead space in the Earth chapter | Split chapters 88 vh instead of 100 vh |
| 7 | Slip heatmap labels clipped | Parentheticals dropped, `automargin`; horizontal colour bar on phones |
| 8 | Six lines of display type over the Earth | Two sentences; the date became a small caption |
| – | "arcsec" orphaned; source links default blue | `.proof span` also matched the unit span (`display: block`); scoped to `.proof > span`; links restyled |

## Round 2 findings still open

- The mobile sky panorama shows about 200° of the 360° (it pans to follow the Sun). It was widened from 1100 to 820 px so
  more of the circle shows; a full 360° in 390 px squashes the SVG labels.
- Some crater rims still show stair-stepping at the 792 m heightmap resolution when the zoom is high.
- Site labels on the pole map can sit under the header near the end of the zoom.
