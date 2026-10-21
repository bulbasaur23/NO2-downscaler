# G0 feasibility note (Phase 0, Days 1-3), revised after Phase 1.2

**Outcome: gate met on its stated terms** (one month of Delhi in Parquet with metadata,
plus this note). Neither fallback condition was triggered by my reading. The plan gives no
numeric threshold for "too low" or "too high", so both are judgments, with the numbers below.

Rows marked (revised) were corrected or extended with the full-window results from
Phase 1.2 (51 months, 2022-07 to 2026-09). Earlier wording is in the Git history.

Deliverable: data/interim/delhi_2024-01.parquet (9,920 rows = 31 days x 320 cells, 14 columns,
file metadata attached). Full evidence and caveats: notes/decisions.md.

## Checks

| Check (plan, Phase 0) | Result | Status |
|---|---|---|
| Repo, env, GEE project, tier | Earth Engine noncommercial, one project; configs in config/project.yaml | Done |
| Units, QA, regridding, collection filtering | Tropospheric column, mol/m2 x 1e6 = umol/m2. L3 built with validity > 50 (about qa_value > 0.5); no QA band, not changeable. Scale 1113.2 m (0.01 deg bins); real pixel ~5.5 x 3.5 km | Done |
| Valid fraction (daily cells viable?) (revised) | Full window 2022-07 to 2026-09 (1,553 days): 74% of cell-days have a NO2 value. Share of days observed: monsoon 48%, winter 81%, pre-monsoon 89%, post-monsoon 81%. By month: Jul 32%, Aug 36%, Jan 67%, others 80-92%. Monsoon is the thinnest season (this note first said winter, from Jan 2024 alone: corrected). Gaps are cloud-driven; monsoon values describe clear-sky conditions only | Done, daily path kept |
| Version plot (D3) (revised) | Algorithm changes 2022-07-17, 2024-11-16, 2025-11-22. Desert control: no version offset (~0.1 umol/m2). Train 1.6.0+1.7.0 (1,217 days, 865 observed); version-shift test 1.8.0 from 2025-11-23 (312 days, 229 observed). 2025-11-22 excluded (mixed version label) | Locked |
| Weather latency, BLH, live speed (D4) | BLH in ERA5 hourly (28 km), none in ERA5-Land. Latest data 6 days behind (plan assumed 2-3 months). Parity vs ERA5-Land: wind/temperature/pressure r ~0.99, dewpoint r 0.955. One single-hour fetch 1.6 s | Provisional (ERA5 only; confirm in Phase 3 ablation) |
| Overpass matching (D4) (revised) | Observation time over the box varies 06:33-08:59 UTC over the full window (two sampled months: 07:01-08:56), derived from solar angles. On 154 of 1,531 days (10%) the cells' own times differ by more than 15 min (cause under test: two-orbit overlap vs an azimuth-averaging flaw in my pull). Rule: weather is matched per cell at its own time, interpolated between hours. Plan's "hour from longitude" rule replaced | Rule locked; cause of the spread open |
| Coastal check (D4) | Not applicable: all 320 NCR cells are land. Coastal modelling is out of scope (cells are masked and warned) | N/A |
| Quota (D5) (revised) | Cap 540,000 EECU-s/month; 20,000/day guard set. Batch export 7.6-7.8 EECU-s per month. Interactive per-day pull ~9 EECU-s per month pulled (daily counter 458 after 51 month-pulls, assumes a reset at 12:30 IST). Full Delhi window ~460 (0.09% of cap), three cities ~1,400. The monthly counter is unreliable (went down once) and is not used | Done for NO2; weather cost not measured |
| Cell ID, grid, observed-cell rule (D2) | 0.05 deg, id "iy_ix" from integer indices, tested. Observed = valid >= 0.50; 30/50/70% moves mean NO2 by ~1.3% (Jan 2024 only; to repeat by season) | Locked |
| NCR box, cell count (D8) | 76.80-77.80 E, 28.20-29.00 N: 320 cells (20 x 16) | Locked |
| Water mask (D8) | 320 of 320 cells land (max water 7.5%); cutoffs untested here | Done |
| CPCB access | Official portal is form-based (sources from 2020-21, current state unverified). Third-party Delhi CSVs exist and parse, but station comparison failed (daily and monthly Spearman near zero; one station's record has an unexplained step; timezone is IST labelled UTC; no coordinates) | Parked |
| Emitters | WRI GPPD via GEE, frozen to config/. Old snapshot; two closed plants excluded (Badarpur, Rajghat). emit_dist_km kept as a candidate; emit_cap_50km_mw dropped | Done, limits noted |
| Demo (D7) | Local run + pre-computed Delhi and Hyderabad polygons (plan default) | Locked |

## Carried into Phase 1 (updated)

- Add obs_utc_hour to every row, per cell (step 1.3); settle the cause of the 10% flagged
  days (scripts/30b) and, if it is the azimuth flaw, re-pull with sin/cos.
- Measure the full live request: weather with lags (the NO2 part of the interactive pull
  is measured).
- Repeat the 50% threshold check by season on the full export; settle the
  two-granule-day rule.
- Phase 3: a rule for zero/negative targets (34 negatives in the window) and robustness
  to extreme values (max 1,157 umol/m2; real episode vs artefact undecided).
- Quota alert policy at 50% and 80% of the monthly cap: unconfirmed, low priority.
- Verify other listed plants near each new city before using emitter features (Phase 5).

## Not established

- Whether the model works: no model, no ablation yet.
- Agreement with ground stations: tested once (one Delhi station, 2024-25) and no
  relationship was found; parked, so the model is validated against TROPOMI only.
- Anything outside the NCR box or outside 2022-2026.