# water_quality.csv

## What this is

Synthetic sensor readings from three water monitoring sites on a river
system near Alice, Eastern Cape, South Africa. Covers 2022-01-01 to
2023-12-31 at 15-minute intervals (70,077 readings per site; 210,231 total).

Designed for the DATA Project / COMP2850 Environmental Monitoring Dashboard.
Data is synthetic but calibrated against real NASA POWER weather for the
location and against SANS 241:2015 water quality standards.

### Sites

| site_id | Description |
|---------|-------------|
| `site_upstream` | Reference point above agricultural land — cleanest baseline |
| `site_downstream` | Below farming activity — elevated turbidity and conductivity from runoff |
| `site_reservoir` | Community dam — most stable; reservoir buffering effect on turbidity |

---

## Column glossary

| Column | Unit | Sensor | What it means |
|--------|------|--------|---------------|
| `timestamp` | ISO 8601 datetime | — | 15-minute interval timestamp |
| `site_id` | string | — | Monitoring site identifier |
| `ph` | pH units (0–14) | DFRobot pH probe | Acidity/alkalinity of the water. 7.0 = neutral. Below 6.5 or above 8.5 is outside the SANS 241 aesthetic range. |
| `turbidity_ntu` | NTU | DFRobot turbidity sensor | Cloudiness of the water caused by suspended particles. Higher = more particles. Not just aesthetic — turbid water resists disinfection. |
| `conductivity_uS_cm` | µS/cm | DFRobot conductivity probe | Concentration of dissolved salts and minerals. Rises in dry season as water evaporates; drops during rain (dilution). A simultaneous rise in both conductivity AND turbidity may indicate contamination. |
| `water_temperature_c` | °C | BME280 (waterproofed probe) | Water temperature. Affects dissolved oxygen levels and bacterial growth rates. |
| `water_level_cm` | cm | DFRobot water level sensor | Height of water. Rises sharply after rain events; decays exponentially during dry periods. |
| `light_lux` | lux | BH1750 light sensor | Ambient light at the water surface. Used as a proxy for algae bloom risk — high light + warm water + slow flow increases algal growth potential. |
| `status` | normal / warning / critical | derived | Overall alert status for this row. See alert_rules.md for threshold logic. |
| `alert_triggered` | 0 or 1 | derived | 1 when status is warning or critical. |
| `alert_ph` | 0 or 1 | derived | 1 when pH outside warning range (< 6.5 or > 8.5). |
| `alert_turbidity` | 0 or 1 | derived | 1 when turbidity > 5 NTU (warning threshold). |
| `alert_turbidity_crit` | 0 or 1 | derived | 1 when turbidity > 10 NTU (critical threshold). |
| `alert_conductivity` | 0 or 1 | derived | 1 when conductivity > 500 µS/cm. |
| `wx_temp_c` | °C | NASA POWER (weather backbone) | Ambient air temperature at time of reading. |
| `wx_rh_pct` | % | NASA POWER | Relative humidity. |
| `wx_rain_mm_hr` | mm/hr | NASA POWER | Rainfall rate. Turbidity spikes follow rain events with a ~30-minute lag. |

---

## Keywords

**NTU** — Nephelometric Turbidity Unit. The standard unit for measuring
turbidity. Named after the nephelometer instrument, which measures light
scattered by particles at a 90° angle.

**Turbidity** — a measure of water cloudiness caused by suspended particles
(sediment, algae, bacteria, organic matter). High turbidity is a public health
proxy: particles shield bacteria from chlorine, making disinfection unreliable.

**Conductivity / EC** — electrical conductivity, a measure of dissolved ions
in water. Pure water does not conduct electricity; dissolved salts do.
Higher EC = more dissolved material. In rivers, EC rises during dry periods
(concentration) and falls during rain (dilution).

**pH** — a logarithmic scale of hydrogen ion concentration. pH 7 = neutral;
below 7 = acidic; above 7 = alkaline. Drinking water standards target 6.5–8.5.

**SANS 241:2015** — South African National Standard for drinking water
quality. The benchmark for all alert thresholds in this dataset.

**Contamination event** — a simultaneous spike in both turbidity AND
conductivity. Rain alone drives turbidity up and conductivity down (dilution
effect), so a combined spike is the signature of chemical or agricultural
runoff input rather than plain sediment wash.

---

## How to load and explore

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('water_quality.csv', parse_dates=['timestamp'])

# View one site
upstream = df[df.site_id == 'site_upstream'].set_index('timestamp')

# Plot turbidity over time
upstream['turbidity_ntu'].plot(figsize=(14, 4), title='Upstream turbidity (NTU)')
plt.axhline(5,  color='orange', linestyle='--', label='Warning (5 NTU)')
plt.axhline(10, color='red',    linestyle='--', label='Critical (10 NTU)')
plt.legend(); plt.show()

# Compare turbidity during rain vs dry periods
rainy = df[df.wx_rain_mm_hr > 2.0]['turbidity_ntu'].mean()
dry   = df[df.wx_rain_mm_hr <= 2.0]['turbidity_ntu'].mean()
print(f'Mean turbidity — rainy: {rainy:.1f} NTU | dry: {dry:.1f} NTU')

# Alert rate by site
df.groupby('site_id')['status'].value_counts(normalize=True).unstack()

# Spot contamination signature: turbidity and conductivity both elevated
contamination = df[
    (df.turbidity_ntu > df.turbidity_ntu.quantile(0.95)) &
    (df.conductivity_uS_cm > df.conductivity_uS_cm.quantile(0.75))
]
print(f'Possible contamination events: {len(contamination)} rows')
```

---

## Known characteristics

- Rain threshold in weather backbone: > 2.0 mm/hr (meaningful convective
  rainfall; sub-2mm values in the MERRA-2 reanalysis include drizzle and
  interpolation artefacts)
- Turbidity spikes follow rain with a ~30-minute lag (two 15-min intervals)
- ~3% of sensor rows contain NaN values (realistic dropout and LoRa packet loss)
- Handle NaN before computing means or plotting — do not assume complete data
