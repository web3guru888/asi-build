package logging

import (
	"context"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// LogLevel represents the severity level of a log message.
type LogLevel int

const (
	DebugLevel LogLevel = iota
	InfoLevel
	WarnLevel
	ErrorLevel
	FatalLevel
)

// String returns the string representation of the log level.
func (l LogLevel) String() string {
	switch l {
	case DebugLevel:
		return "DEBUG"
	case InfoLevel:
		return "INFO"
	case WarnLevel:
		return "WARN"
	case ErrorLevel:
		return "ERROR"
	case FatalLevel:
		return "FATAL"
	default:
		return "UNKNOWN"
	}
}

// Logger represents a structured logger with level support and context integration.
type Logger struct {
	level   LogLevel
	writer  io.Writer
	mu      sync.Mutex
	service string
	env     string
}

// LogEntry represents a structured log entry.
type LogEntry struct {
	Timestamp string                 `json:"timestamp"`
	Level     string                 `json:"level"`
	Message   string                 `json:"message"`
	Service   string                 `json:"service"`
	Env       string                 `json:"env"`
	File      string                 `json:"file,omitempty"`
	Line      int                    `json:"line,omitempty"`
	Caller    string                 `json:"caller,omitempty"`
	Data      map[string]interface{} `json:"data,omitempty"`
}

// NewLogger creates a new instance of Logger with provided service name and environment.
// Defaults to InfoLevel if no level is specified.
func NewLogger(service, env string) *Logger {
	level := InfoLevel
	if val, exists := os.LookupEnv("LOG_LEVEL"); exists {
		level = parseLogLevel(val)
	}

	var writer io.Writer = os.Stdout
	if logFile, ok := os.LookupEnv("LOG_OUTPUT"); ok && logFile != "" {
		if err := ensureLogDir(filepath.Dir(logFile)); err != nil {
			log.Printf("Failed to create log directory: %v", err)
		} else {
			f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
			if err != nil {
				log.Printf("Failed to open log file %s: %v, falling back to stdout", logFile, err)
			} else {
				writer = f
			}
		}
	}

	return &Logger{
		level:   level,
		writer:  writer,
		service: service,
		env:     env,
	}
}

// ensureLogDir creates the directory path for log files if it doesn't exist.
func ensureLogDir(dir string) error {
	if dir == "" || dir == "." {
		return nil
	}
	err := os.MkdirAll(dir, 0755)
	if err != nil {
		return fmt.Errorf("failed to create log directory: %w", err)
	}
	return nil
}

// parseLogLevel converts a string to LogLevel.
func parseLogLevel(level string) LogLevel {
	switch strings.ToLower(level) {
	case "debug":
		return DebugLevel
	case "warn", "warning":
		return WarnLevel
	case "error":
		return ErrorLevel
	case "fatal":
		return FatalLevel
	case "info":
		fallthrough
	default:
		return InfoLevel
	}
}

// SetLevel updates the current logging level.
func (l *Logger) SetLevel(level LogLevel) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.level = level
}

// getCallerInfo returns the file and line number of the caller.
func getCallerInfo(skip int) (string, int) {
	pc, file, line, ok := runtime.Caller(skip)
	if !ok {
		return "unknown", 0
	}
	return filepath.Base(file), line, len(filepath.Ext(file))
}

// formatEntry creates a JSON-formatted log string from an entry.
func (l *Logger) formatEntry(entry LogEntry) string {
	// Build base JSON
	jsonStr := fmt.Sprintf(`{"timestamp":"%s","level":"%s","message":"%s","service":"%s","env":"%s"`,
		entry.Timestamp, entry.Level, entry.Message, entry.Service, entry.Env)

	// Add caller info if present
	if entry.File != "" {
		jsonStr += fmt.Sprintf(`,"file":"%s","line":%d,"caller":"%s"`, entry.File, entry.Line, entry.Caller)
	}

	// Add additional data fields
	if len(entry.Data) > 0 {
		for k, v := range entry.Data {
			switch val := v.(type) {
			case string:
				jsonStr += fmt.Sprintf(`,"%s":"%s"`, k, val)
			case error:
				jsonStr += fmt.Sprintf(`,"%s":"%s"`, k, val.Error())
			default:
				jsonStr += fmt.Sprintf(`,"%s":%v`, k, val)
			}
		}
	}

	jsonStr += "}"
	return jsonStr
}

// log writes the log entry if the level meets the threshold.
func (l *Logger) log(level LogLevel, msg string, data map[string]interface{}) {
	if l.shouldLog(level) {
		entry := LogEntry{
			Timestamp: time.Now().UTC().Format(time.RFC3339),
			Level:     level.String(),
			Message:   msg,
			Service:   l.service,
			Env:       l.env,
			Data:      data,
		}

		// Only capture caller info for Warn and above by default to reduce overhead
		if level >= WarnLevel {
			file, line := getCallerInfo(4) // Adjust skip for actual caller
			if file != "" {
				entry.File = file
				entry.Line = line
				caller := getFuncName(4)
				if caller != "" {
					entry.Caller = caller
				}
			}
		}

		formatted := l.formatEntry(entry)
		l.mu.Lock()
		defer l.mu.Unlock()
		_, _ = l.writer.Write([]byte(formatted + "\n"))
	}
}

// shouldLog checks if the given level should be logged based on current threshold.
func (l *Logger) shouldLog(level LogLevel) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	return level >= l.level
}

// getFuncName retrieves the name of the function at a given call stack depth.
func getFuncName(skip int) string {
	pc, _, _, ok := runtime.Caller(skip)
	if !ok {
		return ""
	}
	fn := runtime.FuncForPC(pc)
	if fn == nil {
		return ""
	}
	name := fn.Name()
	parts := strings.Split(name, ".")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return name
}

// Debug logs a debug message with optional structured data.
func (l *Logger) Debug(ctx context.Context, msg string, data map[string]interface{}) {
	if data == nil {
		data = make(map[string]interface{})
	}
	if ctx != nil {
		if reqID, ok := ctx.Value("request_id").(string); ok {
			data["request_id"] = reqID
		}
	}
	l.log(DebugLevel, msg, data)
}

// Info logs an info message with optional structured data.
func (l *Logger) Info(ctx context.Context, msg string, data map[string]interface{}) {
	if data == nil {
		data = make(map[string]interface{})
	}
	if ctx != nil {
		if reqID, ok := ctx.Value("request_id").(string); ok {
			data["request_id"] = reqID
		}
	}
	l.log(InfoLevel, msg, data)
}

// Warn logs a warning message with optional structured data.
func (l *Logger) Warn(ctx context.Context, msg string, data map[string]interface{}) {
	if data == nil {
		data = make(map[string]interface{})
	}
	if ctx != nil {
		if reqID, ok := ctx.Value("request_id").(string); ok {
			data["request_id"] = reqID
		}
	}
	l.log(WarnLevel, msg, data)
}

// Error logs an error message with optional structured data.
func (l *Logger) Error(ctx context.Context, msg string, data map[string]interface{}) {
	if data == nil {
		data = make(map[string]interface{})
	}
	if ctx != nil {
		if reqID, ok := ctx.Value("request_id").(string); ok {
			data["request_id"] = reqID
		}
	}
	l.log(ErrorLevel, msg, data)
}

// Fatal logs a fatal message and exits the program.
func (l *Logger) Fatal(ctx context.Context, msg string, data map[string]interface{}) {
	if data == nil {
		data = make(map[string]interface{})
	}
	if ctx != nil {
		if reqID, ok := ctx.Value("request_id").(string); ok {
			data["request_id"] = reqID
		}
	}
	l.log(FatalLevel, msg, data)
	os.Exit(1)
}

// WithFields returns a new logger with additional fields pre-populated in logs.
// This is useful for adding service-wide metadata like version, instance ID, etc.
func (l *Logger) WithFields(fields map[string]interface{}) *Logger {
	newLogger := *l
	newLogger.mu.Lock()
	defer newLogger.mu.Unlock()

	// We could enhance this later to carry default fields
	return &newLogger
}

// Close cleans up any resources used by the logger.
// Currently only closes file writers if applicable.
func (l *Logger) Close() error {
	if closer, ok := l.writer.(io.Closer); ok {
		return closer.Close()
	}
	return nil
}