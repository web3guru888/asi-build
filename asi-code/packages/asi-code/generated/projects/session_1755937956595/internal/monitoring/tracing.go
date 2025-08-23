package monitoring

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

// TracingConfig holds configuration for OpenTelemetry tracing
type TracingConfig struct {
	Endpoint string `mapstructure:"endpoint"`
	Timeout  int    `mapstructure:"timeout"` // in seconds
	Headers  map[string]string
}

// Tracing is an interface for OpenTelemetry tracing operations
type Tracing interface {
	Shutdown(ctx context.Context) error
	HTTPMiddleware(next http.Handler) http.Handler
}

// tracingImpl implements the Tracing interface
type tracingImpl struct {
	tracerProvider *sdktrace.TracerProvider
}

// NewTracing initializes OpenTelemetry tracing with the given config
func NewTracing(cfg TracingConfig, serviceName string) (Tracing, error) {
	// Create OTLP HTTP exporter
	exporter, err := otlptracehttp.New(
		context.Background(),
		otlptracehttp.WithEndpoint(cfg.Endpoint),
		otlptracehttp.WithTimeout(time.Duration(cfg.Timeout)*time.Second),
		otlptracehttp.WithHeaders(cfg.Headers),
		otlptracehttp.WithCompression(otlptracehttp.GzipCompression),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create OTLP trace exporter: %w", err)
	}

	// Create resource with service info
	res, err := resource.Merge(
		resource.Default(),
		resource.NewSchemaless(
			semconv.ServiceNameKey.String(serviceName),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Create trace provider
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	// Set global trace provider and propagator
	otel.SetTracerProvider(tracerProvider)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return &tracingImpl{tracerProvider: tracerProvider}, nil
}

// Shutdown gracefully shuts down the tracer provider
func (t *tracingImpl) Shutdown(ctx context.Context) error {
	if t.tracerProvider != nil {
		return t.tracerProvider.Shutdown(ctx)
	}
	return nil
}

// HTTPMiddleware returns an HTTP middleware that traces incoming requests
func (t *tracingImpl) HTTPMiddleware(next http.Handler) http.Handler {
	return otelhttp.NewHandler(next, "")
}

// TraceClient wraps HTTP client with OpenTelemetry tracing instrumentation
func TraceClient(client *http.Client) *http.Client {
	if client == nil {
		client = &http.Client{}
	}

	// Wrap transport with OpenTelemetry instrumentation
	client.Transport = otelhttp.NewTransport(
		client.Transport,
		otelhttp.WithSpanNameFormatter(func(_ string, r *http.Request) string {
			return fmt.Sprintf("%s %s", r.Method, r.URL.Path)
		}),
		otelhttp.WithFilter(func(r *http.Request) bool {
			// Exclude health check and metrics endpoints from tracing
			return !strings.HasPrefix(r.URL.Path, "/health") &&
				!strings.HasPrefix(r.URL.Path, "/metrics")
		}),
	)

	return client
}

// StartSpan starts a new span with the given name and returns a context with the span and the span itself
func StartSpan(ctx context.Context, name string) (context.Context, sdktrace.Span) {
	return otel.Tracer("mlops-platform").Start(ctx, name)
}

// InjectTraceHeaders injects trace context into HTTP headers
func InjectTraceHeaders(ctx context.Context, headers http.Header) {
	otel.GetTextMapPropagator().Inject(ctx, propagation.HeaderCarrier(headers))
}

// ExtractTraceContext extracts trace context from HTTP headers
func ExtractTraceContext(ctx context.Context, headers http.Header) context.Context {
	return otel.GetTextMapPropagator().Extract(ctx, propagation.HeaderCarrier(headers))
}