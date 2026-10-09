# Blameless Postmortem Template

## Incident: [TITLE - e.g., "RxVerify Health Endpoint Returning 500 for 15 Minutes"]

**Date:** YYYY-MM-DD
**Duration:** XX minutes/hours
**Severity:** SEV-1 / SEV-2 / SEV-3
**Status:** Resolved / Investigating / Mitigated
**Author:** [Name]
**Reviewers:** [Names]

---

## Executive Summary

**What happened:** [2-3 sentences describing the user-facing impact]

**Root Cause:** [One sentence identifying the technical root cause]

**Resolution:** [One sentence describing how service was restored]

**Impact:** [Quantified: % of requests failed, # users affected, duration]

---

## Timeline (UTC)

| Time | Event | Notes |
|------|-------|-------|
| HH:MM | Detection | How was it detected? (Alert, user report, etc.) |
| HH:MM | Triage | Initial assessment |
| HH:MM | Investigation | Key findings |
| HH:MM | Mitigation | Action taken to reduce impact |
| HH:MM | Resolution | Service fully restored |
| HH:MM | Post-incident | Follow-up tasks created |

---

## Root Cause Analysis

### What happened technically?
[Detailed technical explanation]

### Why did it happen? (5 Whys)
1. **Why?** [Answer]
2. **Why?** [Answer]
3. **Why?** [Answer]
4. **Why?** [Answer]
5. **Why?** [Answer] ← Root cause usually found here

### Contributing Factors
- [Factor 1]
- [Factor 2]
- [Factor 3]

---

## What Went Well
- [Positive observation 1]
- [Positive observation 2]

## What Could Be Improved
- [Improvement 1]
- [Improvement 2]

---

## Action Items (Preventive)

| # | Action | Owner | Due Date | Ticket/Link |
|---|--------|-------|----------|-------------|
| 1 | [Specific, actionable item] | [Name] | YYYY-MM-DD | [Link] |
| 2 | [Specific, actionable item] | [Name] | YYYY-MM-DD | [Link] |
| 3 | [Specific, actionable item] | [Name] | YYYY-MM-DD | [Link] |

---

## Supporting Evidence
- **Grafana Dashboard:** [Link to dashboard snapshot]
- **Prometheus Alerts:** [Alert names/links]
- **Logs:** [Loki query or log snippets]
- **Deployment History:** [Git commit / ArgoCD / kubectl history]
- **Chat/Comms:** [Slack thread / incident channel link]

---

## Appendix
- Related incidents: [Links]
- Architecture diagram: [Link]
- Runbook followed: [Link]