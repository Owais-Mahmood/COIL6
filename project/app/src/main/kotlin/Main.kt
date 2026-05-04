import backend.getAlertReadings
import backend.getAlertReadingsForSite
import backend.getAlertTypeBreakdownForSite
import backend.getLatestReadingForSite
import backend.getReadingsByStatus
import backend.getReadingsForSite
import backend.loadWaterQualityData
import io.ktor.server.application.install
import io.ktor.server.engine.embeddedServer
import io.ktor.server.http.content.staticResources
import io.ktor.server.netty.Netty
import io.ktor.server.plugins.contentnegotiation.ContentNegotiation
import io.ktor.server.response.respond
import io.ktor.server.response.respondRedirect
import io.ktor.server.routing.get
import io.ktor.server.routing.routing
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.Serializable
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter


@Serializable
data class AlertSummary(
    val type: String,
    val count: Int
)

@Serializable
data class SiteSummary(
    val siteId: String,
    val count: Int
)

@Serializable
data class StatusSummary(
    val status: String,
    val count: Int
)

@Serializable
data class ErrorResponse(
    val error: String
)

@Serializable
data class StatusCountItem(
    val status: String,
    val count: Int
)

@Serializable
data class SiteCountItem(
    val siteId: String,
    val count: Int
)

@Serializable
data class AlertBreakdownResponse(
    val siteId: String,
    val ph: Int,
    val turbidity: Int,
    val conductivity: Int,
    val total: Int
)

@Serializable
data class LatestReadingResponse(
    val timestamp: String,
    val siteId: String,
    val ph: Double,
    val turbidityNtu: Double,
    val conductivityUsCm: Double,
    val waterTemperatureC: Double,
    val waterLevelCm: Double,
    val lightLux: Double,
    val status: String,
    val wxTempC: Double,
    val wxRhPct: Double,
    val wxRainMmHr: Double
)

@Serializable
data class TrendPoint(
    val timestamp: String,
    val ph: Double,
    val turbidityNtu: Double,
    val conductivityUsCm: Double,
    val waterTemperatureC: Double,
    val waterLevelCm: Double,
    val lightLux: Double
)


@Serializable
data class RecentAlert(
    val metric: String,
    val value: Double,
    val status: String,
    val timestamp: String
)

@Serializable
data class AlertTimeSummaryResponse(
    val siteId: String,
    val total: Int,
    val daily: Int,
    val weekly: Int,
    val monthly: Int
)

fun main() {
    val filePath = "../../datasets/datasets/synthetic_outputs/water_quality.csv"
    var waterReadings = loadWaterQualityData(filePath)
    
    val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

    val latestTimestamp = waterReadings.maxOf { LocalDateTime.parse(it.timestamp, formatter) }
    val offset = java.time.Duration.between(latestTimestamp, LocalDateTime.now())

    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {

        install(ContentNegotiation) {
            json()
        }

        routing {

            // Serve frontend files
            staticResources("/", "front-end")

            // Login page first
            get("/") {
                call.respondRedirect("/dashboard.html")
            }

            // Alerts route
            get("/alerts") {
                val alertReadings = getAlertReadings(waterReadings)
                call.respond(AlertSummary("alerts", alertReadings.size))
            }

            // Alert count for a specific site
            get("/alerts/{siteId}") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val alertReadings = getAlertReadingsForSite(waterReadings, siteId)
                call.respond(AlertSummary("alerts", alertReadings.size))
            }

            // Alert type breakdown for a specific site
            get("/alerts/{siteId}/breakdown") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val breakdown = getAlertTypeBreakdownForSite(waterReadings, siteId)
                call.respond(
                    AlertBreakdownResponse(
                        siteId = siteId,
                        ph = breakdown["ph"] ?: 0,
                        turbidity = breakdown["turbidity"] ?: 0,
                        conductivity = breakdown["conductivity"] ?: 0,
                        total = (breakdown["ph"] ?: 0) + (breakdown["turbidity"] ?: 0) + (breakdown["conductivity"] ?: 0)
                    )
                )
            }

            // Dynamic site route
            get("/site/{siteId}") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val siteReadings = getReadingsForSite(waterReadings, siteId)
                call.respond(SiteSummary(siteId, siteReadings.size))
            }

            // Dynamic status route
            get("/status/{status}") {
                val status = call.parameters["status"]

                if (status.isNullOrBlank()) {
                    call.respond(ErrorResponse("No status provided."))
                    return@get
                }

                val statusReadings = getReadingsByStatus(waterReadings, status)
                call.respond(StatusSummary(status, statusReadings.size))
            }

            // Summary of status counts
            get("/summary/status-counts") {
                val statuses = listOf("normal", "warning", "critical")

                val results = statuses.map { status ->
                    StatusCountItem(
                        status = status,
                        count = getReadingsByStatus(waterReadings, status).size
                    )
                }

                call.respond(results)
            }

            // Summary of site counts
            get("/summary/site-counts") {
                val siteIds = waterReadings
                    .map { it.siteId.trim() }
                    .distinct()
                    .sorted()

                val results = siteIds.map { siteId ->
                    SiteCountItem(
                        siteId = siteId,
                        count = getReadingsForSite(waterReadings, siteId).size
                    )
                }

                call.respond(results)
            }

            // Latest reading for a given site
            get("/latest/{siteId}") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val latestReading = getLatestReadingForSite(waterReadings, siteId)

                if (latestReading == null) {
                    call.respond(ErrorResponse("No readings found for site: $siteId"))
                } else {
                    call.respond(
                        LatestReadingResponse(
                            timestamp = LocalDateTime.parse(latestReading.timestamp, formatter).plus(offset).format(formatter),
                            siteId = latestReading.siteId,
                            ph = latestReading.ph,
                            turbidityNtu = latestReading.turbidityNtu,
                            conductivityUsCm = latestReading.conductivityUsCm,
                            waterTemperatureC = latestReading.waterTemperatureC,
                            waterLevelCm = latestReading.waterLevelCm,
                            lightLux = latestReading.lightLux,
                            status = latestReading.status,
                            wxTempC = latestReading.wxTempC,
                            wxRhPct = latestReading.wxRhPct,
                            wxRainMmHr = latestReading.wxRainMmHr
                        )
                    )
                }
            }

            //Getting last 10 alerts
            get("/alerts/{siteId}/recent") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val alerts = getAlertReadingsForSite(waterReadings, siteId)
                    .sortedByDescending { it.timestamp }
                    .take(10)
                    .flatMap { reading ->

                        val ts = LocalDateTime.parse(reading.timestamp, formatter)
                            .plus(offset)
                            .format(formatter)

                        listOfNotNull(
                            if (reading.ph < 6.5 || reading.ph > 8.5)
                                RecentAlert("ph", reading.ph, reading.status, ts) else null,

                            if (reading.turbidityNtu > 1)
                                RecentAlert("turbidity", reading.turbidityNtu, reading.status, ts) else null,

                            if (reading.conductivityUsCm > 1700)
                                RecentAlert("conductivity", reading.conductivityUsCm, reading.status, ts) else null
                        )
                    }

                call.respond(alerts.take(5))
            }


            // Displaying alert no. by time frame
            get("/alerts/{siteId}/summary") {
                val siteIdRaw = call.parameters["siteId"]

                val siteId = siteIdRaw
                    ?.replace("site_", "")
                    ?.replaceFirstChar { it.uppercase() }

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val alerts = getAlertReadingsForSite(waterReadings, siteId)

                val now = LocalDateTime.now()

                val dailyCutoff   = now.minusDays(1)
                val weeklyCutoff  = now.minusWeeks(1)
                val monthlyCutoff = now.minusMonths(1)

                val parsedAlerts = alerts.map {
                    LocalDateTime.parse(it.timestamp, formatter)
                }

                val total   = parsedAlerts.size
                val daily   = parsedAlerts.count { it.isAfter(dailyCutoff) }
                val weekly  = parsedAlerts.count { it.isAfter(weeklyCutoff) }
                val monthly = parsedAlerts.count { it.isAfter(monthlyCutoff) }

                call.respond(
                    AlertTimeSummaryResponse(
                        siteId = siteId,
                        total = total,
                        daily = daily,
                        weekly = weekly,
                        monthly = monthly
                    )
                )
            }

            // Trend data for a given site
            get("/trends/{siteId}") {
                val siteId = call.parameters["siteId"]

                if (siteId.isNullOrBlank()) {
                    call.respond(ErrorResponse("No site ID provided."))
                    return@get
                }

                val siteReadings = getReadingsForSite(waterReadings, siteId)
                    .sortedBy { it.timestamp }
                    .takeLast(200)

                if (siteReadings.isEmpty()) {
                    call.respond(ErrorResponse("No readings found for site: $siteId"))
                } else {
                    val trendData = siteReadings.map { reading ->
                        TrendPoint(
                            timestamp = LocalDateTime.parse(reading.timestamp, formatter).plus(offset).format(formatter),
                            ph = reading.ph,
                            turbidityNtu = reading.turbidityNtu,
                            conductivityUsCm = reading.conductivityUsCm,
                            waterTemperatureC = reading.waterTemperatureC,
                            waterLevelCm = reading.waterLevelCm,
                            lightLux = reading.lightLux
                        )
                    }

                    call.respond(trendData)
                }
            }
        }
    }.start(wait = true)
}