// src/main/kotlin/backend/Main.kt
package backend

import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.routing.*
import io.ktor.server.response.*

fun main() {
    println("Starting server…") // optional, just to see startup

    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        routing {
            get("/") {
                call.respondText("Hello, World! Server is running.")
            }
            // Add more routes here later
        }
    }.start(wait = true)
}