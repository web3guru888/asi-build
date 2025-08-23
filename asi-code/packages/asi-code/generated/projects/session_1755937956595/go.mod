module mlops-platform

go 1.21

require (
	github.com/gorilla/mux v1.8.1
	github.com/prometheus/client_golang v1.16.0
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.43.0
	go.opentelemetry.io/otel v1.19.0
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp v1.19.0
	go.opentelemetry.io/otel/sdk v1.19.0
	golang.org/x/time v0.3.0
)

require (
	github.com/golang-jwt/jwt/v4 v4.5.0
	github.com/prometheus/common v0.46.0
	go.opentelemetry.io/otel/trace v1.19.0
)

replace mlops-platform => ./