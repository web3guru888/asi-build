# kenny_agi_sdk.ConstitutionalAIApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**check_alignment**](ConstitutionalAIApi.md#check_alignment) | **POST** /api/v1/constitution/check | Check alignment
[**get_constitution_status**](ConstitutionalAIApi.md#get_constitution_status) | **GET** /api/v1/constitution/status | Get constitution status


# **check_alignment**
> Response check_alignment(check_alignment_request)

Check alignment

Check if an action aligns with constitutional values

### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
from kenny_agi_sdk.models.check_alignment_request import CheckAlignmentRequest
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
    api_instance = kenny_agi_sdk.ConstitutionalAIApi(api_client)
    check_alignment_request = kenny_agi_sdk.CheckAlignmentRequest() # CheckAlignmentRequest | 

    try:
        # Check alignment
        api_response = await api_instance.check_alignment(check_alignment_request)
        print("The response of ConstitutionalAIApi->check_alignment:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ConstitutionalAIApi->check_alignment: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **check_alignment_request** | [**CheckAlignmentRequest**](CheckAlignmentRequest.md)|  | 

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
**200** | Alignment checked successfully |  -  |
**400** | Constitutional AI module not available |  -  |
**500** | Alignment check failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_constitution_status**
> Response get_constitution_status()

Get constitution status

Get current constitutional AI status and constraints

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
    api_instance = kenny_agi_sdk.ConstitutionalAIApi(api_client)

    try:
        # Get constitution status
        api_response = await api_instance.get_constitution_status()
        print("The response of ConstitutionalAIApi->get_constitution_status:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ConstitutionalAIApi->get_constitution_status: %s\n" % e)
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
**200** | Constitution status retrieved |  -  |
**400** | Constitutional AI module not available |  -  |
**500** | Retrieval failed |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

