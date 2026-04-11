# kenny_agi_sdk.AGICoreApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_agi_status**](AGICoreApi.md#get_agi_status) | **GET** /api/v1/agi/status | Get AGI status
[**initialize_agi**](AGICoreApi.md#initialize_agi) | **POST** /api/v1/agi/initialize | Initialize AGI system
[**process_thought**](AGICoreApi.md#process_thought) | **POST** /api/v1/agi/think | Process thought
[**shutdown_agi**](AGICoreApi.md#shutdown_agi) | **POST** /api/v1/agi/shutdown | Shutdown AGI system


# **get_agi_status**
> Response get_agi_status()

Get AGI status

Get current AGI system status and metrics

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
    api_instance = kenny_agi_sdk.AGICoreApi(api_client)

    try:
        # Get AGI status
        api_response = await api_instance.get_agi_status()
        print("The response of AGICoreApi->get_agi_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AGICoreApi->get_agi_status: %s\n" % e)
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
**200** | AGI status retrieved successfully |  -  |
**500** | Internal server error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **initialize_agi**
> Response initialize_agi(agi_config_request)

Initialize AGI system

Initialize the AGI system with custom configuration

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.agi_config_request import AGIConfigRequest
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
    api_instance = kenny_agi_sdk.AGICoreApi(api_client)
    agi_config_request = kenny_agi_sdk.AGIConfigRequest() # AGIConfigRequest | 

    try:
        # Initialize AGI system
        api_response = await api_instance.initialize_agi(agi_config_request)
        print("The response of AGICoreApi->initialize_agi:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AGICoreApi->initialize_agi: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agi_config_request** | [**AGIConfigRequest**](AGIConfigRequest.md)|  | 

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
**200** | AGI initialized successfully |  -  |
**500** | Initialization failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **process_thought**
> Response process_thought(think_request)

Process thought

Process a thought through the AGI system

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.response import Response
from kenny_agi_sdk.models.think_request import ThinkRequest
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
    api_instance = kenny_agi_sdk.AGICoreApi(api_client)
    think_request = kenny_agi_sdk.ThinkRequest() # ThinkRequest | 

    try:
        # Process thought
        api_response = await api_instance.process_thought(think_request)
        print("The response of AGICoreApi->process_thought:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AGICoreApi->process_thought: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **think_request** | [**ThinkRequest**](ThinkRequest.md)|  | 

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
**200** | Thought processed successfully |  -  |
**500** | Processing failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **shutdown_agi**
> Response shutdown_agi()

Shutdown AGI system

Safely shutdown the AGI system

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
    api_instance = kenny_agi_sdk.AGICoreApi(api_client)

    try:
        # Shutdown AGI system
        api_response = await api_instance.shutdown_agi()
        print("The response of AGICoreApi->shutdown_agi:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AGICoreApi->shutdown_agi: %s\n" % e)
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
**200** | AGI shutdown complete |  -  |
**500** | Shutdown failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

