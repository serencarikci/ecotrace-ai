# Observability

- Structured JSON logs via structlog (requestId, organizationId, durations)
- In-process Prometheus-compatible metrics (`GET /api/v1/system/metrics`, system admin)
- Request middleware timings
- Job / agent / scheduler trace IDs stored on execution records
- Health: `/health`, `/ready`, `/api/v1/system/health*`

OpenTelemetry SDK wiring can be attached at the reverse-proxy / sidecar layer; application exposes IDs and metrics without proprietary SaaS dependency.
