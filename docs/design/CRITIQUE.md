# Critique of v1 (tag `v1-submittable`), ranked by how much a jury would notice

Screenshots: v1 in `docs/screenshots/` at the `v1-submittable` tag; v2 in `docs/screenshots/` on `main` after the merge.
Status: **fixed** (in design-v2), **partly**, or **open**.

| # | What looked unpolished or "mid" | Why a jury notices | Status |
|---|---|---|---|
| 1 | **Broken display headings**: "I Iere", "mctres dccidcd", "Mission consolc", "Athcna". | It reads as a bug in the first 10 seconds and caps the Design score. Root cause: Fraunces at `opsz 144`, weight 250–300, rendered at 40–70 px: hairlines under one device pixel vanish. | **fixed**: Instrument Serif at 400; crops verified at 1x and 2x DPR in Chromium. Firefox and WebKit **not verified** (the Playwright browser download hung and was stopped) |
| 2 | **No idea holding it together.** Big Bang particles, nebula, gold gradient wordmark, glass cards: each fine, together generic "space site". | Creativity (20 %) rewards one strong concept carried everywhere. | **fixed**: LOW LIGHT concept; every effect is grazing light or shadow |
| 3 | **No signature interaction.** The pole chapter was a pre-lit image that zoomed. | Nothing to remember or share. | **fixed**: "be the Sun": the LOLA cap relit live with ray-marched shadows; the cursor is the Sun |
| 4 | **The 3D Moon was lit from an arbitrary side** (light at a fixed position, rotation spun for show). | For a physics product, a fake terminator undercuts credibility. | **fixed**: lit from the SPICE Sun vector on 18 Jan 2027, seen from Earth's direction: the real phase |
| 5 | **Purple-blue "nebula" palette everywhere** (backgrounds #070B24, panels #11163A). | Reads as a template dark theme; the gold Sun had to compete with violet. | **fixed**: space black with warm regolith whites; violet reduced to a faint glow |
| 6 | **Chapter rail of 9 identical dashes** at the top; no chapter names. | Navigation without information; looks unfinished. | **fixed**: chapter name and number in the top bar, hover rail with names |
| 7 | **Every heading looked the same and just faded in.** | Generic fade-and-slide; no transition between chapters. | **fixed**: terminator sweep reveals and light that swings with scroll |
| 8 | **Charts on blue glass with Plotly defaults** (blue hover boxes, full modebar). | Charts are where data sites look most "default". | **fixed**: transparent plots, mono ticks, warm hover, modebar on hover only, one-line takeaway per chart |
| 9 | **Stat numbers in a light serif** (proof numbers, ridge duo, slip cards); "% Sun and link" crammed next to the number. | Hard to scan; units as loud as values. | **fixed**: tabular Geist light, units quieter, labels below |
| 10 | **Streamlit console did not match the story** (different background, fonts, card style; unequal card heights; slider value "2.00" wrapping onto three lines). | Jury clicks "Open the console" and sees a different product. | **fixed**: same tokens and fonts; equal-height verdict cards; slider readouts no-wrap; modebar on hover |
| 11 | **No loader / first impression was an empty black screen with a dot.** | First 2 seconds set the tone. | **fixed**: a sundial loader (≤ 1.4 s, skippable) |
| 12 | **Mobile: pole copy collided with site labels; long text over busy terrain.** | Mobile usability is scored. | **fixed**: scrim panel on phones, labels hidden under 760 px |
| 13 | **No share image, plain favicon, default 404.** | Shared links look unfinished; Awwwards checks details. | **fixed**: hero-rendered OG/Twitter image, sundial favicon, styled 404 ("This page is in permanent shadow") |
| 14 | Hero right half empty until the first scroll (the 3D waits for interaction for performance). | Some jurors don't scroll before judging the hero. | **fixed** (jury round 1): a CSS Moon limb with a rim of grazing sunlight fills it at scroll 0; the 3D still waits, so LCP stays 0.7 s |
| 15 | Console chapter shows a screenshot placeholder because `appUrl` is not set. | Embedded live demo is stronger. | **open**: needs the deployed Streamlit URL in `site/public/config.json` |
| 16 | Lambert shading on the Moon and the terrain (not lunar photometry). | Only an expert would notice. | **open**: logged in METHOD.md |
