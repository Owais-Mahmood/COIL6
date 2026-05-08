package backend

import io.ktor.client.statement.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.ktor.server.testing.*
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertContains

class IntegrationTests {

    // same helper as unit tests so I don't have to fill every field each time
    private fun makeReading(
        siteId: String = "site_upstream",
        status: String = "normal",
        alertTriggered: Int = 0,
        alertPh: Int = 0,
        alertTurbidity: Int = 0,
        alertConductivity: Int = 0,
        timestamp: String = "2024-01-01 00:00:00"
    ) = WaterQualityReading(
        timestamp = timestamp,
        siteId = siteId,
        ph = 7.0,
        turbidityNtu = 2.0,
        conductivityUsCm = 500.0,
        waterTemperatureC = 20.0,
        waterLevelCm = 100.0,
        lightLux = 5000.0,
        status = status,
        alertTriggered = alertTriggered,
        alertPh = alertPh,
        alertTurbidity = alertTurbidity,
        alertTurbidityCrit = 0,
        alertConductivity = alertConductivity,
        wxTempC = 22.0,
        wxRhPct = 60.0,
        wxRainMmHr = 0.0
    )

    // set up a mini app with test data so we don't need the real CSV
    private fun ApplicationTestBuilder.setupApp(readings: List<WaterQualityReading>) {
        application {
            install(ContentNegotiation) { json() }
            routing {
                get("/alerts") {
                    val alerts = getAlertReadings(readings)
                    call.respond(mapOf("count" to alerts.size))
                }
                get("/alerts/{siteId}") {
                    val siteId = call.parameters["siteId"]
                    if (siteId.isNullOrBlank()) {
                        call.respond(HttpStatusCode.BadRequest, mapOf("error" to "No site ID provided."))
                        return@get
                    }
                    val alerts = getAlertReadingsForSite(readings, siteId)
                    call.respond(mapOf("count" to alerts.size))
                }
                get("/site/{siteId}") {
                    val siteId = call.parameters["siteId"]
                    if (siteId.isNullOrBlank()) {
                        call.respond(HttpStatusCode.BadRequest, mapOf("error" to "No site ID provided."))
                        return@get
                    }
                    val siteReadings = getReadingsForSite(readings, siteId)
                    call.respond(mapOf("count" to siteReadings.size))
                }
                get("/status/{status}") {
                    val status = call.parameters["status"]
                    if (status.isNullOrBlank()) {
                        call.respond(HttpStatusCode.BadRequest, mapOf("error" to "No status provided."))
                        return@get
                    }
                    val statusReadings = getReadingsByStatus(readings, status)
                    call.respond(mapOf("count" to statusReadings.size))
                }
            }
        }
    }

    // tests for the main API endpoints
    @Test
    fun `alerts endpoint returns 200`() = testApplication {
        setupApp(listOf(makeReading(alertTriggered = 1), makeReading(alertTriggered = 0)))
        val response = client.get("/alerts")
        assertEquals(HttpStatusCode.OK, response.status)
    }

    @Test
    fun `alerts endpoint returns correct count`() = testApplication {
        setupApp(listOf(
            makeReading(alertTriggered = 1),
            makeReading(alertTriggered = 1),
            makeReading(alertTriggered = 0)
        ))
        val response = client.get("/alerts")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "2")
    }

    @Test
    fun `site endpoint returns 200 for known site`() = testApplication {
        setupApp(listOf(makeReading(siteId = "site_upstream")))
        val response = client.get("/site/site_upstream")
        assertEquals(HttpStatusCode.OK, response.status)
    }

    @Test
    fun `site endpoint returns correct count`() = testApplication {
        setupApp(listOf(
            makeReading(siteId = "site_upstream"),
            makeReading(siteId = "site_upstream"),
            makeReading(siteId = "site_downstream")
        ))
        val response = client.get("/site/site_upstream")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "2")
    }

    @Test
    fun `status endpoint returns correct count`() = testApplication {
        setupApp(listOf(
            makeReading(status = "warning"),
            makeReading(status = "warning"),
            makeReading(status = "normal")
        ))
        val response = client.get("/status/warning")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "2")
    }

    // check the API doesn't crash on weird or malicious inputs
    @Test
    fun `alerts endpoint handles unknown site gracefully`() = testApplication {
        setupApp(listOf(makeReading(siteId = "site_upstream")))
        val response = client.get("/alerts/site_unknown")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "0")
    }

    @Test
    fun `site endpoint handles sql injection style input`() = testApplication {
        setupApp(listOf(makeReading(siteId = "site_upstream")))
        val response = client.get("/site/'; DROP TABLE readings; --")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "0")
    }

    @Test
    fun `status endpoint handles unexpected status value`() = testApplication {
        setupApp(listOf(makeReading(status = "normal")))
        val response = client.get("/status/invalid_status")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "0")
    }

    @Test
    fun `alerts endpoint handles empty dataset`() = testApplication {
        setupApp(emptyList())
        val response = client.get("/alerts")
        assertEquals(HttpStatusCode.OK, response.status)
        assertContains(response.bodyAsText(), "0")
    }
}