plugins {
    alias(libs.plugins.kotlin.jvm)
    id("org.jetbrains.kotlin.plugin.serialization") version "2.2.20"
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.ktor:ktor-server-core-jvm:3.4.1")
    implementation("io.ktor:ktor-server-netty-jvm:3.4.1")
    implementation("io.ktor:ktor-server-content-negotiation-jvm:3.4.1")
    implementation("io.ktor:ktor-serialization-kotlinx-json-jvm:3.4.1")
    implementation("io.ktor:ktor-server-sessions-jvm:3.4.1")
    implementation("io.ktor:ktor-server-html-builder-jvm:3.4.1")

    testImplementation("org.jetbrains.kotlin:kotlin-test")
    testImplementation(libs.junit.jupiter.engine)
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions.jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_24)
}

tasks.withType<JavaCompile>().configureEach {
    sourceCompatibility = "24"
    targetCompatibility = "24"
}

application {
    mainClass = "backend.MainKt"
}

tasks.named<Test>("test") {
    useJUnitPlatform()
}
