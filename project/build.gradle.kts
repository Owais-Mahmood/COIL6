plugins {
    kotlin("jvm") version "2.2.20"
    application
}

kotlin {
    jvmToolchain(24) // match your Java version
}

repositories {
    mavenCentral()
}



dependencies {
    implementation("io.ktor:ktor-server-core:3.4.1")
    implementation("io.ktor:ktor-server-netty:3.4.1")
}

application {
    // Kotlin DSL uses ::class.java for main class reference
    mainClass.set("MainKt")
}