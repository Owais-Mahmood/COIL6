# From Sensor to CSV — Hardware Reference for Fort Hare / DATA ISL Students

## Who this is for

This document is for students building physical sensor prototypes in the DATA ISL
programme at the Wits Innovation Centre. It maps every column in the synthetic
CSV datasets back to the physical sensor that would produce it in a real
deployment — what the sensor is, what it outputs, and what processing happens
before a value reaches the CSV.

Leeds COMP2850 students (building the dashboard) may also find this useful
for understanding what the data represents physically.

---

## The journey from sensor to CSV column

Every CSV value has gone through this chain:

```
Physical world
    ↓
Sensor (converts physical quantity to electrical signal)
    ↓
Microcontroller (reads ADC/I²C/UART; applies calibration formula)
    ↓
Edge processing (unit conversion, validation, local alert logic)
    ↓
LoRa packet (timestamped payload transmitted wirelessly)
    ↓
Gateway / receiver
    ↓
CSV row (one row = one 15-minute reading per site)
```

In the synthetic datasets, the middle steps are simulated. In your prototype,
you implement them. The columns in the CSV are what your system should
eventually produce.

---

## Shared infrastructure — all challenge areas

### Microcontroller: ESP32

The ESP32 is the brain of each sensor node. It:
- Reads sensor values via I²C, UART, or ADC pins
- Applies calibration formulas
- Adds a timestamp
- Packages and transmits a LoRa data packet
- Handles sleep/wake cycles for battery efficiency

All five challenge areas use ESP32 + LoRa as the core platform.

### Communication: LoRa module (SX1276 or similar)

LoRa (Long Range) transmits small data packets over distances of
1–10 km using sub-GHz radio (868 MHz in Europe; 915 MHz in South Africa).
Low power, low data rate — suitable for sending a few sensor readings
every 15 minutes. Not suitable for streaming or large payloads.

### Power: LiPo battery + solar panel

Nodes run from battery, charged by a small solar panel. Battery capacity
and solar sizing determine how long the node operates unattended.
Field deployment planning (Module 5.3 in the ISL programme) covers this.

---

## Challenge 1 — Soil Monitoring (`soil_monitoring.csv`)

### Sensors

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `soil_moisture_vwc` | Capacitive soil moisture sensor (e.g., STEMMA, DFRobot SEN0114) | Analogue (ADC) | 0–3.3V analogue voltage | Map ADC reading to VWC fraction via calibration in air (dry) and submerged (wet). VWC = (ADC − dry) / (wet − dry) |
| `soil_ph` | DFRobot pH probe + BNC connector module (SEN0161) | Analogue (ADC) | Millivolts (Nernst equation: ~59 mV per pH unit at 25°C) | pH = 7 − (Vread − Vmid) / slope; requires two-point calibration with pH 4.0 and pH 7.0 buffer solutions |
| `soil_ec_uS_cm` | DFRobot EC/conductivity probe (DFR0300) | Analogue (ADC) | Voltage proportional to conductivity | EC (µS/cm) = (voltage × factor) / temperature_compensation; temperature correction required |
| `air_temperature_c` | BME280 (onboard) | I²C | Compensated digital reading | Direct from BME280 library — no additional conversion |
| `relative_humidity_pct` | BME280 (onboard) | I²C | Compensated digital reading | Direct from BME280 library |
| `pressure_hPa` | BME280 (onboard) | I²C | Compensated digital reading in Pa | Divide by 100 for hPa |
| `light_lux` | BH1750 light sensor | I²C | 16-bit digital lux value | Direct from BH1750 library — returns lux |

### Key calibration notes

**pH probe:** the Nernst equation assumes 25°C. Outdoor temperature varies.
Apply temperature compensation using the concurrent temperature reading.
pH error without compensation can be ±0.5 units or more.

**Capacitive soil moisture:** capacitive sensors (unlike resistive ones)
do not corrode. Calibration drift is low but not zero — re-calibrate
if sensor is moved to a different soil type.

**EC probe:** conductivity is highly temperature-dependent (~2% per °C).
The DFRobot library includes a temperature compensation function — use it.

---

## Challenge 2 — Pest & Crop Disease Monitoring (`pest_monitoring.csv`)

### Sensors

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `air_temperature_c` | BME280 | I²C | Compensated digital | Direct from library |
| `relative_humidity_pct` | BME280 | I²C | Compensated digital | Direct from library |
| `leaf_wetness_0_1` | DFRobot leaf wetness sensor (SEN0198) | Analogue (ADC) | 0–3.3V proportional to surface resistance | Normalise: (ADC − dry_min) / (wet_max − dry_min); clamp to 0.0–1.0 |
| `light_lux` | BH1750 | I²C | 16-bit lux | Direct from library |
| `vibration_level` | MPU6050 accelerometer/gyro | I²C | 16-bit signed integers, 3 axes (x,y,z) in raw ADC units | Convert axes to g: accel_g = raw / 16384.0 (at ±2g range); compute magnitude = √(x²+y²+z²); normalise to 0–1 for the vibration proxy |
| `pest_trap_count` | Derived / infrared break-beam or acoustic trap | Varies | Pulse count or acoustic detection | Count of trigger events in the 15-minute window. In the dataset this is modelled statistically — your hardware implementation will depend on trap design |

### Key notes

**Leaf wetness sensor:** performance degrades with dust and biological fouling
in outdoor conditions. Clean sensor face regularly. In the synthetic data,
leaf wetness is modelled from humidity and rain — your sensor will read
actual surface moisture, which may differ.

**MPU6050 for vibration:** the MPU6050 is primarily an accelerometer/gyro
for motion tracking. Used here as a vibration proxy — it measures physical
disturbance of the trap structure. Place it on or adjacent to the trap frame.
At rest it reads ~1.0g (gravity). Insect disturbance adds to this.

**Trap count:** the synthetic dataset models this statistically (negative
binomial). In a real deployment you would need a physical counting mechanism:
a break-beam IR sensor, a piezoelectric element on the trap floor, or
optical detection. Design is open — document your approach.

---

## Challenge 3 — Livestock Tracking (`livestock_tracking.csv`, `infrastructure_events.csv`)

### Sensors — animal collar unit

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `latitude` / `longitude` | GPS module (e.g., u-blox NEO-6M, NEO-M8N) | UART (NMEA sentences) | NMEA `$GPRMC` or `$GPGGA` strings | Parse NMEA: latitude in DDMM.MMMM format → decimal degrees = DD + MM.MMMM/60; negative for South |
| `accel_mag_g` | MPU6050 | I²C | 16-bit signed integers per axis | Convert to g (÷16384 at ±2g range); magnitude = √(x²+y²+z²) |
| `ambient_temperature_c` | BME280 | I²C | Compensated digital | Direct from library |

### Sensors — infrastructure gate unit

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `gate_open_event` | Reed switch (magnetic contact sensor) | Digital GPIO | HIGH when magnet present, LOW when absent | Read GPIO pin; 1 = open (magnet absent), 0 = closed |
| `fence_breach_event` | Vibration sensor (DFRobot piezo vibration, or SW-420) | Digital GPIO | HIGH on vibration above threshold | Debounce in firmware (≥3 triggers in 500ms = breach event) |
| `vibration_level` | MPU6050 or SW-420 | I²C or Digital | See above | Magnitude (MPU6050) or pulse count (SW-420) normalised to 0–1 |
| `ambient_temperature_c` | BME280 | I²C | Compensated digital | Direct from library |

### Key notes

**GPS cold start:** GPS modules can take 30–90 seconds to acquire a fix
after power-on (cold start). Subsequent fixes (warm/hot start) are much
faster. Design your firmware to wait for a valid fix flag before logging.
NMEA `$GPRMC` includes a validity flag — check it.

**GPS power:** GPS is power-hungry (~25 mA continuous). For battery-powered
collars, use a GPS with a sleep/periodic fix mode — acquire a fix every
15 minutes and sleep between readings. This is how the 15-minute intervals
in the dataset map to real hardware.

**Reed switch wiring:** wire with a pull-up resistor (internal or external).
The GPIO pin reads HIGH (1) when the magnet is near the switch (closed gate)
and LOW (0) when the magnet is removed (open gate) — or vice versa depending
on the switch type. Confirm with a multimeter before writing your firmware.

**Geofence calculation on device:** the alert_geofence column in the CSV
is computed from GPS coordinates. On a microcontroller you can compute
approximate distance using the equirectangular approximation (fast, no trig):

```cpp
// Approximate distance in degrees (good enough for <10km)
float dlat = lat - KRAAL_LAT;
float dlon = (lon - KRAAL_LON) * cos(KRAAL_LAT * PI / 180.0);
float dist_deg = sqrt(dlat*dlat + dlon*dlon);
bool geofence_breach = (dist_deg > FENCE_RADIUS_DEG);
// FENCE_RADIUS_DEG: 0.004 for cattle, 0.006 for goats
```

---

## Challenge 4 — Water Quality (`water_quality.csv`)

### Sensors

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `ph` | DFRobot pH probe + SEN0161-V2 module | Analogue (ADC) | mV (Nernst equation) | pH = 7 − (Vread − Vmid) / 59.16; two-point calibration with pH 4.0 and 7.0 buffers; temperature-compensate |
| `turbidity_ntu` | DFRobot turbidity sensor (SEN0189) | Analogue (ADC) | 0–4.5V inversely proportional to turbidity | NTU = −1120.4 × V² + 5742.3 × V − 4353.8 (DFRobot datasheet formula); valid range 0–3000 NTU |
| `conductivity_uS_cm` | DFRobot EC probe (DFR0300) | Analogue (ADC) | Voltage proportional to conductivity | EC (µS/cm) = voltage × K / temperature_compensation; K is cell constant (calibrate with known solution) |
| `water_temperature_c` | DS18B20 waterproof temperature probe | 1-Wire | 12-bit digital temperature | Direct from DS18B20 library; returns °C |
| `water_level_cm` | DFRobot water level sensor (SKU:SEN0257) or ultrasonic (JSN-SR04T) | Analogue or UART | Voltage or distance | Calibrate to cm of water depth |
| `light_lux` | BH1750 (above-water, waterproof housing) | I²C | 16-bit lux | Direct from library |

### Key calibration notes

**Turbidity sensor orientation:** the DFRobot SEN0189 must be submerged
upright. Bubbles on the sensor face give false high readings. Use a still
water chamber if possible — avoid placing directly in fast-moving water.

**pH and temperature cross-sensitivity:** pH readings drift significantly
with temperature (Nernst factor). Always take a temperature reading
simultaneously and apply compensation. The DS18B20 provides this.

**EC and temperature:** same issue as soil EC — apply temperature compensation.
The DFR0300 library includes a compensation function.

**Waterproofing:** all sensors in water contact must be in waterproof housings
or have waterproof variants (DS18B20 waterproof probe is standard; pH and EC
probes must have waterproof BNC fittings). The ESP32 and LoRa module must
be in a sealed IP65 enclosure above the waterline.

---

## Challenge 5 — Security Events (`security_events.csv`)

### Sensors

| CSV column | Sensor | Interface | Raw output | Conversion |
|------------|--------|-----------|------------|------------|
| `motion_detected` | PIR motion sensor (HC-SR501 or DFRobot equivalant) | Digital GPIO | HIGH on motion, LOW at rest | Read GPIO; debounce in firmware; 1 = motion in interval |
| `door_open` | Reed switch | Digital GPIO | HIGH/LOW | As per gate reed switch above |
| `vibration_level` | DFRobot piezo vibration sensor or SW-420 | Digital GPIO or Analogue | Pulse or voltage | Normalise to 0–1; or read pulse count in window |
| `smoke_ppm` | MQ135 gas sensor | Analogue (ADC) | 0–3.3V proportional to gas concentration | Rs/Ro calibration: measure Ro in clean air; ppm = a × (Rs/Ro)^b (constants from datasheet per gas). Note: MQ135 is a broad-spectrum gas sensor, not a dedicated smoke detector — values are indicative |
| `sound_db` | DFRobot sound sensor (SKU:DFR0034) | Analogue (ADC) | 0–3.3V proportional to sound pressure | Convert ADC to dB via calibration — or report as a relative unit if absolute calibration is unavailable |
| `light_lux` | BH1750 | I²C | 16-bit lux | Direct from library |
| `flame_detected` | DFRobot flame sensor (SEN0059) | Digital GPIO or Analogue | HIGH on IR flame detection | Digital mode: read GPIO; 1 = flame IR detected |
| `panic_triggered` | DFRobot panic/push button | Digital GPIO | HIGH on press | Read GPIO with debounce; 1 = pressed in interval |

### Key notes

**MQ135 warm-up:** MQ-series sensors require a 24–48 hour burn-in period
and a 20-second warm-up after power-on before readings stabilise. Account
for this in firmware — discard readings taken in the first 30 seconds after
boot. The CSV `smoke_ppm` column is labelled as a proxy precisely because
MQ135 is not a calibrated smoke instrument.

**PIR sensitivity and range:** HC-SR501 has adjustable sensitivity and
delay. Set delay to minimum (a few seconds) for event-based logging at
15-minute resolution. False triggers can occur from sunlight, animals, and
temperature gradients — expect some false positives in real deployments.

**Sensor fusion in firmware:** the `alert_intrusion` column in the CSV
requires simultaneous motion + door + vibration + night. You can implement
this fusion logic on the ESP32 before transmission, or in post-processing
on the gateway/server. Edge fusion (on device) reduces network traffic and
works offline — a strong design choice for low-infrastructure contexts.

**Sound sensor:** consumer sound sensors (like DFR0034) are not calibrated
in absolute dB without further equipment. In practice, report a relative
value (0–1023 ADC range or normalised) and document this limitation clearly
in your technical report. The synthetic CSV uses an approximate dB scale.

---

## Packet structure — what a LoRa payload looks like

Each LoRa transmission should contain a compact, structured payload.
Example structure for water quality (JSON-style for clarity; binary packing
is more efficient in practice):

```json
{
  "node_id": "site_upstream",
  "ts": 1672531200,
  "ph": 7.24,
  "turb": 3.8,
  "cond": 142.5,
  "water_temp": 18.3,
  "level": 85.2,
  "lux": 42100,
  "bat_mv": 3720
}
```

The gateway unpacks this, adds a formatted timestamp, checks alert rules,
and writes a CSV row — matching the structure you see in `water_quality.csv`.

**LoRa payload size:** LoRaWAN limits payloads to 51–222 bytes depending on
spreading factor and region. Binary packing (e.g., multiplying float values
by 100 and sending as int16) fits 8–10 sensor readings comfortably.

---

## Summary table — sensors by challenge area

| Sensor | Challenge 1 (Soil) | Challenge 2 (Pest) | Challenge 3 (Livestock) | Challenge 4 (Water) | Challenge 5 (Security) |
|--------|:-:|:-:|:-:|:-:|:-:|
| BME280 (temp/humidity/pressure) | ✓ | ✓ | ✓ | — | — |
| BH1750 (light) | ✓ | ✓ | — | ✓ | ✓ |
| MPU6050 (accelerometer) | — | ✓ (vibration) | ✓ (activity) | — | — |
| DFRobot pH probe | ✓ | — | — | ✓ | — |
| DFRobot EC/conductivity | ✓ | — | — | ✓ | — |
| DFRobot turbidity (SEN0189) | — | — | — | ✓ | — |
| DFRobot leaf wetness | — | ✓ | — | — | — |
| DS18B20 waterproof temp | — | — | — | ✓ | — |
| GPS module (NEO-6M/M8N) | — | — | ✓ | — | — |
| Reed switch | — | — | ✓ (gate) | — | ✓ (door) |
| Vibration sensor (SW-420/piezo) | — | — | ✓ (fence) | — | ✓ |
| PIR (HC-SR501) | — | — | — | — | ✓ |
| MQ135 (gas/smoke proxy) | — | — | — | — | ✓ |
| DFRobot flame sensor | — | — | — | — | ✓ |
| DFRobot sound sensor | — | — | — | — | ✓ |
| Panic button | — | — | — | — | ✓ |

---

## Useful libraries (Arduino / ESP32)

| Sensor | Library |
|--------|---------|
| BME280 | `Adafruit_BME280` or `BME280` by finitespace |
| BH1750 | `BH1750` by Christopher Laws |
| MPU6050 | `MPU6050` by Electronic Cats, or `Adafruit_MPU6050` |
| DFRobot pH / EC / turbidity | DFRobot sensor libraries (GitHub: DFRobot/DFRobot_ESP_PH) |
| DS18B20 | `DallasTemperature` + `OneWire` |
| GPS (NMEA parsing) | `TinyGPS++` by Mikal Hart |
| LoRa | `LoRa` by Sandeep Mistry, or `RadioLib` |

All available through the Arduino Library Manager or as GitHub repositories.

---

## Further reading

- DFRobot sensor wiki: https://wiki.dfrobot.com
- ESP32 Arduino core: https://github.com/espressif/arduino-esp32
- TinyGPS++ documentation: http://arduiniana.org/libraries/tinygpsplus/
- LoRa library: https://github.com/sandeepmistry/arduino-LoRa
- RadioLib (more complete LoRa/LoRaWAN): https://github.com/jgromes/RadioLib
- NMEA sentence reference: https://gpsd.gitlab.io/gpsd/NMEA.html
