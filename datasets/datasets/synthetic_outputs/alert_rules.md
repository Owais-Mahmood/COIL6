# Alert Rules — DATA Project Sensor Datasets

## How to use this document

These are the alert threshold rules already encoded in the synthetic datasets.
The `status` and `alert_triggered` columns in every CSV are derived from
exactly these thresholds.

**You do not need to change these rules.** Implement them as specified and
your dashboard will correctly reproduce the status logic in the data.

If you want to adjust a threshold — for example, if you decide a more
conservative turbidity limit is appropriate for your chosen site context —
you may do so, but you must:

1. Document the change clearly in your technical report
2. Cite the standard or source you are using as justification
3. Note how your threshold differs from the baseline and why

The authoritative standards are listed at the bottom of this document.

---

## Status Levels

| Status | Meaning |
|--------|---------|
| `normal` | All readings within acceptable range. No action required. |
| `warning` | One or more readings approaching or exceeding a safe limit. Flag for review. |
| `critical` | One or more readings exceed a safety threshold. Immediate attention required. |

**Logic:** `status` is the worst level triggered by any single rule in that
row. `alert_triggered = 1` whenever status is `warning` or `critical`.

---

## Water Quality (`water_quality.csv`)

Three sites on a river/reservoir system. `site_downstream` has a higher
turbidity baseline than `site_upstream` due to agricultural runoff.
`site_reservoir` is the most stable.

**What turbidity actually measures:** the scattering of light by suspended
particles — sediment, algae, bacteria, organic matter. It is a public health
proxy: turbid water cannot be reliably disinfected because particles shield
bacteria from chlorine. Post-rainfall spikes in the Eastern Cape indicate
genuine pathogen transport risk, not merely cloudiness.

**Contamination event signature:** rain drives turbidity *up* and conductivity
*down* (dilution). A simultaneous spike in *both* turbidity and conductivity
suggests chemical or agricultural runoff, not plain sediment — this is the
key pattern to detect.

| Column | Warning | Critical | Standard |
|--------|---------|----------|----------|
| `ph` | < 6.5 or > 8.5 | < 6.0 or > 9.0 | SANS 241:2015 |
| `turbidity_ntu` | > 5 NTU | > 10 NTU | SANS 241:2015 |
| `conductivity_uS_cm` | > 500 µS/cm | > 1500 µS/cm | SANS 241:2015 |

**Status logic:** critical if ANY critical rule fires; warning if ANY warning
rule fires and no critical; normal otherwise.

---

## Soil Monitoring (`soil_monitoring.csv`)

Three sites with different land use. `site_irrigated` has the highest
baseline EC (salinity from irrigation inputs). `site_hillside` is the
driest — most likely to see moisture stress.

**Note on EC:** soil EC rises as moisture falls — dissolved salts concentrate
as water is removed. EC is therefore a proxy for salinity stress risk, and
inversely correlated with soil moisture.

| Column | Warning | Critical | Standard |
|--------|---------|----------|----------|
| `soil_moisture_vwc` | < 0.14 or > 0.45 | < 0.08 | FAO Paper 56 |
| `soil_ph` | < 5.5 or > 7.5 | < 4.5 or > 8.0 | FAO Paper 61 |
| `soil_ec_uS_cm` | > 800 µS/cm | > 2500 µS/cm | FAO Paper 61 |

`soil_moisture_vwc` is a fraction (0.0–1.0). Multiply by 100 for percentage.
0.14 = 14% VWC = lower bound of field capacity for most soils.

**Status logic:** critical if ANY critical rule fires; warning if ANY warning
rule fires and no critical; normal otherwise.

**Note on 2022–23 data:** the Eastern Cape experienced an unusually wet
two-year period. The moisture stress threshold (< 14% VWC) is not triggered
in this dataset. This is realistic — monitoring systems often go long periods
without certain alert types. Your dashboard should handle this gracefully.

---

## Pest Monitoring (`pest_monitoring.csv`)

Three crop sites. `site_orchard` has the highest baseline pest pressure;
`site_brassica` the lowest. Disease risk is a compound trigger — no single
sensor reading alone triggers it.

**Disease model:** based on Huber & Gillespie (1992). Fungal disease requires
temperature, humidity, *and* sustained leaf wetness simultaneously. Leaf
wetness above 0.6 (dimensionless, 0–1 scale) means conditions where fungal
spores can germinate and infect plant tissue.

| Rule | Warning | Critical | Standard |
|------|---------|----------|----------|
| `pest_trap_count` | ≥ 5 per interval | ≥ 20 per interval | FAO FAW IPM Guide 2018 |
| Disease moderate | T ∈ [15,28°C] AND RH > 75% AND leaf_wetness > 0.6 | — | Huber & Gillespie 1992 |
| Disease high | above conditions sustained ≥ 6 consecutive hours | ← this becomes critical | Huber & Gillespie 1992 |

**Status logic:** critical if trap_count ≥ 20 OR disease_high; warning if
trap_count ≥ 5 OR disease_moderate (and no critical); normal otherwise.

---

## Livestock Tracking (`livestock_tracking.csv`)

Two herds: `herd_cattle_A` and `herd_goat_B`. Accelerometer and GPS data
designed to detect illness, theft, and predator events.

**Accelerometer behaviour reference (Martiskainen et al. 2009):**

| Behaviour | Typical accel range |
|-----------|-------------------|
| Resting | ~1.0g |
| Standing / slow movement | ~1.05–1.2g |
| Active grazing / walking | ~1.2–1.5g |
| Fleeing / struggling | > 3.5g |

**Important:** low-activity alerts only fire during active hours (06:00–20:00).
Animals resting at night is normal behaviour — do not alert on it.

| Rule | Warning | Critical | Standard |
|------|---------|----------|----------|
| Low activity | accel < 1.08g sustained 4 readings, 06:00–20:00 only | — | Martiskainen 2009 |
| Geofence breach | distance from kraal > radius | — | Martiskainen 2009 |
| Flee / struggle | — | accel > 3.5g | Martiskainen 2009 |

**Geofence radii:**
- `herd_cattle_A`: 0.004° (~440 m) from kraal centre (−32.780°, 26.840°)
- `herd_goat_B`: 0.006° (~660 m) from kraal centre

**Status logic:** critical if accel > 3.5g; warning if low_activity OR
geofence breach (and no critical); normal otherwise.

---

## Infrastructure Events (`infrastructure_events.csv`)

Fixed monitoring node for farm gate and perimeter fence. Boolean event data,
not continuous readings. Use alongside `livestock_tracking.csv` — correlating
gate events with animal GPS proximity is a useful analysis task.

| Rule | Warning | Critical | Standard |
|------|---------|----------|----------|
| Gate at night | gate_open_event = 1, hour < 6 or ≥ 19 | — | Operational context |
| Fence breach | — | fence_breach_event = 1 | Operational context |

**Status logic:** critical if fence breach; warning if gate open at night;
normal otherwise.

---

## Security Events (`security_events.csv`)

Three nodes covering perimeter, interior, and communal spaces. Multi-sensor
fusion prevents false positives — no single sensor triggers a critical alert
except the panic button.

**Note on smoke_ppm:** this is a proxy reading from the MQ135 gas sensor,
not a calibrated smoke detector. Thresholds are indicative. A real deployment
would require a dedicated smoke/CO sensor for life-safety use.

**Intrusion fusion logic:** motion AND door_open AND vibration > 0.5 AND
night — all four conditions must be true simultaneously. This is standard
practice to avoid false positives.

| Rule | Warning | Critical | Standard |
|------|---------|----------|----------|
| Motion (deep night) | motion = 1, hour < 6 or ≥ 22 | — | CASAS / Cook 2013 |
| Smoke elevated | smoke_ppm > 35 | smoke_ppm > 200 OR flame_detected = 1 | SANS 1691:2007 |
| Intrusion (fusion) | — | motion AND door AND vibration > 0.5 AND night | CASAS / Cook 2013 |
| Panic button | — | panic_triggered = 1 | — |

**Status logic:** critical if intrusion fusion OR fire (smoke > 200 or flame)
OR panic; warning if motion at night (22:00–06:00) OR smoke > 35 ppm (and no
critical); normal otherwise.

---

## Standards Reference

| Reference | Full citation |
|-----------|--------------|
| SANS 241:2015 | South African National Standard — Drinking water, Parts 1 & 2 |
| FAO Paper 56 | Allen et al. (1998). Crop evapotranspiration. FAO Irrigation and Drainage Paper 56. Rome. |
| FAO Paper 61 | Ayers & Westcot (1994). Water quality for agriculture. FAO Irrigation and Drainage Paper 61. Rome. |
| FAO FAW IPM 2018 | FAO (2018). Fall Armyworm: Integrated Pest Management. Rome. |
| Huber & Gillespie 1992 | Huber, L. & Gillespie, T.J. (1992). Modelling leaf wetness in relation to plant disease epidemiology. Annual Review of Phytopathology, 30, 553–577. |
| Martiskainen 2009 | Martiskainen, P. et al. (2009). Cow behaviour pattern recognition using a three-dimensional accelerometer and support vector machines. Applied Animal Behaviour Science, 119(1–2), 32–38. |
| Cook et al. 2013 | Cook, D.J. et al. (2013). CASAS: A smart home in a box. Computer, 46(7), 62–69. |
| SANS 1691:2007 | South African National Standard — Household and similar electrical appliances: Smoke alarms. |
