# \AGICoreAPI

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetAgiStatus**](AGICoreAPI.md#GetAgiStatus) | **Get** /api/v1/agi/status | Get AGI status
[**InitializeAgi**](AGICoreAPI.md#InitializeAgi) | **Post** /api/v1/agi/initialize | Initialize AGI system
[**ProcessThought**](AGICoreAPI.md#ProcessThought) | **Post** /api/v1/agi/think | Process thought
[**ShutdownAgi**](AGICoreAPI.md#ShutdownAgi) | **Post** /api/v1/agi/shutdown | Shutdown AGI system



## GetAgiStatus

> Response GetAgiStatus(ctx).Execute()

Get AGI status



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AGICoreAPI.GetAgiStatus(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AGICoreAPI.GetAgiStatus``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetAgiStatus`: Response
	fmt.Fprintf(os.Stdout, "Response from `AGICoreAPI.GetAgiStatus`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetAgiStatusRequest struct via the builder pattern


### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## InitializeAgi

> Response InitializeAgi(ctx).AGIConfigRequest(aGIConfigRequest).Execute()

Initialize AGI system



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	aGIConfigRequest := *openapiclient.NewAGIConfigRequest() // AGIConfigRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AGICoreAPI.InitializeAgi(context.Background()).AGIConfigRequest(aGIConfigRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AGICoreAPI.InitializeAgi``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `InitializeAgi`: Response
	fmt.Fprintf(os.Stdout, "Response from `AGICoreAPI.InitializeAgi`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiInitializeAgiRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **aGIConfigRequest** | [**AGIConfigRequest**](AGIConfigRequest.md) |  | 

### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ProcessThought

> Response ProcessThought(ctx).ThinkRequest(thinkRequest).Execute()

Process thought



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	thinkRequest := *openapiclient.NewThinkRequest("Analyze the implications of consciousness transcendence") // ThinkRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AGICoreAPI.ProcessThought(context.Background()).ThinkRequest(thinkRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AGICoreAPI.ProcessThought``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ProcessThought`: Response
	fmt.Fprintf(os.Stdout, "Response from `AGICoreAPI.ProcessThought`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiProcessThoughtRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **thinkRequest** | [**ThinkRequest**](ThinkRequest.md) |  | 

### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ShutdownAgi

> Response ShutdownAgi(ctx).Execute()

Shutdown AGI system



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.AGICoreAPI.ShutdownAgi(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `AGICoreAPI.ShutdownAgi``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ShutdownAgi`: Response
	fmt.Fprintf(os.Stdout, "Response from `AGICoreAPI.ShutdownAgi`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiShutdownAgiRequest struct via the builder pattern


### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

