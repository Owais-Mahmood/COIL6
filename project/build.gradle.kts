plugins {
    kotlin("jvm") version "2.2.20"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.ktor:ktor-server-core:2.3.0")
    implementation("io.ktor:ktor-server-netty:2.3.0")
}

application {
    // Kotlin DSL uses ::class.java for main class reference
    mainClass.set("MainKt")
}