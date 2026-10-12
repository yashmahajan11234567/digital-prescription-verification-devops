# Brag Plan: RxVerify

## What is this app?
RxVerify is a digital prescription verification system where doctors issue tamper-evident prescriptions with unique IDs (RX-XXXXXXXXXX), pharmacists verify them instantly by entering the ID, and admins oversee hospitals, staff, and audit trails — all running locally on Kubernetes with full monitoring (Prometheus, Grafana, Loki).

## The angle
A clinical precision product film for a DevOps classroom project that actually works: three roles, one verification ID, zero ambiguity. The joke is how seriously a college prototype takes prescription handoff — and it earns it.

## Hook (first 2-3 seconds)
Black screen. A single verification ID types out in JetBrains Mono, emerald on white, character by character:
**RX-2F2D443F7D**
Sound: subtle keyboard ticks, then a clean *click* as the border locks in.

## Key moments (the middle)

1. **Doctor issues** — Cursor fills the prescription form (patient, medicine, dosage). Hits "Create verification ID." The RX-ID slams in, large, bordered, emerald. One beat hold.

2. **Pharmacist verifies** — Clean verification page. ID types in. "Verify now" clicked. Result card flips in: **Verified** pill, full prescription details in a details grid, "Mark as Received" button appears. Click. Badge updates: *Received*.

3. **Admin dashboard** — Three stat cards count up: Hospitals 3, Doctors 5, Pharmacists 4. Nav links: "View All Hospitals" → table with actions. Hospital detail shows nested doctors/pharmacists tables with status pills.

## Outro / punchline
Full screen, centered:
**Secure prescription handoff.**
**Doctor to pharmacist.**
**Verified.**
Small beneath: *RxVerify • DevOps FA1*
Fade to brand mark: ✚ RxVerify (Space Grotesk, emerald cross)

## User flow worth showing
Doctor logs in → fills prescription form → gets unique RX-ID → Pharmacist enters RX-ID → sees full prescription details → marks as received. Admin oversees hospitals/staff with tenant isolation.

## Tone
- Preset: **polished**
- Creative direction: **quiet premium product film for a clinical prescription handoff system**
- Interpretation: Restrained energy. Longer holds. Confidence through precision. No chaotic cuts. Emerald accents pulse subtly on key reveals. Text reads fully before moving on. The verification ID is the visual anchor — it appears in every scene.

## Format: landscape — 1920x1080
## Duration: 20 seconds

## Visual identity (from the project)
- Background: **#f0f5f1** (--paper)
- Accent: **#0a7a3d** (--emerald)
- Text: **#0d1b12** (--ink)
- Muted: **#4a6b5a** (--muted)
- Card: **#ffffff** (--card)
- Line: **#c8d8ce** (--line)
- Display font: **Space Grotesk** (headings, brand, stat values, step numbers, verification ID labels)
- Body font: **Inter** (UI, paragraphs, form labels)
- Mono font: **JetBrains Mono** (verification IDs, code snippets, patient references)
- Strongest visual element: **Verification ID display** (`.verification-id`) — monospace, large, bordered, emerald background, the ONE bold element

## Share copy (draft)
RxVerify: Secure prescription handoff from doctor to pharmacist. Verified by design. 🏥💊

## Audio direction
- Role: **warm bed with professional restraint**
- Music: **happy-beats-business-moves-vol-1-by-ende-dot-app.mp3** (upbeat but clean, ~110 BPM, cue preset available)
- Music treatment: Start at 0:00, volume -18dB bed, fade in 0.5s, fade out last 1.5s. Beat sync for sequential reveals (stat cards, step cards).
- Music cue guidance: Preset exists (110 BPM). Strong cues at ~2.1s (hook lock), ~6.8s (doctor form submit), ~11.2s (pharmacist verify), ~15.5s (admin stats). Beat-grid windows for 3 stat cards (every other beat), 3 step cards.
- Audio-reactive treatment: **subtle**; emerald glow on brand mark and verification ID breathes with music RMS (0.02-0.05 intensity). No waveform bars.
- SFX posture: **sparse, motion-matched**; keyboard ticks for typing ID, clean click for button presses, soft card-arrival chime for stat/step reveals, subtle whoosh for result card flip.
- Audio-coupled moments:
  - Scene 1: Typing verification ID → keyboard ticks
  - Scene 2: Form submit → click + card arrival
  - Scene 3: Verify button → click + result card flip + "Mark as Received" click
  - Scene 4: Stat cards count up → one chime per card on beat
- Restraint rule: Music never leads; it supports. SFX only on deliberate UI actions. No ambient noise.

## Storyboard

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

**Music mood for this video:** upbeat but clean, professional
**Audio summary:** Warm business bed at -18dB with beat-synced card reveals and stat count-ups; sparse motion-matched SFX (keyboard ticks for typing, clicks for buttons, chimes for arrivals, whoosh for flip); subtle audio-reactive emerald glow on hero elements; music fades cleanly on final punchline.