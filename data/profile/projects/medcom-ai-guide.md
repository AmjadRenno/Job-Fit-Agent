# MedCom.AIGuide — Final Datamatiker Project (Capstone)

## Overview
Web-based decision-support tool developed as an academic final project in a MedCom context. Helps knowledge workers evaluate whether a specific work situation is suitable for AI use, which tool category may be appropriate, what sharing restrictions apply, and what precautions should be taken.

The decision engine is intentionally **deterministic, not generative** — every assessment is explainable and consistent.

## Architecture
Clean Architecture-inspired modular monolith: Domain / Application / Infrastructure (EF Core, SQLite) / WebApi / React frontend (React 19 + TypeScript + Vite) / test projects (domain, application, WebApi integration).

## Technology stack
ASP.NET Core / .NET, C#, React 19, TypeScript, Vite, Tailwind CSS, Entity Framework Core, SQLite, Docker Compose, GitHub Actions, ASP.NET Core Identity, cookie authentication.

## Main functionality
- Guided evaluation wizard (task type, material type, AI access form)
- Deterministic decision engine — 23 decision rules covering sharing, suitability, risk, tool recommendation
- Explicit stop behaviour for high-risk cases (e.g. personal data, medical records) — halts with no tool recommended
- AI tool catalog with privacy notes, use cases, tiers
- Admin area: evaluation history, statistics, guidance posts, read-only decision-rule catalog
- Login rate limiting: 5 requests/minute per IP on admin login
- Generates a printable "Erklæring om AI-anvendelse" (AI-use declaration)

## Security
Admin authentication and authorization, login rate limiting, protected admin endpoints, secure cookie configuration, manual security testing with Burp Suite, environment-based configuration, secret hygiene.

## Testing and quality
186/186 tests passed (domain, application, WebApi integration tests). CI implemented with GitHub Actions.

## Evidence level
Tier 1 — strongest single piece of professional evidence: .NET, architecture, security, testing, CI/CD, React, decision-system design, governance-oriented thinking.

GitHub: github.com/AmjadRenno/MedCom-AIGuide
