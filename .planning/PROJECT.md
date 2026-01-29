# AuditEng V2

## What This Is

AuditEng V2 is an automated validation system for electrical commissioning reports in data centers. It analyzes PDF test reports (thermography, grounding, megger) and determines whether they should be APPROVED or REJECTED based on technical standards. External clients access the system via web app and API.

## Current Milestone: v1.0 Full System

**Goal:** Complete validation system with PDF extraction, all 3 test types, web + API authentication, and validation history dashboard.

**Target features:**
- PDF upload and LandingAI extraction
- Thermography, grounding, and megger validation with Claude analysis
- Web authentication (email/password) and API authentication (API keys)
- Validation history dashboard with evidence-based results

## Core Value

**Zero false rejections.** Every rejection must have clear evidence. Precision over speed — a false positive costs retrabalho, credibility, and operational costs. When in doubt, flag for human review instead of auto-rejecting.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] PDF upload and processing via LandingAI extraction
- [ ] Claude-powered analysis with commissioning engineer persona
- [ ] Thermography validation (calibration, delta phases, camera config, serial cross-validation)
- [ ] Grounding validation (calibration, resistance limits, method verification)
- [ ] Megger validation (calibration, test voltage, minimum resistance)
- [ ] User authentication (email/password for web)
- [ ] API authentication (API keys)
- [ ] Validation history dashboard
- [ ] Evidence-based results (page, field, found vs expected)
- [ ] Three result states: APPROVED, REJECTED, REVIEW NEEDED

### Out of Scope

- Real-time collaboration — single-user validation workflow sufficient for V1
- Mobile app — web responsive is enough
- Multi-language — Portuguese only for V1
- Batch processing UI — API can handle batches, but UI is single-file
- Report generation/export — results displayed in app, no PDF export

## Context

### Technical Environment
- LandingAI ADE handles PDF extraction with visual grounding
- Claude (Sonnet) acts as senior commissioning engineer applying technical rules
- Validation rules are codified from 15+ years of domain experience
- Three client date formats to handle: DD/MM/YYYY (FNEC/Brazil), MM/DD/YY (GENSEP), ISO

### Domain Knowledge (captured in context files)
- `ENGINEER_ROLE.md` — Persona and decision-making behavior
- `VALIDATION_RULES.md` — Technical rules by test type
- `REJECTION_EXAMPLES.md` — Few-shot learning examples
- `TECHNICAL_STANDARDS.md` — Applicable norms (ABNT, Microsoft, IEEE)
- `DATA_SCHEMAS.md` — Extracted and validated data structures

### Critical Validation Rules
1. **Calibration certificates**: Zero tolerance — expired = automatic rejection
2. **Camera config**: Temperature must match datalogger exactly (0.0°C tolerance)
3. **Serial cross-validation**: Must match across report header, photo, and certificate
4. **Phase delta**: >15°C = rejection, >3°C = requires Energy Marshal comment
5. **Date formats**: Client-specific — GENSEP uses American MM/DD/YY

### Known Patterns to Detect
- Copy-paste errors (serial in photo doesn't match declared)
- Expired certificates with confusing date formats
- Camera misconfiguration (ambient temp mismatch)
- Incomplete reports (missing mandatory fields)

## Constraints

- **Tech stack**: Python 3.11+, LandingAI ADE, Anthropic Claude, Pydantic, httpx — already decided
- **Timeline**: Weeks, not months — backlog of reports building
- **Accuracy requirement**: False rejections are worse than false approvals — when uncertain, flag for human review
- **Volume**: Hundreds of reports/month — system must be reliable at scale

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LandingAI for extraction | Visual grounding needed for PDF data with photos | — Pending |
| Claude as "engineer persona" | Technical reasoning, not just checklist | — Pending |
| Three result states | REVIEW NEEDED prevents both false positives and negatives | — Pending |
| Web + API delivery | Clients need both manual upload and integration options | — Pending |
| User accounts + API keys | Different auth for different access patterns | — Pending |

---
*Last updated: 2026-01-22 after milestone v1.0 started*
