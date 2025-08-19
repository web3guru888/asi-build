# \RealityManipulationAPI

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateReality**](RealityManipulationAPI.md#CreateReality) | **Post** /api/v1/reality/create | Create reality
[**ListRealities**](RealityManipulationAPI.md#ListRealities) | **Get** /api/v1/reality/list | List realities



## CreateReality

> Response CreateReality(ctx).RealityRequest(realityRequest).Execute()

Create reality



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
	realityRequest := *openapiclient.NewRealityRequest("QuantumReality_001") // RealityRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.RealityManipulationAPI.CreateReality(context.Background()).RealityRequest(realityRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RealityManipulationAPI.CreateReality``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateReality`: Response
	fmt.Fprintf(os.Stdout, "Response from `RealityManipulationAPI.CreateReality`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateRealityRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **realityRequest** | [**RealityRequest**](RealityRequest.md) |  | 

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


## ListRealities

> Response ListRealities(ctx).Execute()

List realities



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
	resp, r, err := apiClient.RealityManipulationAPI.ListRealities(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `RealityManipulationAPI.ListRealities``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListRealities`: Response
	fmt.Fprintf(os.Stdout, "Response from `RealityManipulationAPI.ListRealities`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiListRealitiesRequest struct via the builder pattern


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

