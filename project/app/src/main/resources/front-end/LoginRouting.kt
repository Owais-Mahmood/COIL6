import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.http.content.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.ktor.server.sessions.*

data class UserSession(val isOfficial: Boolean)

fun Application.configureRouting() {

    install(Sessions) {
        cookie<UserSession>("user_session") {
            cookie.path = "/"
            cookie.maxAgeInSeconds = 3600
        }
    }

    routing {
        staticResources("/", "front-end")

        post("/login") {
            val params = call.receiveParameters()
            val email    = params["email"]    ?: ""
            val password = params["password"] ?: ""

            if (email == "official@gov.za" && password == "demo2026") {
                call.sessions.set(UserSession(isOfficial = true))
                call.respondRedirect("/dashboard-government.html")
            } else {
                call.respondRedirect("/login.html?error=1")
            }
        }

        get("/logout") {
            call.sessions.clear<UserSession>()
            call.respondRedirect("/login.html")
        }
    }
}