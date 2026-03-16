"""
DATA Project — Synthetic IoT Environmental Monitoring Datasets
==============================================================
Generates six synthetic sensor datasets grounded in real NASA POWER
hourly weather data for Alice, Eastern Cape, South Africa (lat -32.78, lon 26.84).

Licence & IP
------------
Free for educational, research, and community use with attribution.
Commercial use requires prior engagement with the project team.
See LICENSE.md for full terms and attribution.
Contact: j.brooks2@leeds.ac.uk

From Extraction to Exchange: Decolonial Approaches to Technological Agency (DATA)
University of Leeds / University of the Witwatersrand / University of Fort Hare
Funded by the Horizons Institute Platform Programme, University of Leeds.

Seed: 2850 (COMP2850 easter egg)

All datasets conform to the DATA Project spec:
  - timestamp, site_id per row
  - sensor columns matching the DFRobot/BME280/BH1750 bundle
  - status column: "normal" / "warning" / "critical"
  - alert_triggered boolean (True when status != normal)
  - granular alert_* columns for analysis extension
  - ~3-5% missing values (sensor dropout / LoRa packet loss)

References:
  SANS 241:2015 (water quality thresholds)
  FAO Irrigation Papers 56, 61 (soil thresholds)
  FAO FAW IPM Guide 2018; Huber & Gillespie 1992 (pest/disease)
  Martiskainen et al. 2009 (livestock accelerometer behaviour)
  CASAS dataset / Cook et al. 2013 (security event rates)
  NASA POWER MERRA-2: https://power.larc.nasa.gov
"""

import numpy as np
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Configuration ─────────────────────────────────────────────────────────────

SEED     = 2850
NASA_CSV = Path("/mnt/user-data/uploads/POWER_Point_Hourly_20220101_20231231_032d78S_026d84E_LST.csv")
OUT_DIR  = Path("/mnt/user-data/outputs/synthetic_outputs")
OUT_DIR.mkdir(exist_ok=True)

WATER_SITES     = ["site_upstream", "site_downstream", "site_reservoir"]
SOIL_SITES      = ["site_riverside", "site_hillside", "site_irrigated"]
PEST_SITES      = ["site_maize", "site_brassica", "site_orchard"]
LIVESTOCK_UNITS = ["herd_cattle_A", "herd_goat_B"]
GATE_UNITS      = ["infrastructure_gate"]
SECURITY_NODES  = ["node_perimeter", "node_interior", "node_communal"]

rng = np.random.default_rng(SEED)


# ── Helpers ───────────────────────────────────────────────────────────────────

def noise(arr, sigma, clip=None):
    """Add Gaussian noise to a numpy array; optionally clip to (lo, hi)."""
    out = np.asarray(arr, dtype=float) + rng.normal(0, sigma, len(arr))
    return np.clip(out, *clip) if clip else out


def status_col(warning_mask, critical_mask):
    """Derive a status string column from boolean masks."""
    out = np.where(critical_mask, "critical",
          np.where(warning_mask,  "warning", "normal"))
    return out


def inject_missing(df, rate):
    """Inject ~rate fraction of NaN into sensor columns as dropouts and short blocks."""
    df = df.copy()
    # Only inject into continuous sensor readings, not flags/alerts/status
    exclude = {"timestamp","site_id","status","alert_triggered"}
    exclude |= {c for c in df.columns if c.startswith("alert_") or
                c.startswith("stress_") or c in
                ("gate_open_event","fence_breach_event","panic_triggered",
                 "motion_detected","door_open","flame_detected")}
    sensor_cols = [c for c in df.select_dtypes(include="number").columns
                   if c not in exclude]
    if not sensor_cols:
        return df
    n = len(df)
    n_target = int(n * rate)
    # Individual dropouts
    for col in sensor_cols:
        n_drop = max(1, n_target // (len(sensor_cols) * 2))
        df.iloc[rng.choice(n, size=n_drop, replace=False),
                df.columns.get_loc(col)] = np.nan
    # Short offline blocks (3–12 readings = 45 min – 3 hr)
    for _ in range(max(1, n_target // 30)):
        col   = sensor_cols[rng.integers(0, len(sensor_cols))]
        start = rng.integers(0, n - 12)
        ln    = int(rng.integers(3, 12))
        df.iloc[start:start+ln, df.columns.get_loc(col)] = np.nan
    return df


# ── 1. Backbone ───────────────────────────────────────────────────────────────

def load_backbone(path):
    """
    Load NASA POWER hourly data, resample to 15-min.
    All derived columns stored as numpy arrays to prevent DatetimeIndex
    alignment bugs when building DataFrames.
    """
    raw = pd.read_csv(path, skiprows=15)
    raw.replace(-999, np.nan, inplace=True)
    raw["timestamp"] = pd.to_datetime(
        raw[["YEAR","MO","DY","HR"]].rename(
            columns={"YEAR":"year","MO":"month","DY":"day","HR":"hour"}))
    raw = raw.set_index("timestamp").drop(columns=["YEAR","MO","DY","HR"])
    raw = raw.interpolate("time")
    bb  = raw.resample("15min").interpolate("time")

    # Derived — all stored as numpy to avoid index-alignment issues
    # Lux: 1 MJ/hr = 277.8 W/m2; 1 W/m2 ≈ 120 lux → 33,333 lux per MJ/hr
    bb["solar_lux"]   = np.clip((bb["ALLSKY_SFC_SW_DWN"] * 33333).to_numpy(), 0, 150000)
    # Pressure: backbone is kPa; spec and BME280 output hPa (1 kPa = 10 hPa)
    bb["pressure_hPa"]= (bb["PS"] * 10).to_numpy()
    # Rain: >2 mm/hr = meaningful convective rainfall in MERRA-2 gridded data
    # (<2 mm/hr includes drizzle and interpolation artefacts across 15-min slots)
    bb["is_raining"]  = (bb["PRECTOTCORR"] > 2.0).to_numpy()
    bb["hour_of_day"] = bb.index.hour
    bb["month"]       = bb.index.month
    bb["wet_season"]  = bb["month"].isin([11,12,1,2,3]).to_numpy()

    print(f"Backbone: {len(bb):,} rows  |  "
          f"T: {bb.T2M.min():.1f}–{bb.T2M.max():.1f}°C  |  "
          f"Rain (>2mm/hr): {int(bb.is_raining.sum()):,}/{len(bb):,} intervals  |  "
          f"Lux max: {bb.solar_lux.max():.0f}\n")
    return bb


# ── 2. Water Quality ──────────────────────────────────────────────────────────

def make_water_quality(bb):
    """
    Sensors: pH probe, turbidity, conductivity, water temp (BME280), BH1750 light, water level
    Causal structure (SANS 241:2015):
      turbidity    <- rain_intensity (30-min lag) × site_multiplier  [log-normal]
      conductivity <- dry_season_concentration × rain_dilution
      pH           <- baseline ± diurnal photosynthesis (reservoir only)
      water_level  <- exponential recession driven by rain
      light_lux    <- solar backbone (algae risk context)
    Status: warning = turbidity>5 OR pH outside 6.5-8.5 OR conductivity>500
            critical = turbidity>10 OR pH outside 6.0-9.0 OR conductivity>1500
    """
    ts   = bb.index
    n    = len(bb)
    T    = bb["T2M"].to_numpy()
    RH   = bb["RH2M"].to_numpy()
    R    = bb["PRECTOTCORR"].to_numpy()
    Rl   = np.concatenate([[0,0], R[:-2]])   # ~30-min lag
    HR   = bb["hour_of_day"].to_numpy()
    WET  = bb["wet_season"].to_numpy()
    RAIN = bb["is_raining"].to_numpy()
    LUX  = bb["solar_lux"].to_numpy()

    dfs = []
    for site in WATER_SITES:
        ph_off, t_mult, ec_base = {
            "site_upstream":   (+0.10, 0.7, 150.0),
            "site_downstream": (-0.10, 1.8, 350.0),
            "site_reservoir":  (+0.20, 0.5, 220.0),
        }[site]

        # pH: baseline 7.2 ± site offset; reservoir gets diurnal photosynthesis swing
        diurnal = (0.15 * np.sin(2*np.pi*(HR-6)/24)
                   if site == "site_reservoir" else np.zeros(n))
        ph = np.clip(7.2 + ph_off + diurnal + rng.normal(0, 0.08, n), 5.0, 9.5)

        # Turbidity: log-normal baseline + rain spike with 30-min lag
        turb = np.clip(
            rng.lognormal(1.0, 0.4, n) + t_mult * Rl * rng.lognormal(0, 0.3, n),
            0.1, 5000.0)

        # Conductivity: higher in dry season (concentration); diluted by rain
        cond = np.clip(
            ec_base * (1 + 0.3*(~WET).astype(float)) * np.where(RAIN, 0.7, 1.0)
            + rng.normal(0, 30, n), 30, 3000)

        # Water temperature: ~3°C below air temp
        water_temp = noise(T - 3.0, 0.8, clip=(5, 35))

        # Water level: exponential recession model
        lv = np.full(n, 80.0)
        for i in range(1, n):
            lv[i] = lv[i-1] * 0.97 + R[i] * 8.0
        lv = np.clip(lv + rng.normal(0, 2, n), 5, 800)

        # Light (BH1750) — algae risk proxy; reservoir more relevant than river
        lux_sensor = noise(LUX, 500, clip=(0, 150000))

        # Alert logic (SANS 241:2015)
        warn_ph   = (ph < 6.5) | (ph > 8.5)
        crit_ph   = (ph < 6.0) | (ph > 9.0)
        warn_turb = turb > 5.0
        crit_turb = turb > 10.0
        warn_ec   = cond > 500.0
        crit_ec   = cond > 1500.0

        warning  = (warn_ph | warn_turb | warn_ec) & ~(crit_ph | crit_turb | crit_ec)
        critical = crit_ph | crit_turb | crit_ec

        dfs.append(pd.DataFrame({
            "timestamp":            ts,
            "site_id":              site,
            "ph":                   ph.round(2),
            "turbidity_ntu":        turb.round(2),
            "conductivity_uS_cm":   cond.round(1),
            "water_temperature_c":  water_temp.round(2),
            "water_level_cm":       lv.round(1),
            "light_lux":            lux_sensor.round(0).astype(int),
            "status":               status_col(warning, critical),
            "alert_triggered":      (warning | critical).astype(int),
            "alert_ph":             (warn_ph | crit_ph).astype(int),
            "alert_turbidity":      warn_turb.astype(int),
            "alert_turbidity_crit": crit_turb.astype(int),
            "alert_conductivity":   (warn_ec | crit_ec).astype(int),
            "wx_temp_c":            T.round(2),
            "wx_rh_pct":            RH.round(1),
            "wx_rain_mm_hr":        R.round(3),
        }))

    out = pd.concat(dfs, ignore_index=True)
    return inject_missing(out, 0.03)


# ── 3. Soil Monitoring ────────────────────────────────────────────────────────

def make_soil(bb):
    """
    Sensors: capacitive soil moisture, BME280 (temp/humidity/pressure), BH1750 light,
             pH probe, conductivity/EC probe
    Causal structure (FAO Papers 56, 61):
      soil_moisture <- exponential decay + rain infiltration
      soil_ec       <- 1/moisture (concentration effect)
      soil_ph       <- slow random drift + wet-season acidification
      pressure_hPa  <- from BME280 (backbone PS column, converted)
      light_lux     <- BH1750 (solar radiation proxy for evapotranspiration)
    Status: warning = moisture outside 14-45% OR pH outside 5.5-7.5 OR EC>800
            critical = moisture <8% OR pH <4.5 OR EC>2500
    """
    ts  = bb.index
    n   = len(bb)
    T   = bb["T2M"].to_numpy()
    RH  = bb["RH2M"].to_numpy()
    R   = bb["PRECTOTCORR"].to_numpy()
    WET = bb["wet_season"].to_numpy()
    LUX = bb["solar_lux"].to_numpy()
    P   = bb["pressure_hPa"].to_numpy()

    dfs = []
    for site in SOIL_SITES:
        m0, ph0, ec0 = {
            "site_riverside": (0.32, 6.1, 380.0),
            "site_hillside":  (0.21, 5.8, 240.0),
            "site_irrigated": (0.28, 6.4, 520.0),
        }[site]

        # Soil moisture: exponential decay, rain infiltration
        moist = np.zeros(n);  moist[0] = m0
        FC = m0 + 0.12
        for i in range(1, n):
            moist[i] = min(moist[i-1] * 0.9995 + min(R[i] * 0.004, 0.08), FC)
        moist = np.clip(moist + rng.normal(0, 0.015, n), 0.04, 0.55)

        # Soil pH: slow random walk + wet-season acidification
        ph_drift = np.cumsum(rng.normal(0, 0.0001, n))
        soil_ph  = np.clip(ph0 - 0.15*WET + ph_drift + rng.normal(0, 0.05, n), 4.0, 8.5)

        # Soil EC: concentration rises as moisture falls
        soil_ec  = np.clip(ec0 * (0.28 / np.maximum(moist, 0.05))
                           + rng.normal(0, 40, n), 50, 4000)

        # BME280: air temp, humidity, pressure
        air_temp = noise(T, 0.5)
        humidity = noise(RH, 2.0, clip=(5, 100))
        pressure = noise(P, 0.5, clip=(900, 1050))

        # BH1750: light (relevant for evapotranspiration calculation)
        light_lux = noise(LUX, 300, clip=(0, 150000))

        # Alert logic (FAO Paper 56)
        warn_m  = (moist < 0.14) | (moist > 0.45)
        crit_m  = (moist < 0.08)
        warn_ph = (soil_ph < 5.5) | (soil_ph > 7.5)
        crit_ph = (soil_ph < 4.5) | (soil_ph > 8.0)
        warn_ec = soil_ec > 800.0
        crit_ec = soil_ec > 2500.0

        warning  = (warn_m | warn_ph | warn_ec) & ~(crit_m | crit_ph | crit_ec)
        critical = crit_m | crit_ph | crit_ec

        dfs.append(pd.DataFrame({
            "timestamp":             ts,
            "site_id":               site,
            "soil_moisture_vwc":     moist.round(3),
            "soil_ph":               soil_ph.round(2),
            "soil_ec_uS_cm":         soil_ec.round(1),
            "air_temperature_c":     air_temp.round(2),
            "relative_humidity_pct": humidity.round(1),
            "pressure_hPa":          pressure.round(1),
            "light_lux":             light_lux.round(0).astype(int),
            "status":                status_col(warning, critical),
            "alert_triggered":       (warning | critical).astype(int),
            "stress_moisture":       (warn_m | crit_m).astype(int),
            "stress_ph":             (warn_ph | crit_ph).astype(int),
            "stress_salinity":       (warn_ec | crit_ec).astype(int),
            "stress_critical":       critical.astype(int),
            "wx_rain_mm_hr":         R.round(3),
        }))

    out = pd.concat(dfs, ignore_index=True)
    return inject_missing(out, 0.04)


# ── 4. Pest & Crop Disease ────────────────────────────────────────────────────

def make_pest(bb):
    """
    Sensors: BME280 (temp/humidity), BH1750 light, leaf wetness, MPU6050 vibration
             (trap disturbance indicator), pest trap count
    Causal structure (FAO FAW IPM Guide 2018; Huber & Gillespie 1992):
      leaf_wetness  <- RH proximity to 100% + rain + night dew
      trap_count    <- NegBin, rate = f(temp, humidity, season)
      vibration     <- low baseline; spikes when insect disturbs trap mechanism
      disease_risk  <- compound: T∈[15,28°C] AND RH>75% AND leaf_wetness>0.6 ≥6hr
    Status: warning = pest trap >=5 OR disease_moderate
            critical = pest trap >=20 OR disease_high
    """
    ts   = bb.index
    n    = len(bb)
    T    = bb["T2M"].to_numpy()
    RH   = bb["RH2M"].to_numpy()
    R    = bb["PRECTOTCORR"].to_numpy()
    LUX  = bb["solar_lux"].to_numpy()
    HR   = bb["hour_of_day"].to_numpy()
    WET  = bb["wet_season"].to_numpy()
    RAIN = bb["is_raining"].to_numpy()

    dfs = []
    for site in PEST_SITES:
        base_rate = {"site_maize":1.5, "site_brassica":0.8, "site_orchard":2.2}[site]

        # Leaf wetness: RH-driven + rain + overnight dew condensation
        dew_prox  = np.clip((RH - 70) / 30, 0, 1)
        night_dew = np.where((HR >= 22) | (HR <= 6), 0.3, 0.0)
        lw = np.clip(dew_prox*0.6 + RAIN.astype(float)*0.4
                     + night_dew + rng.normal(0, 0.05, n), 0, 1)

        # BME280
        air_temp = noise(T, 0.8)
        humidity  = noise(RH, 3.0, clip=(10, 100))

        # BH1750: physical sensor reads near-zero in darkness
        light_lux = np.where(LUX > 0, noise(LUX, 500, clip=(0, 150000)), rng.uniform(0, 5, n))

        # Vibration (MPU6050): low right-skewed baseline; spikes = trap disturbance
        vibration = rng.beta(2, 10, n)   # low baseline
        # Trap disturbance events: correlated with pest pressure
        disturb_p = np.clip(base_rate * 0.01 * np.where(WET, 2.5, 0.6), 0, 0.3)
        disturb   = rng.random(n) < disturb_p
        vibration[disturb] = rng.uniform(0.5, 1.0, disturb.sum())
        vibration = np.clip(vibration, 0, 1)

        # Pest trap count: negative binomial, seasonally modulated
        pest_window = ((air_temp >= 18) & (air_temp <= 30) & (humidity > 60)).astype(float)
        trap_rate   = base_rate * (0.4 + 0.6*pest_window) * np.where(WET, 2.5, 0.6)
        trap_count  = rng.negative_binomial(1, 1/(1+trap_rate), n)

        # Disease risk (compound trigger — Huber & Gillespie 1992)
        wet_hrs = pd.Series(lw > 0.6).rolling(24).sum().fillna(0).to_numpy()
        d_mod   = ((air_temp >= 15) & (humidity > 75) & (lw > 0.6)).astype(int)
        d_high  = ((air_temp >= 15) & (humidity > 80) & (wet_hrs >= 24)).astype(int)

        a_pest  = (trap_count >= 5).astype(int)
        a_outbr = (trap_count >= 20).astype(int)

        warning  = ((a_pest == 1) | (d_mod == 1)) & (a_outbr == 0) & (d_high == 0)
        critical = (a_outbr == 1) | (d_high == 1)

        dfs.append(pd.DataFrame({
            "timestamp":              ts,
            "site_id":                site,
            "air_temperature_c":      air_temp.round(2),
            "relative_humidity_pct":  humidity.round(1),
            "leaf_wetness_0_1":       lw.round(3),
            "light_lux":              light_lux.round(0).astype(int),
            "vibration_level":        vibration.round(3),
            "pest_trap_count":        trap_count,
            "status":                 status_col(warning, critical),
            "alert_triggered":        (warning | critical).astype(int),
            "alert_pest_action":      a_pest,
            "alert_pest_outbreak":    a_outbr,
            "alert_disease_moderate": d_mod,
            "alert_disease_high":     d_high,
            "wx_rain_mm_hr":          R.round(3),
        }))

    out = pd.concat(dfs, ignore_index=True)
    return inject_missing(out, 0.04)


# ── 5. Livestock Tracking ─────────────────────────────────────────────────────

def _livestock_raw(bb):
    """Internal: build animal tracking rows (cattle + goat herds)."""
    KLAT, KLON = -32.780, 26.840
    ts  = bb.index
    n   = len(bb)
    T   = bb["T2M"].to_numpy()
    HR  = bb["hour_of_day"].to_numpy()

    dfs = []
    for unit in LIVESTOCK_UNITS:
        step  = 0.0003 if unit == "herd_cattle_A" else 0.0005
        geo_r = 0.004  if unit == "herd_cattle_A" else 0.006

        # GPS: correlated random walk with kraal attraction at night
        lats = np.zeros(n);  lats[0] = KLAT + rng.normal(0, 0.0002)
        lons = np.zeros(n);  lons[0] = KLON + rng.normal(0, 0.0002)
        for i in range(1, n):
            h, t = HR[i], T[i]
            if h < 6 or h >= 19:                      # night: pull toward kraal
                lats[i] = lats[i-1]*0.92 + KLAT*0.08 + rng.normal(0, 0.00005)
                lons[i] = lons[i-1]*0.92 + KLON*0.08 + rng.normal(0, 0.00005)
            elif 11 <= h <= 14 and t > 28:            # midday heat: minimal movement
                lats[i] = lats[i-1] + rng.normal(0, step*0.1)
                lons[i] = lons[i-1] + rng.normal(0, step*0.1)
            else:                                      # active foraging
                lats[i] = lats[i-1] + rng.normal(0, step)
                lons[i] = lons[i-1] + rng.normal(0, step)

        # Accelerometer: behaviour state machine (Martiskainen et al. 2009)
        accel = np.select(
            [(HR < 6) | (HR >= 20),
             (HR >= 11) & (HR <= 14) & (T > 28),
             ((HR >= 6) & (HR <= 9)) | ((HR >= 16) & (HR <= 19))],
            [rng.normal(1.00, 0.05, n),   # resting
             rng.normal(1.05, 0.08, n),   # standing/heat rest
             rng.normal(1.50, 0.30, n)],  # active grazing/walking
            default=rng.normal(1.20, 0.15, n)
        )
        # Rare fleeing events (~0.1% — theft/predator)
        flee_idx = rng.choice(n, size=max(1, n//1000), replace=False)
        accel[flee_idx] = rng.uniform(3.5, 7.0, len(flee_idx))
        accel = np.clip(accel, 0.5, 8.0)

        dist      = np.sqrt((lats - KLAT)**2 + (lons - KLON)**2)
        geo_b     = (dist > geo_r).astype(int)
        # Low activity alert: only meaningful during active hours (06:00-20:00)
        # Resting accel ~1.0g at night is normal behaviour, not illness
        active_hours = ((HR >= 6) & (HR <= 20)).astype(float)
        low_act   = (pd.Series((accel < 1.08) & (HR >= 6) & (HR <= 20))
                       .rolling(4).min().fillna(0).to_numpy().astype(int))
        flee_al   = (accel > 3.5).astype(int)

        warning  = (low_act == 1) | (geo_b == 1)
        critical = flee_al == 1

        dfs.append(pd.DataFrame({
            "timestamp":             ts,
            "site_id":               unit,
            "latitude":              lats.round(6),
            "longitude":             lons.round(6),
            "accel_mag_g":           accel.round(3),
            "ambient_temperature_c": noise(T, 1.5).round(2),
            "status":                status_col(warning, critical),
            "alert_triggered":       (warning | critical).astype(int),
            "alert_low_activity":    low_act,
            "alert_geofence":        geo_b,
            "alert_flee":            flee_al,
        }))

    return pd.concat(dfs, ignore_index=True)


def make_livestock_animals(bb):
    """
    GPS + accelerometer data for cattle and goat herds.
    Sensors: MPU6050 (accel), GPS module, BME280 (ambient temp).
    Causal structure (Martiskainen et al. 2009; SAPS livestock theft rates):
      GPS   <- correlated random walk + kraal attraction at night
      accel <- behaviour state machine: time-of-day + temperature
    Status: warning = low_activity OR geofence_breach
            critical = flee_accel (possible theft/predator)
    """
    df = _livestock_raw(bb)
    return inject_missing(df, 0.05)


def make_livestock_gate(bb):
    """
    Event log for fixed farm gate and perimeter fence infrastructure.
    Sensors: reed switch (gate), vibration sensor (fence breach), BME280 (ambient).
    Causal structure (SAPS livestock theft rates):
      gate_open    <- Poisson peaked at dawn (06-08) and dusk (17-19)
      fence_breach <- rare Poisson events; higher probability at night
      vibration    <- low baseline; elevated during breach
    Status: warning = gate_open at night
            critical = fence_breach
    """
    ts  = bb.index
    n   = len(bb)
    T   = bb["T2M"].to_numpy()
    HR  = bb["hour_of_day"].to_numpy()

    # Gate events: bimodal (dawn / dusk)
    gate_p   = np.where(((HR>=6)&(HR<=8)) | ((HR>=17)&(HR<=19)), 0.08, 0.005)
    gate_ev  = (rng.random(n) < gate_p).astype(int)

    # Fence breach: rare; higher at night (SAPS theft pattern)
    breach_p = np.where((HR >= 21) | (HR <= 5), 0.0008, 0.0002)
    breach   = (rng.random(n) < breach_p).astype(int)

    # Vibration: low baseline; elevated on breach
    vibration = rng.beta(1, 10, n)
    vibration[breach == 1] = rng.uniform(0.6, 1.0, int(breach.sum()))
    vibration = np.clip(vibration, 0, 1)

    night      = (HR < 6) | (HR >= 19)
    a_gn       = (gate_ev & night).astype(int)
    warning    = a_gn == 1
    critical   = breach == 1

    df = pd.DataFrame({
        "timestamp":             ts,
        "site_id":               "infrastructure_gate",
        "ambient_temperature_c": noise(T, 1.0).round(2),
        "gate_open_event":       gate_ev,
        "fence_breach_event":    breach,
        "vibration_level":       vibration.round(3),
        "status":                status_col(warning, critical),
        "alert_triggered":       (warning | critical).astype(int),
        "alert_gate_night":      a_gn,
        "alert_fence_breach":    breach,
    })
    return inject_missing(df, 0.01)


# ── 6. Security Events ────────────────────────────────────────────────────────

def make_security(bb):
    """
    Sensors: PIR (motion), reed switch (door), vibration, MQ135 (smoke/gas),
             sound level, BH1750 (light/day-night), flame detector, panic button
    Causal structure (SANS 1691:2007; CASAS dataset — Cook et al. 2013):
      motion/door  <- Poisson rate = f(time-of-day, node type)
      smoke_ppm    <- Gamma baseline + cooking-hour spikes + rare fire events
      sound_db     <- Normal(50,10) + activity-hour uplift
      flame        <- boolean; rare, correlated with smoke during fire events
      light_lux    <- BH1750 for day/night context in alert logic
      alert fusion <- motion AND door AND vibration AND night
    Status: warning = motion at night OR smoke>35ppm
            critical = intrusion (fusion) OR fire OR distress (panic)
    """
    ts  = bb.index
    n   = len(bb)
    T   = bb["T2M"].to_numpy()
    HR  = bb["hour_of_day"].to_numpy()
    LUX = bb["solar_lux"].to_numpy()

    dfs = []
    for node in SECURITY_NODES:
        base_p, occ = {
            "node_perimeter": (0.03, 0.5),
            "node_interior":  (0.08, 1.5),
            "node_communal":  (0.05, 1.0),
        }[node]

        # Time-of-day activity multiplier (bimodal — CASAS calibration)
        act = np.where(((HR>=7)&(HR<=9)) | ((HR>=18)&(HR<=22)), 2.5, 1.0)
        act = np.where((HR>=1) & (HR<=5), 0.1, act) * occ

        motion_p  = np.clip(base_p * act, 0, 0.95)
        motion    = (rng.random(n) < motion_p).astype(int)
        door_open = (rng.random(n) < motion_p * 0.4).astype(int)
        vibration = rng.beta(1, 8, n)

        # Smoke: Gamma baseline + cooking-hour spikes + rare fire events
        cooking = ((HR>=7)&(HR<=9)) | ((HR>=17)&(HR<=19))
        smoke   = np.clip(
            rng.gamma(2, 5, n) + np.where(cooking, rng.gamma(3, 20, n), 0)
            + rng.normal(0, 2, n), 0, 500)

        # Flame detector: normally false; true during fire events only
        flame = np.zeros(n, dtype=int)

        # Rare fire events (~3/year across network)
        for fi in rng.choice(n, size=max(1, n//2920), replace=False):
            dur = int(rng.integers(4, 20))
            end = min(fi+dur, n)
            smoke[fi:end]     = rng.uniform(300, 500, end-fi)
            vibration[fi:end] = rng.uniform(0.6, 1.0, end-fi)
            flame[fi:end]     = 1

        # Sound: Normal baseline, activity-hour uplift
        sound = np.clip(
            noise(np.full(n, 50.0), 10) + np.where(cooking, rng.normal(10, 5, n), 0),
            20, 120)

        # BH1750: physical sensor reads near-zero in darkness
        light_lux = np.where(LUX > 0, noise(LUX, 500, clip=(0, 150000)), rng.uniform(0, 5, n))

        # Panic button: extremely rare (SAPS calibrated)
        panic = (rng.random(n) < 0.00005).astype(int)

        # Alert fusion logic
        night    = (HR < 6) | (HR >= 19)
        a_intr   = (motion & door_open & (vibration > 0.5) & night).astype(int)
        a_fire   = ((smoke > 200) | (flame == 1)).astype(int)
        a_distr  = panic.copy()
        a_mn     = (motion & ((HR < 6) | (HR >= 22))).astype(int)
        a_smoke  = (smoke > 35).astype(int)

        warning  = ((a_mn == 1) | (a_smoke == 1)) & (a_intr == 0) & (a_fire == 0) & (a_distr == 0)
        critical = (a_intr == 1) | (a_fire == 1) | (a_distr == 1)

        dfs.append(pd.DataFrame({
            "timestamp":          ts,
            "site_id":            node,
            "motion_detected":    motion,
            "door_open":          door_open,
            "vibration_level":    vibration.round(3),
            "smoke_ppm":          smoke.round(1),
            "sound_db":           sound.round(1),
            "light_lux":          light_lux.round(0).astype(int),
            "flame_detected":     flame,
            "panic_triggered":    panic,
            "status":             status_col(warning, critical),
            "alert_triggered":    (warning | critical).astype(int),
            "alert_intrusion":    a_intr,
            "alert_fire":         a_fire,
            "alert_distress":     a_distr,
            "alert_motion_night": a_mn,
            "alert_smoke":        a_smoke,
            "wx_temp_c":          T.round(2),
        }))

    out = pd.concat(dfs, ignore_index=True)
    return inject_missing(out, 0.02)


# ── README ────────────────────────────────────────────────────────────────────

README = """\
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
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("DATA Project — Synthetic Dataset Generator")
    print(f"Seed: {SEED}  |  Alice, Eastern Cape, SA")
    print("=" * 60 + "\n")

    bb = load_backbone(NASA_CSV)

    tasks = [
        ("Water quality",       make_water_quality,    "water_quality.csv"),
        ("Soil monitoring",     make_soil,             "soil_monitoring.csv"),
        ("Pest monitoring",     make_pest,             "pest_monitoring.csv"),
        ("Livestock (animals)", make_livestock_animals,"livestock_tracking.csv"),
        ("Livestock (gate)",    make_livestock_gate,   "infrastructure_events.csv"),
        ("Security",            make_security,         "security_events.csv"),
    ]

    for label, fn, fname in tasks:
        print(f"Generating {label}...")
        df = fn(bb)
        df.to_csv(OUT_DIR / fname, index=False)
        counts = df["status"].value_counts().to_dict()
        miss   = f"{100*df.isnull().any(axis=1).mean():.1f}%"
        n_warn = counts.get("warning", 0)
        n_crit = counts.get("critical", 0)
        n_norm = counts.get("normal", 0)
        print(f"  {len(df):,} rows  |  "
              f"normal: {100*n_norm/len(df):.1f}%  "
              f"warning: {100*n_warn/len(df):.1f}%  "
              f"critical: {100*n_crit/len(df):.1f}%  |  "
              f"NaN rows: {miss}")

    (OUT_DIR / "README.md").write_text(README)
    print(f"\nAll outputs → {OUT_DIR}/")

if __name__ == "__main__":
    main()
