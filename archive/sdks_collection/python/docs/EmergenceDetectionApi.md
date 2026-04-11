# kenny_agi_sdk.EmergenceDetectionApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**detect_emergence**](EmergenceDetectionApi.md#detect_emergence) | **POST** /api/v1/emergence/detect | Detect emergence patterns


# **detect_emergence**
> Response detect_emergence(request_body)

Detect emergence patterns

Detect emergent patterns in provided data

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.response import Response
from kenny_agi_sdk.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost:8000
# See configuration.py for a list of all supported configuration parameters.
configuration = kenny_agi_sdk.Configuration(
    host = "http://localhost:8000"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): bearerAuth
configuration = kenny_agi_sdk.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
async with kenny_agi_sdk.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = kenny_agi_sdk.EmergenceDetectionApi(api_client)
    request_body = None # Dict[str, object] | 

    try:
        # Detect emergence patterns
        api_response = await api_instance.detect_emergence(request_body)
        print("The response of EmergenceDetectionApi->detect_emergence:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmergenceDetectionApi->detect_emergence: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **request_body** | [**Dict[str, object]**](object.md)|  | 

### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Emergence analysis complete |  -  |
**400** | Emergence detection module not available |  -  |
**500** | Detection failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

