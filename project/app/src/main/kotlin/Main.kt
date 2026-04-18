import backend.getAlertReadings
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
data class LatestReadingResponse(
    val timestamp: String,
    val siteId: String,
    val ph: Double,
    val turbidityNtu: Double,
    val conductivityUsCm: Double,
    val waterTemperatureC: Double,
    val waterLevelCm: Double,
    val lightLux: Double,
    val status: String
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

fun main() {
    val filePath = "../../datasets/datasets/synthetic_outputs/water_quality.csv"
    val waterReadings = loadWaterQualityData(filePath)

    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {

        install(ContentNegotiation) {
            json()
        }

        routing {

            // Serve frontend files
            staticResources("/", "front-end")

            // Login page first
            get("/") {
                call.respondRedirect("/login.html")
            }

            // Enter guest dashboard
            get("/guest") {
                call.respondRedirect("/GuestDashboard.html")
            }

            // Alerts route
            get("/alerts") {
                val alertReadings = getAlertReadings(waterReadings)
                call.respond(AlertSummary("alerts", alertReadings.size))
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
                            timestamp = latestReading.timestamp,
                            siteId = latestReading.siteId,
                            ph = latestReading.ph,
                            turbidityNtu = latestReading.turbidityNtu,
                            conductivityUsCm = latestReading.conductivityUsCm,
                            waterTemperatureC = latestReading.waterTemperatureC,
                            waterLevelCm = latestReading.waterLevelCm,
                            lightLux = latestReading.lightLux,
                            status = latestReading.status
                        )
                    )
                }
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
                    .takeLast (200)

                if (siteReadings.isEmpty()) {
                    call.respond(ErrorResponse("No readings found for site: $siteId"))
                } else {
                    val trendData = siteReadings.map { reading ->
                        TrendPoint(
                            timestamp = reading.timestamp,
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