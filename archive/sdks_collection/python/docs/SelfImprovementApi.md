# kenny_agi_sdk.SelfImprovementApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_improvement_metrics**](SelfImprovementApi.md#get_improvement_metrics) | **GET** /api/v1/improvement/metrics | Get improvement metrics


# **get_improvement_metrics**
> Response get_improvement_metrics()

Get improvement metrics

Get self-improvement performance metrics

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
    api_instance = kenny_agi_sdk.SelfImprovementApi(api_client)

    try:
        # Get improvement metrics
        api_response = await api_instance.get_improvement_metrics()
        print("The response of SelfImprovementApi->get_improvement_metrics:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SelfImprovementApi->get_improvement_metrics: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**Response**](Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Improvement metrics retrieved |  -  |
**400** | Self-improvement module not available |  -  |
**500** | Retrieval failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

