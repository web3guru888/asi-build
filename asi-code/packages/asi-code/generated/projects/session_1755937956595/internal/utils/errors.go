package utils

import (
	"errors"
	"fmt"
	"net/http"
)

// APIError represents a structured error for API responses
type APIError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Detail  string `json:"detail,omitempty"`
}

// Error returns the string representation of the APIError
func (e *APIError) Error() string {
	if e.Detail != "" {
		return fmt.Sprintf("error %d: %s (%s)", e.Code, e.Message, e.Detail)
	}
	return fmt.Sprintf("error %d: %s", e.Code, e.Message)
}

// NewAPIError creates a new APIError with code and message
func NewAPIError(code int, message string) *APIError {
	return &APIError{
		Code:    code,
		Message: message,
	}
}

// NewAPIErrorWithDetail creates a new APIError with code, message, and detailed context
func NewAPIErrorWithDetail(code int, message, detail string) *APIError {
	return &APIError{
		Code:    code,
		Message: message,
		Detail:  detail,
	}
}

// BadRequestError returns an APIError for 400 Bad Request
func BadRequestError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusBadRequest, "bad request", detail)
}

// UnauthorizedError returns an APIError for 401 Unauthorized
func UnauthorizedError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusUnauthorized, "unauthorized", detail)
}

// ForbiddenError returns an APIError for 403 Forbidden
func ForbiddenError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusForbidden, "forbidden", detail)
}

// NotFoundError returns an APIError for 404 Not Found
func NotFoundError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusNotFound, "resource not found", detail)
}

// ConflictError returns an APIError for 409 Conflict
func ConflictError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusConflict, "conflict", detail)
}

// ValidationError returns an APIError for 422 Unprocessable Entity
func ValidationError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusUnprocessableEntity, "validation failed", detail)
}

// InternalServerError returns an APIError for 500 Internal Server Error
func InternalServerError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusInternalServerError, "internal server error", detail)
}

// ServiceUnavailableError returns an APIError for 503 Service Unavailable
func ServiceUnavailableError(detail string) *APIError {
	return NewAPIErrorWithDetail(http.StatusServiceUnavailable, "service unavailable", detail)
}

// IsAPIError checks if an error is of type *APIError
func IsAPIError(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr)
}

// WrapAPIError converts a standard error into an InternalServerError with the original message
func WrapAPIError(err error) *APIError {
	if apiErr, ok := err.(*APIError); ok {
		return apiErr
	}
	return InternalServerError(err.Error())
}

// HandleError writes the appropriate HTTP response based on the error type
func HandleError(w http.ResponseWriter, err error) {
	apiErr, ok := err.(*APIError)
	if !ok {
		apiErr = InternalServerError(err.Error())
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(apiErr.Code)
	//nolint:errcheck
	fmt.Fprintf(w, `{"code":%d,"message":"%s"`, apiErr.Code, apiErr.Message)
	if apiErr.Detail != "" {
		//nolint:errcheck
		fmt.Fprintf(w, `,"detail":"%s"`, apiErr.Detail)
	}
	//nolint:errcheck
	fmt.Fprint(w, "}")
}