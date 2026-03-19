package com.example

import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.html.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.request.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.html.*
import org.jetbrains.exposed.sql.transactions.transaction
import org.jetbrains.exposed.sql.*
import java.time.LocalDate
import io.ktor.server.sessions.*

fun Application.configureRouting() {
    routing {
        get("/") {
            val query = call.request.queryParameters["q"] ?: ""
            val session = call.sessions.get<UserSession>()
            
            val results = if (query.isNotBlank()) {
                transaction {
                    Books.selectAll()
                        .where { 
                            (Books.title.lowerCase() like "%${query.lowercase()}%") or 
                            (Books.author.lowerCase() like "%${query.lowercase()}%") or
                            (Books.isbn like "%$query%")
                        }
                        .map {
                            val bookId = it[Books.bookId]
                            val isCheckedOut = Checkouts.selectAll()
                                .where { Checkouts.bookId eq bookId }
                                .count() > 0
                            val isReserved = Reservations.selectAll()
                                .where { Reservations.bookId eq bookId }
                                .count() > 0
                            
                            mapOf(
                                "id" to bookId,
                                "title" to it[Books.title],
                                "author" to it[Books.author],
                                "isbn" to it[Books.isbn],
                                "format" to it[Books.formatCode],
                                "location" to it[Books.locationCode],
                                "checkedOut" to isCheckedOut,
                                "reserved" to isReserved
                            )
                        }
                }
            } else emptyList()
            
            call.respondHtml {
                head { 
                    title("Library Search")
                    link(rel="stylesheet", href="/static/css/search.css")
                }
                body {
                    div(classes = "nav-header") {
                        if (session != null) {
                            p { +"Welcome, ${session.username}!" }
                            div(classes = "nav-links") {
                                a(href = "/home/${session.userId}") { +"Home" }
                                a(href = "/logout") { +"Logout" }
                            }
                        } else {
                            div(classes = "nav-links") {
                                a(href = "/login") { +"Login" }
                                a(href = "/sign-up") { +"Sign Up" }
                            }
                        }
                    }
                    
                    div(classes = "search-container") {
                        h1 { +"Book Search" }
                        form(action = "/", method = FormMethod.get, classes = "search-form") {
                            input(type = InputType.text, name = "q") {
                                value = query
                                placeholder = "Search by title or author..."
                            }
                            submitInput { value = "Search" }
                        }

                        if (query.isNotBlank()) {
                            h2 { +"Search results for \"$query\""}
                            if (results.isEmpty()) {
                                p { +"No books found." }
                            } else {
                                p(classes = "result-count") { +"Found ${results.size} result(s)" }
                                results.forEach { book ->
                                    div(classes = "result") {
                                        a(href = "/book/${book["id"]}", classes = "result-title") {
                                            +book["title"].toString()
                                        }
                                        div(classes = "result-meta") {
                                            +"by ${book["author"]}"
                                        }
                                        div(classes = "result-meta") {
                                            +"ISBN: ${book["isbn"] ?: "N/A"} | "
                                            +"Format: ${book["format"] ?: "N/A"} | "
                                            +"Location: ${book["location"] ?: "N/A"}"
                                        }
                                        div(classes = "result-meta") {
                                            val checkoutStatus = if (book["checkedOut"] == true) "Checked Out" else "Available"
                                            val reserveStatus = if (book["reserved"] == true) "Reserved" else "Available"
                                            span(classes = if (book["checkedOut"] == true) "status-unavailable" else "status-available") {
                                                +"Checkout: $checkoutStatus"
                                            }
                                            +" | "
                                            span(classes = if (book["reserved"] == true) "status-unavailable" else "status-available") {
                                                +"Reserve: $reserveStatus"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        get("/search") {
            call.respondRedirect("/")
        }

        get("/book/{id}") {
            val id = call.parameters["id"]?.toIntOrNull()

            val book = id?.let {
                transaction {
                    Books.selectAll().where { Books.bookId eq it }.singleOrNull()
                }
            }

            call.respondHtml {
                head { 
                    title("Book Detail")
                    link(rel="stylesheet", href="/static/css/book.css")
                }
                body {
                    div(classes = "book-container") {
                        if (book == null) {
                            p { +"Book not found." }
                            a(href = "/") { +"Back to search" }
                        } else {
                            div(classes = "book-header") {
                                h1 { +book[Books.title] }
                            }
                            
                            div(classes = "book-details") {
                                p { +"Author: ${book[Books.author]}" }
                                p { +"ISBN: ${book[Books.isbn] ?: "N/A"}" }
                                p { +"Format: ${book[Books.formatCode] ?: "N/A"}" }
                                p { +"Location: ${book[Books.locationCode] ?: "N/A"}" }
                                if (book[Books.notes] != null) {
                                    p { +"Notes: ${book[Books.notes]}" }
                                }
                            }
                            
                            div(classes = "book-actions") {
                                form(action = "/checkout/${book[Books.bookId]}", method = FormMethod.post) {
                                    submitInput(classes = "action-button checkout-button") { value = "Checkout" }
                                }
                                form(action = "/reserve/${book[Books.bookId]}", method = FormMethod.post) {
                                    submitInput(classes = "action-button reserve-button") { value = "Reserve" }
                                }
                            }
                            
                            div(classes = "book-footer") {
                                a(href = "/") { +"Back to search" }
                            }
                        }
                    }
                }
            }

            if (book != null) {
                println(book[Books.title])
            }
        }

        post("/checkout/{id}") {
            val bookId = call.parameters["id"]?.toIntOrNull()
            val session = call.sessions.get<UserSession>()
            val userId = session?.userId ?: 1

            val result = bookId?.let {
                transaction {
                    val alreadyCheckedOut = Checkouts.selectAll()
                        .where { Checkouts.bookId eq it }
                        .count() > 0

                    if (alreadyCheckedOut) {
                        "already_checked_out"
                    } else {
                        Checkouts.insert {
                            it[Checkouts.bookId] = bookId
                            it[Checkouts.userId] = userId
                            it[dueDate] = LocalDate.now().plusDays(14)
                            it[timesRenewed] = 0
                        }                        
                        "success"
                    }
                }
            } ?: "error"

            call.respondHtml {
                head { 
                    title("Checkout") 
                    script {
                        unsafe {
                            when (result) {
                                "already_checked_out" -> raw("alert('This book is already checked out!'); window.location.href = '/book/$bookId';")
                                "success" -> raw("alert('Book checked out successfully!'); window.location.href = '/book/$bookId';")
                                else -> raw("alert('Error processing checkout'); window.location.href = '/book/$bookId';")
                            }
                        }
                    }
                }
                body { }
            }
        }

        post("/reserve/{id}") {
            val bookId = call.parameters["id"]?.toIntOrNull()
            val session = call.sessions.get<UserSession>()
            val userId = session?.userId ?: 1

            val result = bookId?.let {
                transaction {
                    val checkout = Checkouts.selectAll()
                        .where { Checkouts.bookId eq it }
                        .singleOrNull()
                    
                    val alreadyReserved = Reservations.selectAll()
                        .where { Reservations.bookId eq it }
                        .count() > 0

                    when {
                        checkout == null -> "not_checked_out"
                        alreadyReserved -> "already_reserved"
                        else -> {
                            val availableFrom = checkout[Checkouts.dueDate]
                            val expiryDate = availableFrom.plusDays(5)
                            
                            Reservations.insert {
                                it[Reservations.bookId] = bookId
                                it[Reservations.userId] = userId
                                it[Reservations.expiryDate] = expiryDate
                            }
                            "success:$availableFrom:$expiryDate"
                        }
                    }
                }
            } ?: "error"

            call.respondHtml {
                head { 
                    title("Reserve") 
                    script {
                        unsafe {
                            val parts = result.split(":")
                            when (parts[0]) {
                                "not_checked_out" -> raw("alert('This book is not checked out. You can check it out directly instead.'); window.location.href = '/book/$bookId';")
                                "already_reserved" -> raw("alert('This book is already reserved!'); window.location.href = '/book/$bookId';")
                                "success" -> {
                                    val availableFrom = parts.getOrNull(1) ?: ""
                                    val expiryDate = parts.getOrNull(2) ?: ""
                                    raw("alert('Book reserved successfully! Available from $availableFrom until $expiryDate'); window.location.href = '/book/$bookId';")
                                }
                                else -> raw("alert('Error processing reservation'); window.location.href = '/book/$bookId';")
                            }
                        }
                    }
                }
                body { }
            }
        }

        get("/sign-up") {
            call.respondHtml {
                head {
                    title("Sign Up")
                    link(rel="stylesheet", href="/static/css/logsignup.css")
                }
                body { 
                    div(classes = "auth-container") {
                        h1 { +"Sign up" }
                        form(action = "/sign-up", method = FormMethod.post, classes = "auth-form") {
                            div(classes = "form-group") {
                                label {
                                    htmlFor = "username"
                                    +"Username"
                                }
                                input(type = InputType.text, name = "username") {
                                    id = "username"
                                    required = true
                                    placeholder = "Enter Username"
                                }
                            }
                            div(classes = "form-group") {
                                label {
                                    htmlFor = "password"
                                    +"Password"
                                }
                                input(type = InputType.password, name = "password") {
                                    id = "password"
                                    required = true
                                    placeholder = "Enter Password"
                                }
                            }
                            submitInput(classes = "auth-submit") { value = "Sign up" }
                        }
                        div(classes = "auth-footer") {
                            a(href = "/login") { +"Log in instead" }
                        }
                    }
                }
            }
        }

        post("/sign-up") {
            val params = call.receiveParameters()
            val username = params["username"]?.trim()
            val password = params["password"]

            val result = when {
                username.isNullOrBlank() -> "empty_username"
                password.isNullOrBlank() -> "empty_password"
                else -> {
                    transaction {
                        val existingUser = Users.selectAll()
                            .where { Users.username eq username }
                            .count() > 0

                        if (existingUser) {
                            "username_exists"
                        } else {
                            Users.insert {
                                it[Users.username] = username
                                it[Users.password] = password
                                it[isStaff] = false
                            }
                            "success"
                        }
                    }
                }
            }

            call.respondHtml {
                head { 
                    title("Sign Up") 
                    script {
                        unsafe {
                            when (result) {
                                "empty_username" -> raw("alert('Username cannot be empty'); window.location.href = '/sign-up';")
                                "empty_password" -> raw("alert('Password cannot be empty'); window.location.href = '/sign-up';")
                                "username_exists" -> raw("alert('Username already exists'); window.location.href = '/sign-up';")
                                "success" -> raw("alert('Account created successfully!'); window.location.href = '/login';")
                            }
                        }
                    }
                }
                body { }
            }
        }

        get("/login") {
            call.respondHtml {
                head { 
                    title("Login")
                    link(rel="stylesheet", href="/static/css/logsignup.css")
                }
                body {
                    div(classes = "auth-container") {
                        h1 { +"Login" }
                        form(action = "/login", method = FormMethod.post, classes = "auth-form") {
                            div(classes = "form-group") {
                                label { 
                                    htmlFor = "username"
                                    +"Username"
                                }
                                input(type = InputType.text, name = "username") {
                                    id = "username"
                                    required = true
                                    placeholder = "Enter Username"
                                }
                            }
                            div(classes = "form-group") {
                                label { 
                                    htmlFor = "password"
                                    +"Password"
                                }
                                input(type = InputType.password, name = "password") {
                                    id = "password"
                                    required = true
                                    placeholder = "Enter Password"
                                }
                            }
                            submitInput(classes = "auth-submit") { value = "Login" }
                        }
                        div(classes = "auth-footer") {
                            a(href = "/sign-up") { +"Sign up" }
                        }
                    }
                }
            }
        }

        post("/login") {
            val params = call.receiveParameters()
            val username = params["username"]?.trim()
            val password = params["password"]

            val result = when {
                username.isNullOrBlank() || password.isNullOrBlank() -> "empty_fields"
                else -> {
                    transaction {
                        val user = Users.selectAll()
                            .where { (Users.username eq username) and (Users.password eq password) }
                            .singleOrNull()

                        if (user != null) {
                            call.sessions.set(UserSession(user[Users.userId], user[Users.username]))
                            "success"
                        } else {
                            "invalid_credentials"
                        }
                    }
                }
            }

            call.respondHtml {
                head { 
                    title("Login") 
                    script {
                        unsafe {
                            when (result) {
                                "empty_fields" -> raw("alert('Please enter username and password'); window.location.href = '/login';")
                                "invalid_credentials" -> raw("alert('Invalid username or password'); window.location.href = '/login';")
                                "success" -> raw("alert('Login successful!'); window.location.href = '/';")
                            }
                        }
                    }
                }
                body { }
            }
        }

        get("/logout") {
            call.sessions.clear<UserSession>()
            call.respondRedirect("/")
        }

        get("/home/{userId}") {
            val userId = call.parameters["userId"]?.toIntOrNull()
            val session = call.sessions.get<UserSession>()
            
            if (userId == null || session == null || session.userId != userId) {
                call.respondRedirect("/login")
                return@get
            }
            
            val checkedOutBooks = transaction {
                Checkouts.innerJoin(Books, { Checkouts.bookId }, { Books.bookId })
                    .selectAll()
                    .where { Checkouts.userId eq userId }
                    .map {
                        mapOf(
                            "bookId" to it[Books.bookId],
                            "title" to it[Books.title],
                            "author" to it[Books.author],
                            "dueDate" to it[Checkouts.dueDate].toString()
                        )
                    }
            }
            
            val reservedBooks = transaction {
                Reservations.innerJoin(Books, { Reservations.bookId }, { Books.bookId })
                    .leftJoin(Checkouts, { Reservations.bookId }, { Checkouts.bookId })
                    .selectAll()
                    .where { Reservations.userId eq userId }
                    .map {
                        val expiryDate = it[Reservations.expiryDate]
                        val availableFrom = it.getOrNull(Checkouts.dueDate)?.toString() ?: "Now"
                        
                        mapOf(
                            "bookId" to it[Books.bookId],
                            "title" to it[Books.title],
                            "author" to it[Books.author],
                            "availableFrom" to availableFrom,
                            "expiryDate" to expiryDate.toString()
                        )
                    }
            }
            
            call.respondHtml {
                head {
                    title("Home page")
                    link(rel="stylesheet", href="/static/css/home.css")
                }
                body {
                    div(classes = "home-container") {
                        div(classes = "home-header") {
                            h1 { +"Home page" }
                            div(classes = "home-nav") {
                                p { +"Welcome, ${session.username}!" }
                                a(href = "/") { +"Back to search" }
                                a(href = "/logout") { +"Log out" }
                            }
                        }
                        
                        div(classes = "book-section") {
                            h3 { +"Checked out books: ${checkedOutBooks.size}" }
                            if (checkedOutBooks.isEmpty()) {
                                p { +"No books checked out" }
                            } else {
                                ul {
                                    checkedOutBooks.forEach { book ->
                                        li {
                                            a(href = "/book/${book["bookId"]}") {
                                                +"${book["title"]} by ${book["author"]}"
                                            }
                                            +" - Due: ${book["dueDate"]}"
                                        }
                                    }
                                }
                            }
                        }
                        
                        div(classes = "book-section") {
                            h3 { +"Reserved books: ${reservedBooks.size}" }
                            if (reservedBooks.isEmpty()) {
                                p { +"No books reserved" }
                            } else {
                                ul {
                                    ul {
                                        reservedBooks.forEach { book ->
                                            li {
                                                a(href = "/book/${book["bookId"]}") {
                                                    +"${book["title"]} by ${book["author"]}"
                                                }
                                                +" - Available from: ${book["availableFrom"]} until ${book["expiryDate"]}"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}