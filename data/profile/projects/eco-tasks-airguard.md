# EcoTasks-AirGuard-NASA

Blazor WebAssembly + ASP.NET Core 8 application delivering near real-time North American air quality (AirNow API) combined with contextual weather (OpenWeather API) and TEMPO coverage concepts.

## Features
Live AQI + pollutant metrics with category coloring, 12-hour PM2.5 forecast chart, city selection with bulk snapshot loading, alerts page with filtering, onboarding/home page with AQI guide and system status latency probe, PDF report generation scaffold (QuestPDF), resilient data loading (timeout + exponential retry), health checks, clean Client/Server/Shared project segmentation with shared DTOs.

## Security & hardening
Secrets via environment variables (not in source), API-key health check, non-root containers, HSTS/HTTPS enforced in non-development, CORS/base-URL hygiene, fail-fast on missing keys, environment segregation.

## Evidence level
Tier 2 — supporting evidence for external API integration, data aggregation, resilience patterns, and security-focused containerization.

GitHub: github.com/AmjadRenno/EcoTasks-AirGuard-NASA
