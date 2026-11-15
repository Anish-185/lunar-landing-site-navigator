# Space Apps 2026 project page: ready-to-paste text

Fields follow the official [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/) (page dated 13 Nov 2026). The guide sets **no character limits** for these fields. Its only hard limits apply to the demo: a video of 30 seconds or less, or at most 7 slides including the title. Ours is 28.0 s and 7 slides. All content must be in English. Videos and documents can't be uploaded, so the demo is a public link (GitHub Pages, no login).

Challenge: **Lunar Landing Site Navigator** · Team: **Anish G**

---

## Project Name

Gnomon: Lunar Landing Site Navigator

## High-Level Project Summary

Gnomon is a landing-site planner for the Moon's south pole, built on NASA data. There the Sun never climbs: it circles the horizon a degree or two up, so a ridge 100 km away can switch a solar lander off. Earth bobs up and down and drops behind the terrain for days.

For any site, date and lander, Gnomon gives Power, Comms and Landing-light verdicts and the countdown to the next sunset or Earthset. It names the ridge that blocks the Sun ("Mons Malapert, 111 km away at az 94°") and gives the odds of a good landing across the whole landing ellipse. When the launch slips, it re-ranks every site and landing day and offers a Plan B.

It answers the challenge's question (when can I see the Sun and Earth from here?) in plain words and pictures, for mission planners, educators and the public. Its answers are checked against JPL Horizons and NASA's own illumination maps.

## Link to Project Demo

https://anish-185.github.io/lunar-landing-site-navigator/demo/

(The page has a 28-second video with English subtitles and a 7-slide PDF deck. Direct links: https://anish-185.github.io/lunar-landing-site-navigator/demo/gnomon_demo.mp4 and https://anish-185.github.io/lunar-landing-site-navigator/demo/gnomon_slides.pdf)

## Link to Final Project

https://anish-185.github.io/lunar-landing-site-navigator/

(The story site embeds the live mission console, which is also at https://gnomon-moon.streamlit.app. Source code: https://github.com/Anish-185/lunar-landing-site-navigator. If the console shows Streamlit's sleep screen, click "Yes, get this app back up" and wait about 30 seconds.)

## Detailed Project Description

**What it does.** Gnomon has two parts. The story site is a scroll-driven tour for anyone: you fly to the south pole and "be the Sun", moving a 1.5° light over NASA's LOLA terrain and watching the shadows run for tens of kilometres. You see the Sun circle a real skyline, Earth play hide and seek, and why 250 m decided IM-2 Athena's fate.

The mission console is the planner. It has six pages:
- **Site:** verdicts with reasons, countdowns, a 360° sky panorama, an hourly timeline and "blame the ridge", plus landing-zone odds over 200 simulated landings, a decision brief and a CSV export.
- **Compare:** up to four sites or dates side by side.
- **Slip Replanner:** every candidate site and landing day re-ranked, with Plan B cards that say what changed.
- **Map:** NASA's long-run sunlight and Earth-visibility maps and Diviner cold traps.
- **Athena replay:** IM-2's landing, step by step.
- **Evidence:** how we checked our numbers.

**How it works.** An offline Python pipeline reads NASA's LOLA south-pole terrain models: 20 m near the site, 80 m out to the far horizon. It traces the terrain horizon at 720 azimuths with NASA-AMMOS MMGIS Sightline code and names each blocking point from the USGS Gazetteer. It computes the Sun and Earth with NASA NAIF SPICE (DE440, MOON_ME frame), and gives each of 200 landing-ellipse points its own horizon and slope. Compact results are saved to files. The console (Streamlit) and the logic library (NumPy, 227 tests) read only those files and make no network calls. The story site is static (Vite, three.js, Plotly) and reads the same engine's output.

**Validation.**
- Sun and Earth positions match JPL Horizons to 0.004 arcsec over 130 checks.
- Long-run sunlight at 13 of 14 polar sites falls inside the range of NASA's own LOLA illumination map within 420 m of the site.
- Hindcast: our first sunset after Chandrayaan-3's landing falls on 4 Sep 2023, the day ISRO put Vikram to sleep "at sunset".

**Known limits** are listed openly. Terrain smaller than about 40 m is invisible, including Athena's 20 m crater. Comms thresholds and lander power numbers are illustrative and labelled as such.

**Benefits.** It answers questions planners actually ask, in plain words:
- Will we have power and a link home?
- Who is to blame when we don't?
- How much margin does the landing ellipse leave?
- What's our Plan B if the launch slips?

It is free, open source (Apache-2.0) and runs in a browser.

**What we hope to achieve.** A tool that a mission team, a teacher or a curious reader can use to understand why the Moon's south pole is so hard, and to choose better landing sites and dates for Artemis-era missions.

**Tools and languages.**
- **Languages:** Python and JavaScript.
- **Python:** SpiceyPy, Skyfield, NumPy, SciPy, pandas, rasterio, pyproj, GDAL, GeoPandas, Numba, Streamlit, Plotly, pytest.
- **JavaScript:** Vite, three.js, Plotly.js, Lenis, Motion.
- **Vendored code:** NASA-AMMOS MMGIS Sightline scripts.
- **Hosting and build:** GitHub Pages and Streamlit Community Cloud. Playwright and FFmpeg for screenshots and the demo video.

## Use of Super Intelligence (SI)

Yes. The code and text were written with Claude Code (Anthropic), an AI coding assistant, from the team's prompts. The team chose the idea, features and data, and reviewed, tested and is responsible for the result. The AI also helped with research (reading other public projects for ideas, credited without copying code) and with drafting the documentation and this page.

No images, video or audio were generated by AI. Every visual is either a render of NASA data by our code, a NASA public-domain image, or a screen capture of the app. This disclosure is also in the README, in ATTRIBUTIONS.md, on the deck's last slide and in the demo video's metadata.

## NASA Data

- **LOLA south polar DEMs:** 20 m and 80 m, with slope, height error and permanently shadowed regions (PGDA product 90, Barker et al. 2023); 240 m for Chandrayaan-3.
- **LOLA average Sun and Earth visibility maps:** PGDA product 69, Mazarico et al. 2011, used for validation and the map layers.
- **NAIF SPICE kernels:** DE440 ephemeris, lunar PCK and the MOON_ME frame.
- **JPL Horizons:** used to validate our ephemeris.
- **LRO Diviner Polar Resource Product:** maximum temperature, for cold traps under 110 K.
- **LROC imagery:** Athena's resting position.
- **NASA SVS:** CGI Moon Kit and Blue Marble.
- **Deep Space Network:** station positions.
- **Hubble:** Carina Nebula image (background).
- **NASA's Artemis III briefing for Space Apps:** landing criteria.
- **USGS:** Gazetteer of Planetary Nomenclature, for feature names.

## Space Agency Partner Data and Other References

**Space agency partner data:** ISRO's published Chandrayaan-3 landing site, landing time and end-of-mission statement ("at sunset over the landing site"), via Wikipedia, which cites ISRO. We use them for the hindcast. We used no other partner datasets.

**Open-source code:**
- NASA-AMMOS MMGIS (Apache-2.0)
- SpiceyPy, Skyfield, NumPy, SciPy, pandas, rasterio, pyproj, GDAL, GeoPandas, Shapely, Numba, Streamlit, Plotly, pyarrow and PyYAML
- three.js, Plotly.js, Lenis, Motion, Vite and Playwright

**Fonts and icons:** Instrument Serif, Geist and Geist Mono (SIL OFL); Lucide icons (ISC).

**References:**
- Barker et al. 2023 (LOLA polar DEMs)
- Mazarico et al. 2011 (Icarus, polar illumination)
- Paige et al. 2010 (Diviner)
- Bertone et al. (shape-from-shading DEMs, PGDA 104)
- JPL IPN Progress Reports 42-222, 42-226 and 42-243 (multipath near the south pole)
- LROC "IM-2 Athena Seen Obliquely"
- Associated Press and Gizmodo reports on Athena
- Wikipedia mission pages for Chandrayaan-3, IM-1, IM-2 and Blue Ghost 1 (facts only)

**Ideas only, no code copied:** other public Space Apps repositories, credited in ATTRIBUTIONS.md.

The full list, with licences and links: https://github.com/Anish-185/lunar-landing-site-navigator/blob/main/ATTRIBUTIONS.md

---

### Before you click "Submit for Judging"

- [ ] Paste each field above, then Save Progress.
- [ ] Open the demo link and the final-project link in a private window (no login).
- [ ] Wake the console once (https://gnomon-moon.streamlit.app) shortly before judging.
- [ ] Tick "Terms and Conditions" and "Confirm All Work is Original", then **Submit for Judging** before 23:59 local time.
