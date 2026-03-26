package backend

import java.io.File

// Data class representing one row of water quality readings
data class WaterQualityReading(
    val timestamp: String,
    val siteId: String,
    val ph: Double,
    val turbidityNtu: Double,
    val conductivityUsCm: Double,
    val waterTemperatureC: Double,
    val waterLevelCm: Double,
    val lightLux: Double,
    val status: String,
    val alertTriggered: Int,
    val alertPh: Int,
    val alertTurbidity: Int,
    val alertTurbidityCrit: Int,
    val alertConductivity: Int,
    val wxTempC: Double,
    val wxRhPct: Double,
    val wxRainMmHr: Double
)

// If a value can't be parsed, use a default instead of crashing
fun safeDouble(value: String, fieldName: String, lineNumber: Int): Double {
    return value.toDoubleOrNull() ?: 0.0
}

fun safeInt(value: String, fieldName: String, lineNumber: Int): Int {
    return value.toIntOrNull() ?: 0
}

// Loads the CSV file and converts each row into a WaterQualityReading object
fun loadWaterQualityData(filePath: String): List<WaterQualityReading> {
    val readings = mutableListOf<WaterQualityReading>()

    // Read all lines from the file
    val lines = File(filePath).readLines()

    // Start from index 1 to skip the header row
    for (i in 1 until lines.size) {
        val lineNumber = i + 1

        // Split the row by commas and trim whitespace
        val row = lines[i].split(",").map { it.trim() }

        // Skip rows that don't have enough columns
        if (row.size < 17) {
            println("Skipping malformed row at line $lineNumber")
            continue
        }

        // Create a reading object from the row
        val reading = WaterQualityReading(
            timestamp = row[0],
            siteId = row[1],
            ph = safeDouble(row[2], "ph", lineNumber),
            turbidityNtu = safeDouble(row[3], "turbidity_ntu", lineNumber),
            conductivityUsCm = safeDouble(row[4], "conductivity_uS_cm", lineNumber),
            waterTemperatureC = safeDouble(row[5], "water_temperature_c", lineNumber),
            waterLevelCm = safeDouble(row[6], "water_level_cm", lineNumber),
            lightLux = safeDouble(row[7], "light_lux", lineNumber),
            status = row[8],
            alertTriggered = safeInt(row[9], "alert_triggered", lineNumber),
            alertPh = safeInt(row[10], "alert_ph", lineNumber),
            alertTurbidity = safeInt(row[11], "alert_turbidity", lineNumber),
            alertTurbidityCrit = safeInt(row[12], "alert_turbidity_crit", lineNumber),
            alertConductivity = safeInt(row[13], "alert_conductivity", lineNumber),
            wxTempC = safeDouble(row[14], "wx_temp_c", lineNumber),
            wxRhPct = safeDouble(row[15], "wx_rh_pct", lineNumber),
            wxRainMmHr = safeDouble(row[16], "wx_rain_mm_hr", lineNumber)
        )

        readings.add(reading)
    }

    return readings
}

// Returns only the readings that match the given site ID
fun getReadingsForSite(
    readings: List<WaterQualityReading>,
    siteId: String
): List<WaterQualityReading> {

    // Normalise both sides to avoid case/whitespace mismatches
    val target = siteId.trim().lowercase()

    return readings.filter { it.siteId.trim().lowercase() == target }
}

// Returns only the readings where an alert has been triggered
fun getAlertReadings(readings: List<WaterQualityReading>): List<WaterQualityReading> {
    return readings.filter { it.alertTriggered == 1 }
}

// Returns only the readings that match the given status
fun getReadingsByStatus(
    readings: List<WaterQualityReading>,
    status: String
): List<WaterQualityReading> {

    // Normalise both sides to avoid case/whitespace mismatches
    val target = status.trim().lowercase()

    return readings.filter { it.status.trim().lowercase() == target }
}

fun main() {
    val filePath = "../../datasets/datasets/synthetic_outputs/water_quality.csv"
    
    // Load all readings from the CSV
    val waterReadings = loadWaterQualityData(filePath)

    println("Loaded ${waterReadings.size} readings")

    if (waterReadings.isNotEmpty()) {
        println("First reading:")
        println(waterReadings[0])
    }

    // Test filtering by site
    val siteToCheck = "site_upstream"
    val siteReadings = getReadingsForSite(waterReadings, siteToCheck)

    println("Readings count for $siteToCheck: ${siteReadings.size}")

    if (siteReadings.isNotEmpty()) {
        println("First reading for $siteToCheck:")
        println(siteReadings[0])
    } else {
        println("No readings found for site: $siteToCheck")
    }

    // Test filtering alert readings
    val alertReadings = getAlertReadings(waterReadings)

    println("Total alert-triggered readings: ${alertReadings.size}")

    if (alertReadings.isNotEmpty()) {
        println("First alert reading:")
        println(alertReadings[0])
    } else {
        println("No alert-triggered readings found.")
    }

    // Test filtering by status
    val statusToCheck = "critical"
    val statusReadings = getReadingsByStatus(waterReadings, statusToCheck)

    println("Total $statusToCheck readings: ${statusReadings.size}")

    if (statusReadings.isNotEmpty()) {
        println("First $statusToCheck reading:")
        println(statusReadings[0])
    } else {
        println("No $statusToCheck readings found.")
    }
}