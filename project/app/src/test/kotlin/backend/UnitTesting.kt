package backend

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class UnitTests {

    // helper so I don't have to repeat all fields every time I make a test reading
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

    // test the safe parsing functions
    @Test
    fun `safeDouble parses valid number`() {
        assertEquals(7.5, safeDouble("7.5", "ph", 1))
    }

    @Test
    fun `safeDouble handles invalid input`() {
        assertEquals(0.0, safeDouble("abc", "ph", 1))
    }

    @Test
    fun `safeDouble handles empty string`() {
        assertEquals(0.0, safeDouble("", "ph", 1))
    }

    @Test
    fun `safeInt parses valid number`() {
        assertEquals(1, safeInt("1", "alertTriggered", 1))
    }

    @Test
    fun `safeInt handles invalid input`() {
        assertEquals(0, safeInt("xyz", "alertTriggered", 1))
    }

    // tests for filtering readings by site
    @Test
    fun `getReadingsForSite only returns correct site`() {
        val readings = listOf(
            makeReading(siteId = "site_upstream"),
            makeReading(siteId = "site_downstream"),
            makeReading(siteId = "site_upstream")
        )
        assertEquals(2, getReadingsForSite(readings, "site_upstream").size)
    }

    // make sure whitespace/case differences don't break anything
    @Test
    fun `getReadingsForSite is case insensitive`() {
        val readings = listOf(
            makeReading(siteId = "SITE_UPSTREAM"),
            makeReading(siteId = "site_upstream")
        )
        assertEquals(2, getReadingsForSite(readings, "site_upstream").size)
    }

    @Test
    fun `getReadingsForSite returns empty when no matches`() {
        val readings = listOf(makeReading(siteId = "site_upstream"))
        assertEquals(0, getReadingsForSite(readings, "site_reservoir").size)
    }

    // tests for alert filtering
    @Test
    fun `getAlertReadings only returns triggered alerts`() {
        val readings = listOf(
            makeReading(alertTriggered = 1),
            makeReading(alertTriggered = 0),
            makeReading(alertTriggered = 1)
        )
        assertEquals(2, getAlertReadings(readings).size)
    }

    @Test
    fun `getAlertReadings returns empty when no alerts`() {
        val readings = listOf(
            makeReading(alertTriggered = 0),
            makeReading(alertTriggered = 0)
        )
        assertEquals(0, getAlertReadings(readings).size)
    }

    @Test
    fun `getReadingsByStatus filters by status correctly`() {
        val readings = listOf(
            makeReading(status = "normal"),
            makeReading(status = "warning"),
            makeReading(status = "critical"),
            makeReading(status = "normal")
        )
        assertEquals(2, getReadingsByStatus(readings, "normal").size)
    }

    @Test
    fun `getReadingsByStatus is case insensitive`() {
        val readings = listOf(
            makeReading(status = "NORMAL"),
            makeReading(status = "normal")
        )
        assertEquals(2, getReadingsByStatus(readings, "normal").size)
    }

    @Test
    fun `getAlertReadingsForSite only returns alerts for that site`() {
        val readings = listOf(
            makeReading(siteId = "site_upstream",   alertTriggered = 1),
            makeReading(siteId = "site_upstream",   alertTriggered = 0),
            makeReading(siteId = "site_downstream", alertTriggered = 1)
        )
        assertEquals(1, getAlertReadingsForSite(readings, "site_upstream").size)
    }

    // tests for the alert breakdown function
    @Test
    fun `getAlertTypeBreakdownForSite counts each alert type`() {
        val readings = listOf(
            makeReading(siteId = "site_upstream",   alertPh = 1),
            makeReading(siteId = "site_upstream",   alertPh = 1, alertTurbidity = 1),
            makeReading(siteId = "site_upstream",   alertConductivity = 1),
            makeReading(siteId = "site_downstream", alertPh = 1)
        )
        val result = getAlertTypeBreakdownForSite(readings, "site_upstream")
        assertEquals(2, result["ph"])
        assertEquals(1, result["turbidity"])
        assertEquals(1, result["conductivity"])
    }

    @Test
    fun `getAlertTypeBreakdownForSite ignores other sites`() {
        val readings = listOf(
            makeReading(siteId = "site_downstream", alertPh = 1)
        )
        val result = getAlertTypeBreakdownForSite(readings, "site_upstream")
        assertEquals(0, result["ph"])
    }

    // tests for getting the latest reading
    @Test
    fun `getLatestReadingForSite returns most recent timestamp`() {
        val readings = listOf(
            makeReading(siteId = "site_upstream", timestamp = "2024-01-01 08:00:00"),
            makeReading(siteId = "site_upstream", timestamp = "2024-01-03 10:00:00"),
            makeReading(siteId = "site_upstream", timestamp = "2024-01-02 12:00:00")
        )
        assertEquals("2024-01-03 10:00:00", getLatestReadingForSite(readings, "site_upstream")?.timestamp)
    }

    @Test
    fun `getLatestReadingForSite returns null when site has no readings`() {
        val readings = listOf(makeReading(siteId = "site_upstream"))
        assertNull(getLatestReadingForSite(readings, "site_reservoir"))
    }
}