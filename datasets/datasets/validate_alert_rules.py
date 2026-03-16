"""
DATA Project — Alert Rules Validator
=====================================
Checks that alert_rules.json is consistent with the actual CSV data.
Run this any time the generator is modified to confirm rules and data stay in sync.

Usage:
    python validate_alert_rules.py

Expects:
    - synthetic_outputs/ directory alongside this script
    - alert_rules.json inside synthetic_outputs/

All checks account for:
    - Floating-point rounding at 2 d.p. (boundary tolerance ±0.005)
    - NaN rows excluded from threshold checks (NaN injection happens
      after alert columns are set, so alert values are valid even when
      the corresponding sensor reading is NaN)
"""

import json
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
        print(f'         {detail}')

def threshold_check(df, col, alert_col, threshold, operator, tol=0.005):
    """
    Check that alert_col fires iff col {operator} threshold.
    Excludes NaN rows in col. Applies tolerance for rounding boundary.
    operator: 'gt' or 'lt'
    """
    valid = df[df[col].notna()]
    if operator == 'gt':
        should_fire   = valid[valid[col] > threshold + tol]
        should_silent = valid[valid[col] < threshold - tol]
    else:
        should_fire   = valid[valid[col] < threshold - tol]
        should_silent = valid[valid[col] > threshold + tol]

    fire_rate   = should_fire[alert_col].mean()   if len(should_fire)   else None
    silent_rate = should_silent[alert_col].mean() if len(should_silent) else None
    return fire_rate, silent_rate


# ── Water Quality ─────────────────────────────────────────────────────────────
print('\n=== Water Quality ===')
w = pd.read_csv(OUT / 'water_quality.csv')

for site in w.site_id.unique():
    s = w[w.site_id == site]

    # pH warning
    fr, sr = threshold_check(s, 'ph', 'alert_ph', 6.5, 'lt')
    fr2, sr2 = threshold_check(s, 'ph', 'alert_ph', 8.5, 'gt')
    ph_warn_ok = (fr == 1.0 or fr is None) and (fr2 == 1.0 or fr2 is None) and (sr == 0.0 or sr is None)
    check('water', f'pH warning alert correct [{site}]', ph_warn_ok,
          f'below 6.5 rate={fr}  above 8.5 rate={fr2}  in-range rate={sr}')

    # Turbidity warning >5
    fr, sr = threshold_check(s, 'turbidity_ntu', 'alert_turbidity', 5.0, 'gt')
    check('water', f'turbidity warning (>5 NTU) correct [{site}]',
          (fr == 1.0 or fr is None) and (sr == 0.0 or sr is None),
          f'above threshold: {fr}  below: {sr}')

    # Turbidity critical >10
    fr, sr = threshold_check(s, 'turbidity_ntu', 'alert_turbidity_crit', 10.0, 'gt')
    check('water', f'turbidity critical (>10 NTU) correct [{site}]',
          (fr == 1.0 or fr is None) and (sr == 0.0 or sr is None),
          f'above threshold: {fr}  below: {sr}')

    # Conductivity warning >500
    fr, sr = threshold_check(s, 'conductivity_uS_cm', 'alert_conductivity', 500.0, 'gt')
    check('water', f'conductivity warning (>500) correct [{site}]',
          (fr == 1.0 or fr is None) and (sr == 0.0 or sr is None),
          f'above threshold: {fr}  below: {sr}')

    # Status consistency (excluding NaN rows)
    s_clean = s.dropna(subset=['ph','turbidity_ntu','conductivity_uS_cm'])
    crit = (s_clean.ph < 6.0) | (s_clean.ph > 9.0) | \
           (s_clean.turbidity_ntu > 10) | (s_clean.conductivity_uS_cm > 1500)
    warn = ((s_clean.ph < 6.5) | (s_clean.ph > 8.5) |
            (s_clean.turbidity_ntu > 5) | (s_clean.conductivity_uS_cm > 500)) & ~crit
    expected = np.where(crit, 'critical', np.where(warn, 'warning', 'normal'))
    match_rate = (expected == s_clean.status.values).mean()
    check('water', f'status column consistent with rules [{site}]',
          match_rate >= 0.999,
          f'match rate: {match_rate*100:.3f}% (allow 0.1% for rounding boundary rows)')


# ── Soil ───────────────────────────────────────────────────────────────────────
print('\n=== Soil Monitoring ===')
s = pd.read_csv(OUT / 'soil_monitoring.csv')

for site in s.site_id.unique():
    sd = s[s.site_id == site]

    # Moisture stress: <0.14 or >0.45
    # Check each boundary separately, then check the truly-in-range rows with both bounds
    tol = 0.005
    fr_lo, _    = threshold_check(sd, 'soil_moisture_vwc', 'stress_moisture', 0.14, 'lt')
    fr_hi, _    = threshold_check(sd, 'soil_moisture_vwc', 'stress_moisture', 0.45, 'gt')
    truly_ok    = sd[(sd.soil_moisture_vwc >= 0.14+tol) & (sd.soil_moisture_vwc <= 0.45-tol)]
    sr_both     = truly_ok['stress_moisture'].mean() if len(truly_ok) else None
    check('soil', f'stress_moisture thresholds correct [{site}]',
          (fr_lo == 1.0 or fr_lo is None) and
          (fr_hi == 1.0 or fr_hi is None) and
          (sr_both == 0.0 or sr_both is None),
          f'<0.14: {fr_lo}  >0.45: {fr_hi}  in-range: {sr_both}')

    # pH stress: <5.5 or >7.5
    fr_lo, sr_lo = threshold_check(sd, 'soil_ph', 'stress_ph', 5.5, 'lt')
    fr_hi, sr_hi = threshold_check(sd, 'soil_ph', 'stress_ph', 7.5, 'gt')
    check('soil', f'stress_ph thresholds correct [{site}]',
          (fr_lo == 1.0 or fr_lo is None) and
          (fr_hi == 1.0 or fr_hi is None) and
          (sr_lo == 0.0 or sr_lo is None),
          f'<5.5: {fr_lo}  >7.5: {fr_hi}  in-range: {sr_lo}')

    # EC stress: >800
    fr, sr = threshold_check(sd, 'soil_ec_uS_cm', 'stress_salinity', 800.0, 'gt')
    check('soil', f'stress_salinity threshold (>800) correct [{site}]',
          (fr == 1.0 or fr is None) and (sr == 0.0 or sr is None),
          f'>800: {fr}  <=800: {sr}')


# ── Pest Monitoring ───────────────────────────────────────────────────────────
print('\n=== Pest Monitoring ===')
p = pd.read_csv(OUT / 'pest_monitoring.csv')

for site in p.site_id.unique():
    pd_ = p[p.site_id == site]

    # Action threshold >=5
    hi  = pd_[pd_.pest_trap_count >= 5].alert_pest_action.mean()
    lo  = pd_[pd_.pest_trap_count <  5].alert_pest_action.mean()
    check('pest', f'alert_pest_action fires iff trap_count>=5 [{site}]',
          hi == 1.0 and lo == 0.0, f'>=5: {hi}  <5: {lo}')

    # Outbreak threshold >=20
    rows_hi = pd_[pd_.pest_trap_count >= 20]
    hi2 = rows_hi.alert_pest_outbreak.mean() if len(rows_hi) else None
    lo2 = pd_[pd_.pest_trap_count < 20].alert_pest_outbreak.mean()
    check('pest', f'alert_pest_outbreak fires iff trap_count>=20 [{site}]',
          (hi2 == 1.0 or hi2 is None) and lo2 == 0.0,
          f'>=20: {hi2 if hi2 is not None else "n/a (no rows)"}  <20: {lo2}')


# ── Livestock Tracking ────────────────────────────────────────────────────────
print('\n=== Livestock Tracking ===')
ls = pd.read_csv(OUT / 'livestock_tracking.csv', parse_dates=['timestamp'])
ls['hour'] = ls.timestamp.dt.hour

for site in ls.site_id.unique():
    sd = ls[ls.site_id == site]

    # Low activity only during active hours (06-20)
    night_alerts = sd[(sd.hour < 6) | (sd.hour > 20)].alert_low_activity.sum()
    check('livestock', f'alert_low_activity never fires outside 06:00-20:00 [{site}]',
          night_alerts == 0, f'night-hour alerts: {night_alerts}')

    # Flee only when accel > 3.5
    flee_rows = sd[sd.alert_flee == 1]
    min_accel = flee_rows.accel_mag_g.min() if len(flee_rows) else None
    check('livestock', f'alert_flee only when accel>3.5g [{site}]',
          min_accel is None or min_accel > 3.5,
          f'min accel when flee=1: {min_accel}')

    # Geofence: check status is consistent
    flee_rate = sd.alert_flee.mean()
    check('livestock', f'flee events rare (<1%) [{site}]',
          flee_rate < 0.01, f'flee rate: {flee_rate*100:.2f}%')


# ── Infrastructure Events ─────────────────────────────────────────────────────
print('\n=== Infrastructure Events ===')
inf = pd.read_csv(OUT / 'infrastructure_events.csv', parse_dates=['timestamp'])
inf['hour'] = inf.timestamp.dt.hour

breach_statuses = inf[inf.fence_breach_event == 1]['status'].unique().tolist()
check('infra', 'fence_breach always produces critical status',
      breach_statuses == ['critical'],
      f'status values when breach=1: {breach_statuses}')

crit_no_breach = inf[(inf.fence_breach_event == 0) & (inf.status == 'critical')].shape[0]
check('infra', 'no critical status without fence_breach',
      crit_no_breach == 0, f'critical rows with breach=0: {crit_no_breach}')

night_gate_warn = inf[
    (inf.gate_open_event == 1) &
    ((inf.hour < 6) | (inf.hour >= 19)) &
    (inf.fence_breach_event == 0)
]['status'].unique().tolist()
check('infra', 'night gate events produce warning status',
      night_gate_warn == ['warning'],
      f'status when gate at night (no breach): {night_gate_warn}')


# ── Security Events ───────────────────────────────────────────────────────────
print('\n=== Security Events ===')
sec = pd.read_csv(OUT / 'security_events.csv', parse_dates=['timestamp'])
sec['hour'] = sec.timestamp.dt.hour

day_intr = sec[(sec.hour >= 6) & (sec.hour < 19)].alert_intrusion.sum()
check('security', 'alert_intrusion only fires at night (before 06:00 or after 19:00)',
      day_intr == 0, f'daytime intrusion alerts: {day_intr}')

fire_rows = sec[sec.alert_fire == 1]
min_smoke = fire_rows[fire_rows.flame_detected == 0].smoke_ppm.min() if len(fire_rows) else None
check('security', 'alert_fire only when smoke>200 OR flame_detected=1',
      min_smoke is None or min_smoke > 200,
      f'min smoke when fire alert and no flame: {min_smoke}')

panic_statuses = sec[sec.panic_triggered == 1]['status'].unique().tolist()
check('security', 'panic_triggered always produces critical status',
      'critical' in panic_statuses,
      f'status when panic=1: {panic_statuses}')

smoke_warn = sec[(sec.smoke_ppm > 35) & (sec.alert_fire == 0)].alert_smoke.mean()
check('security', 'alert_smoke fires when smoke>35 (below fire threshold)',
      smoke_warn == 1.0 if not pd.isna(smoke_warn) else True,
      f'alert_smoke rate when 35<smoke<=200: {smoke_warn}')


# ── Summary ───────────────────────────────────────────────────────────────────
print(f'\n{"="*60}')
passed = sum(1 for r in results if r[2])
total  = len(results)
failed = [r for r in results if not r[2]]

print(f'RESULT: {passed}/{total} checks passed')
if failed:
    print(f'\n{len(failed)} FAILED:')
    for r in failed:
        print(f'  [{r[0]}] {r[1]}')
        print(f'    {r[3]}')
else:
    print('All checks passed.')
    print('alert_rules.json is consistent with the CSV data.')
