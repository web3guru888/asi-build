# kenny_agi_sdk.ConsciousnessApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**elevate_consciousness**](ConsciousnessApi.md#elevate_consciousness) | **POST** /api/v1/consciousness/elevate | Elevate consciousness
[**get_consciousness_level**](ConsciousnessApi.md#get_consciousness_level) | **GET** /api/v1/consciousness/level | Get consciousness level


# **elevate_consciousness**
> Response elevate_consciousness(consciousness_request)

Elevate consciousness

Elevate consciousness to target level with safety checks

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.consciousness_request import ConsciousnessRequest
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
    api_instance = kenny_agi_sdk.ConsciousnessApi(api_client)
    consciousness_request = kenny_agi_sdk.ConsciousnessRequest() # ConsciousnessRequest | 

    try:
        # Elevate consciousness
        api_response = await api_instance.elevate_consciousness(consciousness_request)
        print("The response of ConsciousnessApi->elevate_consciousness:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ConsciousnessApi->elevate_consciousness: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **consciousness_request** | [**ConsciousnessRequest**](ConsciousnessRequest.md)|  | 

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
**200** | Consciousness elevated successfully |  -  |
**400** | Invalid consciousness level or module not available |  -  |
**500** | Elevation failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_consciousness_level**
> Response get_consciousness_level()

Get consciousness level

Get current consciousness level and status

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
    api_instance = kenny_agi_sdk.ConsciousnessApi(api_client)

    try:
        # Get consciousness level
        api_response = await api_instance.get_consciousness_level()
        print("The response of ConsciousnessApi->get_consciousness_level:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ConsciousnessApi->get_consciousness_level: %s\n" % e)
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
**200** | Consciousness level retrieved |  -  |
**400** | Divine Mathematics module not available |  -  |
**500** | Retrieval failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

