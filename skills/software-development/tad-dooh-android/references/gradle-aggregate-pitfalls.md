# gradle-aggregate-pitfalls.md

## settings.gradle.kts

Use `dependencyResolutionManagement`, not `dependencyResolution`:

  dependencyResolutionManagement {
    repositoriesMode.set(FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
  }

The old block does not exist in Gradle 8.x and breaks sync before any dependency is resolved.

## build.gradle.kts plugins

Hilt plugin must be declared in BOTH root `build.gradle.kts` (apply false) and app module `build.gradle.kts` (apply true):

  // root
  id("com.google.dagger.hilt.android") version "2.52" apply false

  // app/build.gradle.kts
  plugins { id("com.google.dagger.hilt.android"); ... }

Forgetting the root alias causes "Plugin with id 'com.google.dagger.hilt.android' not found."

## app/build.gradle.kts deps

  implementation("com.google.dagger:hilt-android:2.52")
  ksp("com.google.dagger:hilt-compiler:2.52")
  implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
  implementation("androidx.hilt:hilt-work:1.2.0")
  ksp("androidx.hilt:hilt-compiler:1.2.0")

There are two distinct `hilt-compiler` artifacts:
- `com.google.dagger:hilt-compiler` — for `@Inject`, `@Module`, `@InstallIn`
- `androidx.hilt:hilt-compiler` — for `@HiltWorker`, `@AssistedInject`

## Room schema

`ksp { arg("room.schemaLocation", "$projectDir/schemas") }` must remain in `defaultConfig` inside `android {}`.

## compileSdk = 35, minSdk = 24, Java 17

- compileSdk = 35 needed for `foregroundServiceType="location"` + `lockTaskMode="always"`
- Java 17 target matches `compileOptions { sourceCompatibility = JavaVersion.VERSION_17 }`
