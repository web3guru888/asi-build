# kenny_agi_sdk.WebSocketApi

All URIs are relative to *http://localhost:8000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**websocket_connection**](WebSocketApi.md#websocket_connection) | **GET** /ws | WebSocket endpoint


# **websocket_connection**
> websocket_connection()

WebSocket endpoint

WebSocket endpoint for real-time AGI updates and bidirectional communication.

**Connection**: `ws://localhost:8000/ws`

**Authentication**: Include `Authorization: Bearer <token>` header

**Message Format**:
- Send: Raw text messages for AGI processing
- Receive: JSON objects with type, data, and timestamp

**Message Types**:
- `thought`: AGI thought processing result
- `consciousness_change`: Consciousness level updates
- `reality_shift`: Reality matrix changes
- `error`: Error messages


### Example

* Bearer (JWT) Authentication (bearerAuth):

```python
import kenny_agi_sdk
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
    api_instance = kenny_agi_sdk.WebSocketApi(api_client)

    try:
        # WebSocket endpoint
        await api_instance.websocket_connection()
    except Exception as e:
        print("Exception when calling WebSocketApi->websocket_connection: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

void (empty response body)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**101** | WebSocket connection established |  -  |
**400** | Invalid WebSocket request |  -  |
**401** | Authentication required |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

