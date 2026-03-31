import backend.getAlertReadings
import backend.getReadingsForSite
import backend.loadWaterQualityData
import io.ktor.server.engine.embeddedServer
import io.ktor.server.netty.Netty
import io.ktor.server.response.respondText
import io.ktor.server.routing.get
import io.ktor.server.routing.routing

fun main() {
    val filePath = "../../datasets/datasets/synthetic_outputs/water_quality.csv"
    val waterReadings = loadWaterQualityData(filePath)

    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        routing {

            // Home
            get("/") {
                call.respondText("Hello, World!")
            }

            // Alerts
            get("/alerts") {
                val alertReadings = getAlertReadings(waterReadings)
                call.respondText("Total alert-triggered readings: ${alertReadings.size}")
            }

            // Site-specific (hardcoded for now)
            get("/site/site_upstream") {
                val siteReadings = getReadingsForSite(waterReadings, "site_upstream")
                call.respondText("Total readings for site_upstream: ${siteReadings.size}")
            }
        }
    }.start(wait = true)
}