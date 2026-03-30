import io.ktor.server.application.*
import io.ktor.server.http.content.*
import io.ktor.server.routing.*
import io.ktor.server.response.*

fun Application.configureRouting() {

    // routing logic to resolve image linking issues
    routing { 
        staticResources("/","front-end")
    
    //the route from pressing "continue as guest" to the guest dashboard
        get("/guest") {
            call.respondRedirect(/GuestDashboard.html)
        }
    }
}