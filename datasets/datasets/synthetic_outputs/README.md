# DATA Project — Synthetic IoT Environmental Monitoring Datasets

## Overview

Six synthetic sensor datasets for the DATA Project / COMP2850 Environmental
Monitoring Dashboard. Grounded in real NASA POWER hourly weather data for
Alice, Eastern Cape, South Africa (lat -32.78, lon 26.84), 2022-2023,
resampled to 15-minute intervals.

**These are synthetic datasets** calibrated against authoritative standards
(SANS 241, FAO, WHO). They are not real sensor readings. They are intended
for student dashboard development and testing.

---

## Files

| File | Domain | Sites/nodes |
|------|--------|-------------|
| water_quality.csv | Water quality monitoring | site_upstream, site_downstream, site_reservoir |
| soil_monitoring.csv | Soil condition monitoring | site_riverside, site_hillside, site_irrigated |
| pest_monitoring.csv | Pest & crop disease | site_maize, site_brassica, site_orchard |
| livestock_tracking.csv | Animal GPS & activity | herd_cattle_A, herd_goat_B |
| infrastructure_events.csv | Gate & fence events | infrastructure_gate |
| security_events.csv | Community security | node_perimeter, node_interior, node_communal |

---

## Universal Columns (all files)

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | ISO 8601, 15-min intervals, 2022-01-01 to 2023-12-31 |
| site_id | string | Sensor node identifier |
| status | string | "normal" / "warning" / "critical" |
| alert_triggered | int (0/1) | 1 when status is warning or critical |

Additional `alert_*` columns give granular breakdown of what triggered the alert.
Pass-through `wx_*` columns give the underlying weather context.

---

## Sensor Columns by File

### water_quality.csv
| Column | Unit | Sensor |
|--------|------|--------|
| ph | pH units | DFRobot pH probe |
| turbidity_ntu | NTU | DFRobot turbidity |
| conductivity_uS_cm | µS/cm | DFRobot conductivity |
| water_temperature_c | °C | BME280 (waterproofed probe) |
| water_level_cm | cm | DFRobot water level |
| light_lux | lux | BH1750 (algae risk proxy) |

**What turbidity measures:** the scattering of light by suspended particles —
sediment, algae, bacteria, organic matter. High turbidity is a public health
proxy: turbid water cannot be reliably disinfected because particles shield
bacteria from chlorine. In the Eastern Cape context (severe soil erosion in
the Karoo/Great Fish River catchment), post-rainfall turbidity spikes are a
genuine indicator of pathogen transport risk, not merely aesthetic cloudiness.
A simultaneous spike in both turbidity AND conductivity indicates chemical
or agricultural runoff contamination rather than plain sediment.

**Thresholds (SANS 241:2015):**
- Turbidity: warning >5 NTU; critical >10 NTU
- pH: warning outside 6.5-8.5; critical outside 6.0-9.0
- Conductivity: warning >500 µS/cm; critical >1500 µS/cm

### soil_monitoring.csv
| Column | Unit | Sensor |
|--------|------|--------|
| soil_moisture_vwc | fraction (0-1) | Capacitive soil moisture |
| soil_ph | pH units | DFRobot pH probe |
| soil_ec_uS_cm | µS/cm | DFRobot conductivity |
| air_temperature_c | °C | BME280 |
| relative_humidity_pct | % | BME280 |
| pressure_hPa | hPa | BME280 |
| light_lux | lux | BH1750 |

**Thresholds (FAO Irrigation Papers 56, 61):**
- Moisture: warning <14% or >45% VWC; critical <8% VWC
- pH: warning outside 5.5-7.5; critical outside 4.5-8.0
- EC: warning >800 µS/cm; critical >2500 µS/cm

### pest_monitoring.csv
| Column | Unit | Sensor |
|--------|------|--------|
| air_temperature_c | °C | BME280 |
| relative_humidity_pct | % | BME280 |
| leaf_wetness_0_1 | 0-1 | DFRobot leaf wetness |
| light_lux | lux | BH1750 |
| vibration_level | 0-1 | MPU6050 (trap disturbance) |
| pest_trap_count | count | Derived from trap sensor |

**Thresholds (FAO FAW IPM Guide 2018; Huber & Gillespie 1992):**
- Pest: warning trap_count >=5; critical >=20
- Disease: warning = T∈[15,28°C] AND RH>75% AND leaf_wetness>0.6;
           critical = above sustained for 6+ hours

### livestock_tracking.csv
| Column | Unit | Sensor |
|--------|------|--------|
| latitude | degrees | GPS module |
| longitude | degrees | GPS module |
| accel_mag_g | g | MPU6050 accelerometer |
| ambient_temperature_c | °C | BME280 |

**Thresholds (Martiskainen et al. 2009):**
- warning: accel <1.08g sustained 4 readings (possible illness) OR geofence breach
- critical: accel >3.5g sustained (possible theft/fleeing)

### infrastructure_events.csv
| Column | Unit | Sensor |
|--------|------|--------|
| ambient_temperature_c | °C | BME280 |
| gate_open_event | 0/1 | Reed switch |
| fence_breach_event | 0/1 | Vibration sensor |
| vibration_level | 0-1 | MPU6050 |

**Thresholds:** warning = gate open at night; critical = fence breach

### security_events.csv
| Column | Unit | Sensor |
|--------|------|--------|
| motion_detected | 0/1 | PIR |
| door_open | 0/1 | Reed switch |
| vibration_level | 0-1 | DFRobot vibration |
| smoke_ppm | ppm | MQ135 |
| sound_db | dB | DFRobot sound |
| light_lux | lux | BH1750 |
| flame_detected | 0/1 | DFRobot flame sensor |
| panic_triggered | 0/1 | DFRobot panic button |

**Thresholds (SANS 1691:2007; CASAS dataset):**
- warning: motion at night OR smoke >35 ppm
- critical: intrusion (motion+door+vibration at night) OR fire (smoke>200 OR flame)
            OR distress (panic button)

---

## Temporal Backbone

All datasets share real NASA POWER hourly weather for Alice (lat -32.78, lon 26.84),
resampled to 15-minute intervals. Rain events coherently drive turbidity spikes
(water), soil moisture rises, and animal movement patterns simultaneously.

Wet season: November-March. Dry season: May-September.

Rain threshold: >2.0 mm/hr (meaningful convective rainfall; sub-2mm values in
MERRA-2 gridded reanalysis include interpolation artefacts and drizzle events
that would not trigger real-world sensor responses).

---

## Missing Data

NaN values injected at realistic rates:
- Water quality: ~3% (stable river monitoring)
- Soil: ~4% (field conditions, occasional probe fouling)
- Pest: ~4% (field conditions)
- Livestock: ~5% (harsher field hardware; collar charging gaps)
- Gate/infrastructure: ~1% (fixed, more reliable hardware)
- Security: ~2% (indoor/fixed hardware)

Handle NaN in your dashboard — do not assume complete data.

---

## Causal Ground Truth (known relationships encoded in the data)

turbidity       <- rain_intensity(lag 30min) x site_multiplier
conductivity    <- dry_season_factor x rain_dilution
soil_moisture   <- exponential_decay + rain_infiltration
soil_ec         <- 1/soil_moisture (concentration effect)
trap_count      <- NegBin(rate = f(temp, humidity, wet_season))
disease_risk    <- T in [15,28C] AND RH>75% AND leaf_wetness>0.6 sustained >=6hr
accel           <- behaviour_state(time_of_day, temperature)
alert_intrusion <- motion AND door_open AND vibration>0.5 AND night

These relationships are the "ground truth" — a well-built analysis component
should be able to recover them from the data.

---

## Reproducibility

numpy.random.default_rng(seed=2850). Re-running generate_datasets.py
produces identical output. Seed = COMP2850.

---

## Standards

- SANS 241:2015 — South African National Standard for drinking water quality
- FAO Irrigation Paper 56 — crop water requirements and stress thresholds
- FAO Irrigation Paper 61 — salinity and EC thresholds for irrigation
- FAO FAW IPM Guide 2018 — Fall Armyworm integrated pest management
- Huber & Gillespie (1992) Annual Review of Phytopathology — leaf wetness and disease
- Martiskainen et al. (2009) — livestock accelerometer behaviour classification
- CASAS Smart Home dataset (Cook et al. 2013) — PIR/door event rate calibration
- SANS 1691:2007 — CO and smoke alarm thresholds
- NASA POWER MERRA-2 — weather spine: https://power.larc.nasa.gov

---

## Licence

Synthetic data generated for academic use within the DATA Project / COMP2850.
