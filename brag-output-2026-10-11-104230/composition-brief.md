# Hyperframes Composition Brief: RxVerify

## Objective
Create a short launch-style brag video for RxVerify — a digital prescription verification system for DevOps FA1.

## Output
- Composition directory: `/Users/yashsiphone/Downloads/digital-prescription-verification-devops/brag-output-2026-10-11-104230/composition/`
- Rendered video: `/Users/yashsiphone/Downloads/digital-prescription-verification-devops/brag-output-2026-10-11-104230/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `/Users/yashsiphone/Downloads/digital-prescription-verification-devops/`
- Primary files read: `templates/index.html`, `templates/verify.html`, `templates/result.html`, `templates/issue.html`, `templates/admin/dashboard.html`, `static/style.css`, `README.md`
- Product name: **RxVerify**
- Tagline / strongest claim: **"Secure prescription handoff. Doctor to pharmacist. Verified."**
- Key UI or visual moment to recreate: **Verification ID display** (`.verification-id`) — monospace, large, bordered, emerald background, the ONE bold element
- Copy that must appear verbatim:
  - "Secure prescription handoff."
  - "Doctor to pharmacist."
  - "Verified."
  - "RX-2F2D443F7D" (verification ID format)
  - "RxVerify • DevOps FA1"
  - Brand mark: "✚ RxVerify"

## Creative Direction
- Tone preset: **polished**
- Creative direction: **quiet premium product film for a clinical prescription handoff system**
- Interpretation: Restrained energy. Longer holds. Confidence through precision. No chaotic cuts. Emerald accents pulse subtly on key reveals. Text reads fully before moving on. The verification ID is the visual anchor — it appears in every scene.
- Angle: A clinical precision product film for a DevOps classroom project that actually works: three roles, one verification ID, zero ambiguity. The joke is how seriously a college prototype takes prescription handoff — and it earns it.
- Hook: Black screen. A single verification ID types out in JetBrains Mono, emerald on white, character by character: **RX-2F2D443F7D**
- Outro / punchline: Full screen centered three lines: "Secure prescription handoff." / "Doctor to pharmacist." / "Verified." Then brand mark.
- Avoid:
  - Generic SaaS language ("streamline your workflow")
  - Abstract filler visuals
  - Unrelated visual redesign

## Visual Identity
- Background: **#f0f5f1** (--paper)
- Text: **#0d1b12** (--ink)
- Accent: **#0a7a3d** (--emerald)
- Muted: **#4a6b5a** (--muted)
- Card: **#ffffff** (--card)
- Line: **#c8d8ce** (--line)
- Display font: **Space Grotesk** (headings, brand, stat values, step numbers, verification ID labels)
- Body font: **Inter** (UI, paragraphs, form labels)
- Mono font: **JetBrains Mono** (verification IDs, code snippets, patient references)
- Visual references from the project:
  - `.verification-id` — the hero element (monospace, large, bordered, emerald bg)
  - `.step-card` with `.step-number` (01/02/03)
  - `.stat-card` with `.stat-value` (large emerald numbers)
  - `.status.pill` (active=emerald, revoked=alert)
  - `.form-grid` prescription form
  - `.verify-form` minimal centered form
  - `.result-card` with `.details` grid
  - Admin stats grid + nav links + tables with status pills

## Storyboard (from brag-plan.md)

### Scene 1 — Hook: The ID — 3s
Black → single verification ID types out character-by-character: **RX-2F2D443F7D** (JetBrains Mono, clamp 1.5-2rem, emerald #0a7a3d on white, bordered 2px, padded). Holds 1.5s settled.
Sequential/interaction: **yes** — types out character by character (~0.06s/char), then border draws in (0.3s).
Audio intent: Tension → resolution. Keyboard ticks per character. Clean *click* on border lock.
Audio-coupled idea: Typed text with subtle key ticks.
Music: Bed starts -18dB, fades in 0.5s.
Transition mood: **clean crossfade** → Scene 2

### Scene 2 — Doctor Issues — 5s
Doctor portal form (form-grid layout). Cursor fills: Patient name, Medicine, Dosage, Instructions. "Create verification ID" button clicked (ripple). RX-ID slams in large (`.verification-id` style), holds 1.5s. Doctor name readonly visible.
Sequential/interaction: **yes** — form fields fill sequentially (0.3s each), button press simulated, ID reveals fast-in then holds.
Audio intent: Purposeful. Form filling = subtle key ticks. Submit = decisive click. ID reveal = soft card chime.
Audio-coupled idea: Sequential form fill with key ticks; button click; card arrival chime.
Music: Continues bed. Beat at ~6.8s for submit moment.
Transition mood: **clean wipe left** → Scene 3

### Scene 3 — Pharmacist Verifies — 5s
Verification page (minimal, centered). ID types in (uppercase). "Verify now" clicked. Result card flips in (3D flip 0.4s): **Verified** status pill (emerald), verification ID hero, details grid (Patient, Doctor, Clinic, Medicine, Dosage, Issue date, Status). "Mark as Received" button appears → clicked → badge updates to *Received* with timestamp.
Sequential/interaction: **yes** — ID types, button click, card 3D flip, details grid items arrive one by one (0.15s stagger), Receive button click.
Audio intent: Clinical precision. Type → click → flip whoosh → stagger chimes → final click.
Audio-coupled idea: Typed ID with key ticks; 3D flip with whoosh; staggered grid reveals on beat-grid; Receive click.
Music: Beat at ~11.2s for verify moment. Grid staggers on beat-grid (every other beat).
Transition mood: **soft crossfade** → Scene 4

### Scene 4 — Admin Oversees — 4s
Admin dashboard. Three stat cards count up simultaneously: Hospitals **3**, Doctors **5**, Pharmacists **4** (stat-value, Space Grotesk 2.5rem, emerald). Nav links row: "View All Hospitals" → hard cut to Hospitals table with action buttons → Hospital detail with nested doctors/pharmacists tables (status pills: active/revoked).
Sequential/interaction: **yes** — 3 stat cards count up together (0.8s ease-out), then nav click, table rows fade in staggered (0.1s), detail view push.
Audio intent: Authority. Count-up = satisfying. Table = clean order.
Audio-coupled idea: Stat count-up synchronized (one chime per card on beat). Table row arrivals subtle.
Music: Beat at ~15.5s for stats. Beat-grid for table rows.
Transition mood: **clean crossfade** → Scene 5

### Scene 5 — Outro — 3s
Centered, generous whitespace:
**Secure prescription handoff.** (Space Grotesk, clamp 2.25-3.5rem, --ink)
**Doctor to pharmacist.** (Space Grotesk, same)
**Verified.** (Space Grotesk, emerald #0a7a3d)
Small: *RxVerify • DevOps FA1* (Inter, --muted)
Brand mark: **✚ RxVerify** (Space Grotesk 1.35rem, emerald cross, --ink text)
Holds 2s settled.
Sequential/interaction: **yes** — three lines type out sequentially (0.4s each, 0.2s gap), brand mark fades in last.
Audio intent: Finality. Quiet confidence.
Audio-coupled idea: Three headline lines type with key ticks (slower, deliberate). Brand mark fade with subtle swell.
Music: Fades out over last 1.5s. Final chord resolves.
Transition mood: **hold → end**

---

## Audio
- Audio role: **warm bed with professional restraint**
- Audio arc: Bed fades in → supports sequential reveals on beat → fades cleanly on final punchline
- Music: **happy-beats-business-moves-vol-1-by-ende-dot-app.mp3** (in `assets/music/`)
- Music treatment: Start at 0:00, volume -18dB bed, fade in 0.5s, fade out last 1.5s. Beat sync for sequential reveals (stat cards, step cards, grid items).
- Music cue guidance: Preset exists (110 BPM). Strong cues at ~2.1s (hook lock), ~6.8s (doctor form submit), ~11.2s (pharmacist verify), ~15.5s (admin stats). Beat-grid windows for 3 stat cards (every other beat), 3 step cards, details grid items.
- Audio-reactive treatment: **subtle**; emerald glow on brand mark and verification ID breathes with music RMS (0.02-0.05 intensity). No waveform bars.
- Audio-coupled moments:
  - Scene 1: Typing verification ID → keyboard ticks
  - Scene 2: Form submit → click + card arrival
  - Scene 3: Verify button → click + result card flip + "Mark as Received" click
  - Scene 4: Stat cards count up → one chime per card on beat
- SFX selection guidance: Sparse, motion-matched. Keyboard ticks for typing, clean clicks for buttons, soft card-arrival chimes for reveals, subtle whoosh for 3D flip. Prefer low high-frequency-risk sounds from `assets/sfx/` for repeated/polished moments.
- SFX analysis guidance: Use `/Users/yashsiphone/.hermes/skills/brag/assets/sfx/sfx-analysis.md` for selection. Lower high-frequency-risk for repeated moments.
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume based on the implemented animation.
- Audio files: Music copied to `assets/music/`. Hyperframes copies selected SFX into `assets/sfx/`.

## Hyperframes Instructions
Load the Hyperframes domain skills (`hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-cli`) to create or update the composition in `<output-dir>/composition/`. /brag is its own workflow — do not enter the `hyperframes` entry-point intent interview or route into its generic promo / launch-video workflow.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds (target 20s).
- Include the planned music/SFX layer.
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Hyperframes decides exact animation timing and should ignore cues that hurt readability, scene pacing, or the product story.
- Major reveals may move toward nearby strong cues within about 0.15s. Smaller entrances may align to nearby beat points within about 0.10s. Use only 1-3 strong cue locks in a 15-25s video unless the edit clearly benefits from more.
- Use SFX to support motion and interaction: card sounds for card-like reveals, short announcement cues for major payoffs, key/click sounds for text or user actions, and restraint when the edit is already busy.
- Honor planned music treatment such as fade-outs, ducking, beat-aligned reveals, or letting a final SFX ring over the music, using the best Hyperframes-supported implementation.
- When music is present and the treatment is not `none`, consider Hyperframes audio-reactive workflow: extract audio data and use RMS/frequency bands for subtle, brand-specific motion. Good targets are glow, depth, background warmth, card presence, title emphasis, or other existing visual elements. Avoid waveform/equalizer visuals, musical-note graphics, generic particle systems, strobing, or heavy pulsing.
- Use local assets for audio and any required runtime/media dependencies when possible.
- Run `hyperframes check` before render — it is brag's single gate.
- Keep creation and rendering local. Remote or publishing workflows require a separate explicit user request.

## Self-Review Checklist (Pre-Render)
- [ ] Composition brief exists at `<output-dir>/composition-brief.md`
- [ ] Brief clearly identifies exact product moments to show
- [ ] Composition uses current Hyperframes workflow, not hardcoded /brag template
- [ ] Music file copied to `<output-dir>/composition/assets/music/`
- [ ] At least one visual element subtly reacts to music (audio-reactive treatment present), or extraction failure documented
- [ ] At least 1 major tween beat-locked to strong cue within ±0.15s, marked `// beat-locked`
- [ ] Sequential events snap to consecutive `beats[]` timestamps (±0.10s), marked `// beat-grid`
- [ ] Composition shows at least one real UI/copy/visual element from project
- [ ] Every factual claim grounded in project (no invented capabilities)
- [ ] Total duration 15-25 seconds
- [ ] `hyperframes check` passes, or blocker documented