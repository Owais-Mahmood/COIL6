

fun Application.configureRouting() {
    
    // routing logic to resolve image linking issues
    routing { 
        staticResources("/","front-end")
    }

}