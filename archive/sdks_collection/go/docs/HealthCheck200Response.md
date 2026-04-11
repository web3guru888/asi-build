# HealthCheck200Response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | Pointer to **string** |  | [optional] 
**Timestamp** | Pointer to **time.Time** |  | [optional] 
**Services** | Pointer to [**HealthCheck200ResponseServices**](HealthCheck200ResponseServices.md) |  | [optional] 

## Methods

### NewHealthCheck200Response

`func NewHealthCheck200Response() *HealthCheck200Response`

NewHealthCheck200Response instantiates a new HealthCheck200Response object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewHealthCheck200ResponseWithDefaults

`func NewHealthCheck200ResponseWithDefaults() *HealthCheck200Response`

NewHealthCheck200ResponseWithDefaults instantiates a new HealthCheck200Response object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *HealthCheck200Response) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *HealthCheck200Response) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *HealthCheck200Response) SetStatus(v string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *HealthCheck200Response) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### GetTimestamp

`func (o *HealthCheck200Response) GetTimestamp() time.Time`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *HealthCheck200Response) GetTimestampOk() (*time.Time, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *HealthCheck200Response) SetTimestamp(v time.Time)`

SetTimestamp sets Timestamp field to given value.

### HasTimestamp

`func (o *HealthCheck200Response) HasTimestamp() bool`

HasTimestamp returns a boolean if a field has been set.

### GetServices

`func (o *HealthCheck200Response) GetServices() HealthCheck200ResponseServices`

GetServices returns the Services field if non-nil, zero value otherwise.

### GetServicesOk

`func (o *HealthCheck200Response) GetServicesOk() (*HealthCheck200ResponseServices, bool)`

GetServicesOk returns a tuple with the Services field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetServices

`func (o *HealthCheck200Response) SetServices(v HealthCheck200ResponseServices)`

SetServices sets Services field to given value.

### HasServices

`func (o *HealthCheck200Response) HasServices() bool`

HasServices returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


