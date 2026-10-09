# RxVerify SRE Documentation

## Service Level Indicators (SLIs)

| SLI | Description | Measurement | Target |
|-----|-------------|-------------|--------|
| **Availability** | Health endpoint returns 200 OK | `up{job="rxverify"} == 1` | ≥ 99.9% |
| **Latency (p95)** | 95th percentile HTTP request duration | `histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))` | ≤ 500ms |
| **Error Rate** | Percentage of 5xx responses | `sum(rate(flask_http_request_total{status=~"5.."}[5m])) / sum(rate(flask_http_request_total[5m]))` | ≤ 1% |

## Service Level Objectives (SLOs)

| SLO | Target | Measurement Window | Alerting |
|-----|--------|-------------------|----------|
| **Availability** | 99.9% | 30-day rolling | Page if < 99.5% over 1h |
| **Latency (p95)** | < 500ms | 5-minute sliding | Alert if > 1s for 5m |
| **Error Rate** | < 1% | 5-minute sliding | Alert if > 5% for 5m |

## Service Level Agreement (SLA) — *Demonstration Only*

> **This is a classroom demonstration. No actual contractual SLA exists.**

| Metric | Commitment | Consequence |
|--------|------------|-------------|
| Monthly Uptime | 99.5% | Demo re-run with faculty |
| Incident Response | Acknowledge within 15 min | Postmortem required |
| Incident Resolution | Resolve within 4 hours | Blameless postmortem published |

## Error Budget Policy

- **Error Budget** = 100% - SLO target
- **Availability Budget**: 0.1% = 43.2 minutes downtime/month
- **Burn Rate Alerting**:
  - 1x budget/hr → Alert (investigate)
  - 6x budget/hr → Page (urgent)
  - 100x budget/hr → Page + auto-rollback if configured

## Runbook Links

- [Incident Response Runbook](./incident-runbook.md)
- [Postmortem Template](./postmortem-template.md)
- [Deployment Rollback Procedure](./rollback-procedure.md)