# \ConsciousnessAPI

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**ElevateConsciousness**](ConsciousnessAPI.md#ElevateConsciousness) | **Post** /api/v1/consciousness/elevate | Elevate consciousness
[**GetConsciousnessLevel**](ConsciousnessAPI.md#GetConsciousnessLevel) | **Get** /api/v1/consciousness/level | Get consciousness level



## ElevateConsciousness

> Response ElevateConsciousness(ctx).ConsciousnessRequest(consciousnessRequest).Execute()

Elevate consciousness



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
	consciousnessRequest := *openapiclient.NewConsciousnessRequest() // ConsciousnessRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConsciousnessAPI.ElevateConsciousness(context.Background()).ConsciousnessRequest(consciousnessRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConsciousnessAPI.ElevateConsciousness``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ElevateConsciousness`: Response
	fmt.Fprintf(os.Stdout, "Response from `ConsciousnessAPI.ElevateConsciousness`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiElevateConsciousnessRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **consciousnessRequest** | [**ConsciousnessRequest**](ConsciousnessRequest.md) |  | 

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


## GetConsciousnessLevel

> Response GetConsciousnessLevel(ctx).Execute()

Get consciousness level



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
	resp, r, err := apiClient.ConsciousnessAPI.GetConsciousnessLevel(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConsciousnessAPI.GetConsciousnessLevel``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConsciousnessLevel`: Response
	fmt.Fprintf(os.Stdout, "Response from `ConsciousnessAPI.GetConsciousnessLevel`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetConsciousnessLevelRequest struct via the builder pattern


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

