# G0 feasibility note (Phase 0, Days 1-3)

**Outcome: gate met on its stated terms** (one month of Delhi in Parquet with metadata,
plus this note). Neither fallback condition was triggered by my reading. The plan gives no
numeric threshold for "too low" or "too high", so both are judgments, with the numbers below.

Deliverable: data/interim/delhi_2024-01.parquet (9,920 rows = 31 days x 320 cells, 14 columns,
file metadata attached). Full evidence and caveats: notes/decisions.md.

## Checks

| Check (plan, Phase 0) | Result | Status |
|---|---|---|
| Repo, env, GEE project, tier | Earth Engine noncommercial, one project; configs in config/project.yaml | Done |
| Units, QA, regridding, collection filtering | Tropospheric column, mol/m2 x 1e6 = umol/m2. L3 built with validity > 50 (about qa_value > 0.5); no QA band, not changeable. Scale 1113.2 m (0.01 deg bins); real pixel ~5.5 x 3.5 km | Done |
| Valid fraction (daily cells viable?) | Jan 2024: 18 of 31 days with >=50% valid area; 5,387 of 9,920 cell-days observed (54.3%). Apr 2024: 28 of 30 days. Winter is thin; cloud-driven gaps | Done, daily path kept |
| Version plot (D3) | Algorithm changes 2022-07-17, 2024-11-16, 2025-11-22. Desert control: no version offset (~0.1 umol/m2). Train 1.6.0+1.7.0, test 1.8.0 | Locked |
| Weather latency, BLH, live speed (D4) | BLH in ERA5 hourly (28 km), none in ERA5-Land. Latest data 6 days behind (plan assumed 2-3 months). Parity vs ERA5-Land: wind/temperature/pressure r ~0.99, dewpoint r 0.955. One single-hour fetch 1.6 s | Provisional (ERA5 only; confirm in Phase 3 ablation) |
| Overpass matching (D4) | Observation time over the box moves 07:01-08:56 UTC within a month: per-day time from solar angles, weather interpolated between hours. Plan's "hour from longitude" rule replaced | Locked |
| Coastal check (D4) | Not applicable: all 320 NCR cells are land. Coastal modelling is out of scope (cells are masked and warned) | N/A |
| Quota (D5) | Cap 540,000 EECU-s/month. One month of Delhi export 7.6-7.8 EECU-s; 51 months ~400; three cities ~1,200 (~0.2% of cap). 20,000/day guard set | Done for export |
| Cell ID, grid, observed-cell rule (D2) | 0.05 deg, id "iy_ix" from integer indices, tested. Observed = valid >= 0.50; 30/50/70% moves mean NO2 by ~1.3% | Locked |
| NCR box, cell count (D8) | 76.80-77.80 E, 28.20-29.00 N: 320 cells (20 x 16) | Locked |
| Water mask (D8) | 320 of 320 cells land (max water 7.5%); cutoffs untested here | Done |
| CPCB access | Official portal is form-based (sources from 2020-21, current state unverified). Third-party Delhi CSVs exist; timezone is IST labelled UTC; no station coordinates; one station's NO2 looks inverted | Optional, Delhi only |
| Emitters | WRI GPPD via GEE, frozen to config/. Old snapshot; two closed plants excluded (Badarpur, Rajghat). emit_dist_km kept as a candidate; emit_cap_50km_mw dropped | Done, limits noted |
| Demo (D7) | Local run + pre-computed Delhi and Hyderabad polygons (plan default) | Locked |

## Carried into Phase 1 (not gate-blocking, my judgment)

- Add obs_utc_hour to every row (the Phase 0 Parquet stores the angles, not the hour).
- Measure the full live request: weather with lags, and the EECU cost of interactive calls.
- Quota alert policy at 50% and 80% of the monthly cap: confirm it exists.
- Count short archive days after 2025-11-22; settle the two-granule-day rule; repeat the
  50% threshold and negative-value checks on the full export (summer, monsoon).
- Resolve the open ground-data items before any use: station coordinates, Sirifort NO2.
- Verify other listed plants near each new city before using emitter features (Phase 5).

## Not established

- Whether the model works: no model, no ablation yet.
- Agreement with ground stations: not tested.
- Anything outside the NCR box, outside winter, or outside 2022-2026.