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

// Helper functions to avoid crashes if the CSV has missing or weird values
fun safeDouble(value: String, fieldName: String, lineNumber: Int): Double {
    return value.toDoubleOrNull() ?: run {
        println("Invalid $fieldName at line $lineNumber, defaulting to 0.0")
        0.0
    }
}

fun safeInt(value: String, fieldName: String, lineNumber: Int): Int {
    return value.toIntOrNull() ?: run {
        println("Invalid $fieldName at line $lineNumber, defaulting to 0")
        0
    }
}

// Loads the CSV file and converts each row into a WaterQualityReading object
fun loadWaterQualityData(filePath: String): List<WaterQualityReading> {
    val readings = mutableListOf<WaterQualityReading>()

    // Read all lines from the file
    val lines = File(filePath).readLines()

    // Start from index 1 to skip the header row
    for (i in 1 until lines.size) {
        // Split the row by commas and trim whitespace
        val row = lines[i].split(",").map { it.trim() }

        // Skip rows that don't have enough columns
        if (row.size < 17) {
            println("Skipping malformed row at line ${i + 1}")
            continue
        }

        // Create a reading object from the row
        val reading = WaterQualityReading(
            timestamp = row[0],
            siteId = row[1],
            ph = safeDouble(row[2], "ph", i + 1),
            turbidityNtu = safeDouble(row[3], "turbidity_ntu", i + 1),
            conductivityUsCm = safeDouble(row[4], "conductivity_uS_cm", i + 1),
            waterTemperatureC = safeDouble(row[5], "water_temperature_c", i + 1),
            waterLevelCm = safeDouble(row[6], "water_level_cm", i + 1),
            lightLux = safeDouble(row[7], "light_lux", i + 1),
            status = row[8],
            alertTriggered = safeInt(row[9], "alert_triggered", i + 1),
            alertPh = safeInt(row[10], "alert_ph", i + 1),
            alertTurbidity = safeInt(row[11], "alert_turbidity", i + 1),
            alertTurbidityCrit = safeInt(row[12], "alert_turbidity_crit", i + 1),
            alertConductivity = safeInt(row[13], "alert_conductivity", i + 1),
            wxTempC = safeDouble(row[14], "wx_temp_c", i + 1),
            wxRhPct = safeDouble(row[15], "wx_rh_pct", i + 1),
            wxRainMmHr = safeDouble(row[16], "wx_rain_mm_hr", i + 1)
        )

        // Add the reading to the list
        readings.add(reading)
    }

    return readings
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
}