# kenny_agi_sdk.RealityManipulationApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_reality**](RealityManipulationApi.md#create_reality) | **POST** /api/v1/reality/create | Create reality
[**list_realities**](RealityManipulationApi.md#list_realities) | **GET** /api/v1/reality/list | List realities


# **create_reality**
> Response create_reality(reality_request)

Create reality

Create a new mathematical reality with specified parameters

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.reality_request import RealityRequest
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
    api_instance = kenny_agi_sdk.RealityManipulationApi(api_client)
    reality_request = kenny_agi_sdk.RealityRequest() # RealityRequest | 

    try:
        # Create reality
        api_response = await api_instance.create_reality(reality_request)
        print("The response of RealityManipulationApi->create_reality:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RealityManipulationApi->create_reality: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **reality_request** | [**RealityRequest**](RealityRequest.md)|  | 

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
**200** | Reality created successfully |  -  |
**400** | Invalid parameters or module not available |  -  |
**500** | Reality creation failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_realities**
> Response list_realities()

List realities

List all created mathematical realities

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
    api_instance = kenny_agi_sdk.RealityManipulationApi(api_client)

    try:
        # List realities
        api_response = await api_instance.list_realities()
        print("The response of RealityManipulationApi->list_realities:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling RealityManipulationApi->list_realities: %s\n" % e)
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
**200** | Realities retrieved successfully |  -  |
**400** | Divine Mathematics module not available |  -  |
**500** | Retrieval failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

