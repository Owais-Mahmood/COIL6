"""
DATA Project — Dataset Causal Validation
=========================================
Confirms that the causal relationships encoded in the synthetic datasets
are actually present in the data. Run this alongside validate_alert_rules.py
any time the generator is modified.

Usage:
    python validate_datasets.py

Checks 23 causal and behavioural claims across all six datasets.
Each claim maps to a relationship documented in the per-dataset READMEs
and the generate_datasets.py comments.
"""

import pandas as pd
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
OUT  = HERE / 'synthetic_outputs'

results = []

def check(domain, claim, passed, detail):
    icon = 'PASS' if passed else 'FAIL'
    results.append((domain, claim, passed, detail))
    print(f'  [{icon}] {claim}')
    if not passed:
        print(f'         ↳ {detail}')


# ── Water Quality ─────────────────────────────────────────────────────────────
print('\n=== Water Quality ===')
w  = pd.read_csv(OUT / 'water_quality.csv', parse_dates=['timestamp'])
w['month'] = w.timestamp.dt.month
w['wet']   = w.month.isin([11,12,1,2,3])
up   = w[w.site_id == 'site_upstream'].reset_index(drop=True)
down = w[w.site_id == 'site_downstream'].reset_index(drop=True)

# 1. Turbidity rises significantly after rain
rainy = up[up.wx_rain_mm_hr > 2.0].turbidity_ntu.mean()
dry   = up[up.wx_rain_mm_hr <= 2.0].turbidity_ntu.mean()
ratio = rainy / dry
check('water', 'turbidity rises >1.5x after rain (rain > 2 mm/hr)',
      ratio > 1.5,
      f'rainy={rainy:.1f} NTU  dry={dry:.1f} NTU  ratio={ratio:.1f}x')

# 2. Downstream more turbid than upstream (agricultural runoff multiplier)
check('water', 'downstream turbidity > upstream (site multiplier)',
      down.turbidity_ntu.mean() > up.turbidity_ntu.mean() * 1.2,
      f'downstream={down.turbidity_ntu.mean():.1f}  upstream={up.turbidity_ntu.mean():.1f} NTU')

# 3. Conductivity higher in dry season (concentration effect)
ec_dry = up[~up.wet].conductivity_uS_cm.mean()
ec_wet = up[up.wet].conductivity_uS_cm.mean()
check('water', 'conductivity higher in dry season (>1.1x wet season)',
      ec_dry > ec_wet * 1.1,
      f'dry={ec_dry:.0f}  wet={ec_wet:.0f} µS/cm  ratio={ec_dry/ec_wet:.2f}x')

# 4. Turbidity/conductivity: rain drives them in OPPOSITE directions (correct physics)
r_tc = up.turbidity_ntu.corr(up.conductivity_uS_cm)
check('water', 'turbidity & conductivity negatively correlated (rain drives opposite directions)',
      r_tc < 0,
      f'Pearson r={r_tc:.3f} (rain: turbidity↑ conductivity↓ via dilution)')

# 5. Contamination signature: simultaneous high turbidity + high conductivity exists in data
both_high = up[
    (up.turbidity_ntu    > up.turbidity_ntu.quantile(0.95)) &
    (up.conductivity_uS_cm > up.conductivity_uS_cm.quantile(0.75))
]
check('water', 'contamination signature (simultaneous turbidity+conductivity spikes) exists',
      len(both_high) > 0,
      f'{len(both_high)} rows with turbidity >95th pct AND conductivity >75th pct')


# ── Soil Monitoring ───────────────────────────────────────────────────────────
print('\n=== Soil Monitoring ===')
s    = pd.read_csv(OUT / 'soil_monitoring.csv', parse_dates=['timestamp'])
s['month'] = s.timestamp.dt.month
s['wet']   = s.month.isin([11,12,1,2,3])
hill = s[s.site_id == 'site_hillside'].reset_index(drop=True)
riv  = s[s.site_id == 'site_riverside'].reset_index(drop=True)

# 6. Soil moisture decays in dry windows after rain
rain_idx = hill[hill.wx_rain_mm_hr > 5.0].index
ok = 0; checked = 0
for idx in rain_idx[:20]:
    start = idx + 2
    end   = min(idx + 16, len(hill) - 1)
    if end > start and hill.loc[start:end, 'wx_rain_mm_hr'].max() < 0.5:
        checked += 1
        if hill.loc[end, 'soil_moisture_vwc'] < hill.loc[start, 'soil_moisture_vwc']:
            ok += 1
check('soil', 'soil moisture decays during dry windows after rain',
      checked == 0 or ok >= checked * 0.7,
      f'decaying in {ok}/{checked} dry windows post-rain')

# 7. Soil EC inversely correlated with moisture (concentration effect)
r_ec = riv.soil_ec_uS_cm.corr(riv.soil_moisture_vwc)
check('soil', 'soil EC inversely correlated with moisture (r < -0.3)',
      r_ec < -0.3,
      f'Pearson r(EC, moisture) = {r_ec:.3f}')

# 8. Soil pH lower in wet season (acidification)
ph_wet = riv[riv.wet].soil_ph.mean()
ph_dry = riv[~riv.wet].soil_ph.mean()
check('soil', 'soil pH lower in wet season (acidification)',
      ph_dry > ph_wet,
      f'wet={ph_wet:.3f}  dry={ph_dry:.3f}')

# 9. Site irrigated has highest EC baseline
ec_by_site = s.groupby('site_id').soil_ec_uS_cm.mean()
check('soil', 'site_irrigated has highest EC baseline',
      ec_by_site.idxmax() == 'site_irrigated',
      f'{ec_by_site.round(0).to_dict()}')

# 10. Hillside is the driest site
check('soil', 'site_hillside has lowest mean soil moisture',
      s.groupby('site_id').soil_moisture_vwc.mean().idxmin() == 'site_hillside',
      f"{s.groupby('site_id').soil_moisture_vwc.mean().round(3).to_dict()}")


# ── Pest Monitoring ───────────────────────────────────────────────────────────
print('\n=== Pest Monitoring ===')
p     = pd.read_csv(OUT / 'pest_monitoring.csv', parse_dates=['timestamp'])
p['month'] = p.timestamp.dt.month
p['wet']   = p.month.isin([11,12,1,2,3])
maize = p[p.site_id == 'site_maize']

# 11. Leaf wetness higher when RH high
lw_hi_rh = maize[maize.relative_humidity_pct > 80].leaf_wetness_0_1.mean()
lw_lo_rh = maize[maize.relative_humidity_pct < 50].leaf_wetness_0_1.mean()
check('pest', 'leaf wetness higher when RH > 80% vs RH < 50% (>1.3x)',
      lw_hi_rh > lw_lo_rh * 1.3,
      f'high RH={lw_hi_rh:.3f}  low RH={lw_lo_rh:.3f}  ratio={lw_hi_rh/lw_lo_rh:.1f}x')

# 12. Trap counts higher in wet season
trap_wet = maize[maize.wet].pest_trap_count.mean()
trap_dry = maize[~maize.wet].pest_trap_count.mean()
check('pest', 'trap counts higher in wet season (>1.5x dry)',
      trap_wet > trap_dry * 1.5,
      f'wet={trap_wet:.2f}  dry={trap_dry:.2f}  ratio={trap_wet/trap_dry:.1f}x')

# 13. Disease high rows have elevated leaf wetness
lw_dh  = maize[maize.alert_disease_high == 1].leaf_wetness_0_1.mean()
lw_ndh = maize[maize.alert_disease_high == 0].leaf_wetness_0_1.mean()
check('pest', 'disease_high rows have higher mean leaf wetness (>1.3x normal)',
      lw_dh > lw_ndh * 1.3,
      f'during disease_high={lw_dh:.3f}  normal={lw_ndh:.3f}')

# 14. Vibration elevated when trap count high
vib_hi = maize[maize.pest_trap_count >= 5].vibration_level.mean()
vib_lo = maize[maize.pest_trap_count <  5].vibration_level.mean()
check('pest', 'mean vibration higher when trap_count >= 5 (trap disturbance)',
      vib_hi > vib_lo,
      f'trap>=5: {vib_hi:.4f}  trap<5: {vib_lo:.4f}  ratio={vib_hi/vib_lo:.2f}x')


# ── Livestock Tracking ────────────────────────────────────────────────────────
print('\n=== Livestock Tracking ===')
ls = pd.read_csv(OUT / 'livestock_tracking.csv', parse_dates=['timestamp'])
ls['hour'] = ls.timestamp.dt.hour
cattle = ls[ls.site_id == 'herd_cattle_A'].copy()
KLAT, KLON = -32.780, 26.840
cattle['dist'] = np.sqrt((cattle.latitude - KLAT)**2 + (cattle.longitude - KLON)**2)

# 15. Accel lower at night than daytime
night_g = cattle[(cattle.hour < 6)  | (cattle.hour >= 20)].accel_mag_g.mean()
day_g   = cattle[(cattle.hour >= 8) & (cattle.hour <= 16)].accel_mag_g.mean()
check('livestock', 'accel lower at night (resting) than daytime (>1.1x)',
      day_g > night_g * 1.1,
      f'night={night_g:.3f}g  day={day_g:.3f}g  ratio={day_g/night_g:.2f}x')

# 16. GPS closer to kraal at night
night_d = cattle[(cattle.hour < 6)  | (cattle.hour >= 19)].dist.mean()
day_d   = cattle[(cattle.hour >= 8) & (cattle.hour <= 16)].dist.mean()
check('livestock', 'GPS closer to kraal at night than daytime (<0.6x day distance)',
      night_d < day_d * 0.6,
      f'night dist={night_d:.5f}°  day dist={day_d:.5f}°  ratio={night_d/day_d:.2f}x')

# 17. Low-activity alert only during active hours
night_la = cattle[(cattle.hour < 6) | (cattle.hour > 20)].alert_low_activity.sum()
check('livestock', 'alert_low_activity never fires outside active hours (06:00–20:00)',
      night_la == 0,
      f'low_activity alerts outside active hours: {night_la}')

# 18. Flee events rare
flee_rate = cattle.alert_flee.mean()
check('livestock', 'flee events rare (< 1% of readings)',
      flee_rate < 0.01,
      f'flee rate = {flee_rate*100:.2f}%')


# ── Security Events ───────────────────────────────────────────────────────────
print('\n=== Security Events ===')
sec = pd.read_csv(OUT / 'security_events.csv', parse_dates=['timestamp'])
sec['hour'] = sec.timestamp.dt.hour
interior = sec[sec.site_id == 'node_interior']
motion_hr = interior.groupby('hour').motion_detected.mean()

# 19. Motion bimodal
morning    = motion_hr.loc[7:9].mean()
evening    = motion_hr.loc[18:22].mean()
midday     = motion_hr.loc[11:14].mean()
deep_night = motion_hr.loc[1:5].mean()
check('security', 'motion bimodal: morning & evening > midday (>1.3x) and > deep night',
      morning > midday * 1.3 and evening > midday * 1.3 and deep_night < midday * 0.5,
      f'morning={morning:.3f}  evening={evening:.3f}  midday={midday:.3f}  night={deep_night:.3f}')

# 20. Smoke elevated during cooking hours
cook_h  = ((interior.hour >= 7) & (interior.hour <= 9)) | \
          ((interior.hour >= 17) & (interior.hour <= 19))
cook_smoke  = interior[cook_h].smoke_ppm.mean()
other_smoke = interior[~cook_h].smoke_ppm.mean()
check('security', 'smoke elevated during cooking hours (>1.3x other times)',
      cook_smoke > other_smoke * 1.3,
      f'cooking={cook_smoke:.1f}  other={other_smoke:.1f}  ratio={cook_smoke/other_smoke:.1f}x')

# 21. Intrusion only at night
day_intr = sec[(sec.hour >= 6) & (sec.hour < 19)].alert_intrusion.sum()
check('security', 'alert_intrusion only fires at night',
      day_intr == 0,
      f'daytime intrusion alerts: {day_intr}')

# 22. Flame rows have much higher smoke
flame_on  = sec[sec.flame_detected == 1].smoke_ppm.mean()
flame_off = sec[sec.flame_detected == 0].smoke_ppm.mean()
check('security', 'flame_detected rows have much higher smoke_ppm (>5x)',
      flame_on > flame_off * 5,
      f'smoke when flame=1: {flame_on:.0f}  flame=0: {flame_off:.0f}  ratio={flame_on/flame_off:.0f}x')

# 23. Panic extremely rare
panic_rate = sec.panic_triggered.mean()
check('security', 'panic_triggered very rare (< 0.01% of readings)',
      panic_rate < 0.0001,
      f'panic rate = {panic_rate*100:.4f}%')


# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n{"="*60}')
passed = sum(1 for r in results if r[2])
failed = [r for r in results if not r[2]]
print(f'RESULT: {passed}/{len(results)} causal checks passed')
if failed:
    print(f'\n{len(failed)} FAILED:')
    for r in failed:
        print(f'  [{r[0]}] {r[1]}')
        print(f'    {r[3]}')
else:
    print('All checks passed.')
    print('Causal structure is consistent with documented ground truth.')
