# How to Run the Dataset Generator Locally

This package contains six synthetic IoT sensor datasets for the DATA Project /
COMP2850 Environmental Monitoring Dashboard, plus the Python script that
generated them so you can reproduce, inspect, or modify the data.

---

## What's in the zip

```
data-project-datasets/
├── README_run_locally.md          ← this file
├── generate_datasets.py           ← the generator script
│
├── synthetic_outputs/
│   ├── README.md                  ← overview of all datasets
│   ├── alert_rules.md             ← threshold rules (human-readable)
│   ├── alert_rules.json           ← threshold rules (machine-readable)
│   │
│   ├── water_quality.csv
│   ├── README_water_quality.md
│   ├── soil_monitoring.csv
│   ├── README_soil_monitoring.md
│   ├── pest_monitoring.csv
│   ├── README_pest_monitoring.md
│   ├── livestock_tracking.csv
│   ├── README_livestock_tracking.md
│   ├── infrastructure_events.csv
│   ├── README_infrastructure_events.md
│   ├── security_events.csv
│   └── README_security_events.md
```

---

## Just using the CSVs?

You don't need to run anything. Load the CSV files directly into your
dashboard project with pandas:

```python
import pandas as pd

df = pd.read_csv('synthetic_outputs/water_quality.csv', parse_dates=['timestamp'])
print(df.head())
```

Read the per-dataset READMEs and `alert_rules.md` for column definitions
and threshold logic.

---

## Re-running the generator

You only need to do this if you want to:
- Reproduce the datasets from scratch
- Modify the generator (e.g. change a distribution or threshold)
- Understand how the data was created

### Requirements

Python 3.9 or later. The following packages:

```
numpy
pandas
scipy
```

Install with:

```bash
pip install numpy pandas scipy
```

### NASA POWER weather file

The generator requires the real hourly weather data file for Alice,
Eastern Cape. This file is **not** included in the zip (it is ~2 MB and
freely available). Download it as follows:

1. Go to https://power.larc.nasa.gov/data-access-viewer/
2. Set parameters:
   - Temporal resolution: **Hourly**
   - Date range: **2022-01-01 to 2023-12-31**
   - Latitude: **-32.78** / Longitude: **26.84**
   - Parameters: T2M, RH2M, PRECTOTCORR, WS2M, ALLSKY_SFC_SW_DWN, T2MDEW, PS
3. Download as CSV
4. Place the downloaded file in the same directory as `generate_datasets.py`
5. Update the `NASA_CSV` path at the top of `generate_datasets.py` to match
   your filename

### Run

```bash
python generate_datasets.py
```

Output CSVs are written to `synthetic_outputs/`. The generator is
deterministic — running it twice produces identical files (seed = 2850).

Expected runtime: approximately 2–4 minutes on a typical laptop.

---

## Modifying the generator

The generator is structured as one function per dataset. Each function:

1. Takes the shared weather backbone (`bb`) as input
2. Computes sensor readings using the causal relationships described in
   the relevant README
3. Derives alert columns from those readings
4. Calls `inject_missing()` to add realistic NaN values
5. Returns a DataFrame

To change a threshold, find the relevant `make_*` function and edit the
alert logic. If you change a threshold, update `alert_rules.json` and
`alert_rules.md` to match, and document your reason in your project report.

---

## Reproducibility

All datasets use `numpy.random.default_rng(seed=2850)`. The seed is set
once at the top of the script and used throughout. Re-running the script
with the same NASA POWER CSV will always produce identical output.

Seed 2850 = COMP2850.

---

## Questions?

Refer to the per-dataset READMEs and the alert_rules files first.
The generator source code is thoroughly commented and reflects the
causal structure described in each README.
