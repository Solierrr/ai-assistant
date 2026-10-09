

## Telemetria (OpenTelemetry)

O serviço envia traces, métricas e logs por OTLP pelo wrapper `opentelemetry-instrument` (auto-instrumentação de FastAPI e `logging`), sem código na aplicação. Ele só é usado quando `OTEL_SDK_DISABLED=false`; sem isso o serviço sobe como antes. Para ver a telemetria localmente, use o Grafana local pelo `make up OBS=1` (ver `docs-warehouse/helps/TRY-LOCAL.md`).

```text
OTEL_SDK_DISABLED=false
OTEL_SERVICE_NAME=ai-assistant
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_RESOURCE_ATTRIBUTES=service.namespace=solaria,deployment.environment=local
OTEL_PYTHON_LOG_CORRELATION=true
```
