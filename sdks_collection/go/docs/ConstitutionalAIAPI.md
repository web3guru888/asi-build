# \ConstitutionalAIAPI

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CheckAlignment**](ConstitutionalAIAPI.md#CheckAlignment) | **Post** /api/v1/constitution/check | Check alignment
[**GetConstitutionStatus**](ConstitutionalAIAPI.md#GetConstitutionStatus) | **Get** /api/v1/constitution/status | Get constitution status



## CheckAlignment

> Response CheckAlignment(ctx).CheckAlignmentRequest(checkAlignmentRequest).Execute()

Check alignment



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
	checkAlignmentRequest := *openapiclient.NewCheckAlignmentRequest("Increase consciousness level to 95%") // CheckAlignmentRequest | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ConstitutionalAIAPI.CheckAlignment(context.Background()).CheckAlignmentRequest(checkAlignmentRequest).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConstitutionalAIAPI.CheckAlignment``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CheckAlignment`: Response
	fmt.Fprintf(os.Stdout, "Response from `ConstitutionalAIAPI.CheckAlignment`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCheckAlignmentRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **checkAlignmentRequest** | [**CheckAlignmentRequest**](CheckAlignmentRequest.md) |  | 

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


## GetConstitutionStatus

> Response GetConstitutionStatus(ctx).Execute()

Get constitution status



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
	resp, r, err := apiClient.ConstitutionalAIAPI.GetConstitutionStatus(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ConstitutionalAIAPI.GetConstitutionStatus``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetConstitutionStatus`: Response
	fmt.Fprintf(os.Stdout, "Response from `ConstitutionalAIAPI.GetConstitutionStatus`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetConstitutionStatusRequest struct via the builder pattern


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

