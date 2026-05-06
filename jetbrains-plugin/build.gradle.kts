plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "1.9.22"
    id("org.jetbrains.intellij") version "1.16.1"
}
group = "com.aitrustvalidator"
version = "0.4.0"
repositories { mavenCentral() }
intellij {
    version.set("2023.2")
    type.set("IC")
    plugins.set(listOf("com.intellij.java", "JavaScript"))
}
kotlin { jvmToolchain(17) }
tasks {
    patchPluginXml { sinceBuild.set("232"); untilBuild.set("241.*") }
}
dependencies { implementation("com.google.code.gson:gson:2.14.0") }
