<!-- Sync Impact Report
Version change: 0.0.0 (template) → 1.0.0 (initial ratification)
Added sections: Core Principles (5), Security & Compliance, Development Workflow, Governance
Templates requiring updates: ✅ constitution.md written
Follow-up TODOs: None
-->

# Online Judge (Google Classroom Integration) Constitution

## Core Principles

### I. Correctness & Fairness (NON-NEGOTIABLE)
The judge MUST produce deterministic, reproducible verdicts. Identical code submitted twice MUST yield identical results under the same constraints. Time/memory limits MUST be enforced uniformly across all submissions regardless of user role. Grading logic MUST be covered by automated tests before deployment.

### II. Security Isolation
Every submitted code execution MUST run in an isolated sandbox (container or seccomp-restricted process). No submission may access the host filesystem, network, or other user data. Sandbox escape constitutes a critical incident and triggers immediate rollback. Dependency on external execution services MUST document their isolation guarantees.

### III. Google Classroom Integration Fidelity
All assignment creation, roster sync, and grade passback operations MUST use the official Google Classroom API. OAuth 2.0 with minimal required scopes is mandatory — never store raw Google credentials. Grade passback MUST be idempotent: posting the same score twice MUST NOT duplicate entries in Google Classroom.

### IV. Test-First Development
TDD is mandatory: tests written and approved → tests fail (red) → implementation (green) → refactor. No feature is considered done without passing tests. Integration tests MUST cover the full submission-to-verdict pipeline and the Classroom grade passback flow.

### V. Simplicity & Incremental Delivery
Start with the simplest solution that satisfies requirements. YAGNI — no speculative features. Each deliverable MUST be a working vertical slice (submit code → get verdict → post grade). Complexity beyond that requires explicit justification in the spec.

## Security & Compliance

- All user data (submissions, scores) MUST be stored encrypted at rest.
- Google OAuth tokens MUST be stored server-side only; never exposed to the client.
- Submission content is untrusted input — sanitize before logging or displaying.
- Audit logs for all grade modifications MUST be retained for 90 days minimum.
- GDPR/FERPA awareness: student submission data MUST be deletable on request.

## Development Workflow

- Feature branches from `main`; PRs require passing CI (lint + tests) before merge.
- Spec-driven: constitution → spec → plan → tasks → implement (spec-kit workflow).
- Every task branch follows the naming convention: `feature/<task-id>-<short-description>`.
- Docker Compose MUST reproduce the full local environment (judge, API, DB, sandbox).
- Environment variables via `.env` file; `.env.example` committed, `.env` gitignored.

## Governance

This constitution supersedes all other development practices and conventions.
Amendments require: (1) updated spec reflecting the change, (2) team review,
(3) version bump per semantic rules below, (4) migration plan if breaking.

All PRs/reviews MUST verify compliance with Security Isolation and Correctness principles.
Any deviation from sandbox isolation rules requires a security review before merge.

Versioning policy:
- MAJOR: Backward-incompatible changes to grading logic, API contracts, or sandbox model.
- MINOR: New principle added or material expansion of existing guidance.
- PATCH: Clarifications, wording fixes, non-semantic refinements.

**Version**: 1.0.0 | **Ratified**: 2026-05-11 | **Last Amended**: 2026-05-11
