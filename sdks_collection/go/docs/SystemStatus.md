# SystemStatus

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | Pointer to **string** |  | [optional] 
**Modules** | Pointer to **map[string]string** | Status of individual modules | [optional] 
**Performance** | Pointer to [**SystemStatusPerformance**](SystemStatusPerformance.md) |  | [optional] 
**LastUpdated** | Pointer to **time.Time** |  | [optional] 

## Methods

### NewSystemStatus

`func NewSystemStatus() *SystemStatus`

NewSystemStatus instantiates a new SystemStatus object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSystemStatusWithDefaults

`func NewSystemStatusWithDefaults() *SystemStatus`

NewSystemStatusWithDefaults instantiates a new SystemStatus object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *SystemStatus) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *SystemStatus) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *SystemStatus) SetStatus(v string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *SystemStatus) HasStatus() bool`

HasStatus returns a boolean if a field has been set.

### GetModules

`func (o *SystemStatus) GetModules() map[string]string`

GetModules returns the Modules field if non-nil, zero value otherwise.

### GetModulesOk

`func (o *SystemStatus) GetModulesOk() (*map[string]string, bool)`

GetModulesOk returns a tuple with the Modules field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetModules

`func (o *SystemStatus) SetModules(v map[string]string)`

SetModules sets Modules field to given value.

### HasModules

`func (o *SystemStatus) HasModules() bool`

HasModules returns a boolean if a field has been set.

### GetPerformance

`func (o *SystemStatus) GetPerformance() SystemStatusPerformance`

GetPerformance returns the Performance field if non-nil, zero value otherwise.

### GetPerformanceOk

`func (o *SystemStatus) GetPerformanceOk() (*SystemStatusPerformance, bool)`

GetPerformanceOk returns a tuple with the Performance field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPerformance

`func (o *SystemStatus) SetPerformance(v SystemStatusPerformance)`

SetPerformance sets Performance field to given value.

### HasPerformance

`func (o *SystemStatus) HasPerformance() bool`

HasPerformance returns a boolean if a field has been set.

### GetLastUpdated

`func (o *SystemStatus) GetLastUpdated() time.Time`

GetLastUpdated returns the LastUpdated field if non-nil, zero value otherwise.

### GetLastUpdatedOk

`func (o *SystemStatus) GetLastUpdatedOk() (*time.Time, bool)`

GetLastUpdatedOk returns a tuple with the LastUpdated field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastUpdated

`func (o *SystemStatus) SetLastUpdated(v time.Time)`

SetLastUpdated sets LastUpdated field to given value.

### HasLastUpdated

`func (o *SystemStatus) HasLastUpdated() bool`

HasLastUpdated returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


