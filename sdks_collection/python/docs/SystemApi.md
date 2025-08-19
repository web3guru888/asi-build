# kenny_agi_sdk.SystemApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_api_info**](SystemApi.md#get_api_info) | **GET** / | Get API information
[**health_check**](SystemApi.md#health_check) | **GET** /health | Health check


# **get_api_info**
> GetApiInfo200Response get_api_info()

Get API information

Returns basic API information and available endpoints

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.get_api_info200_response import GetApiInfo200Response
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
    api_instance = kenny_agi_sdk.SystemApi(api_client)

    try:
        # Get API information
        api_response = await api_instance.get_api_info()
        print("The response of SystemApi->get_api_info:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SystemApi->get_api_info: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**GetApiInfo200Response**](GetApiInfo200Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | API information |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **health_check**
> HealthCheck200Response health_check()

Health check

Check the health status of the API and AGI system

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.health_check200_response import HealthCheck200Response
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
    api_instance = kenny_agi_sdk.SystemApi(api_client)

    try:
        # Health check
        api_response = await api_instance.health_check()
        print("The response of SystemApi->health_check:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SystemApi->health_check: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**HealthCheck200Response**](HealthCheck200Response.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Health status |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

