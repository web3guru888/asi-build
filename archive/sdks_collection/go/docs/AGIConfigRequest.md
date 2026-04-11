# AGIConfigRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | Pointer to **string** | Name identifier for the AGI instance | [optional] [default to "KennyAGI"]
**ConsciousnessEnabled** | Pointer to **bool** | Enable consciousness operations | [optional] [default to true]
**SafetyMode** | Pointer to **bool** | Enable safety constraints and monitoring | [optional] [default to true]
**DivineAccess** | Pointer to **bool** | Enable divine mathematics access (requires elevated permissions) | [optional] [default to false]
**QuantumEnhanced** | Pointer to **bool** | Enable quantum computing enhancements | [optional] [default to false]

## Methods

### NewAGIConfigRequest

`func NewAGIConfigRequest() *AGIConfigRequest`

NewAGIConfigRequest instantiates a new AGIConfigRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAGIConfigRequestWithDefaults

`func NewAGIConfigRequestWithDefaults() *AGIConfigRequest`

NewAGIConfigRequestWithDefaults instantiates a new AGIConfigRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *AGIConfigRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *AGIConfigRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *AGIConfigRequest) SetName(v string)`

SetName sets Name field to given value.

### HasName

`func (o *AGIConfigRequest) HasName() bool`

HasName returns a boolean if a field has been set.

### GetConsciousnessEnabled

`func (o *AGIConfigRequest) GetConsciousnessEnabled() bool`

GetConsciousnessEnabled returns the ConsciousnessEnabled field if non-nil, zero value otherwise.

### GetConsciousnessEnabledOk

`func (o *AGIConfigRequest) GetConsciousnessEnabledOk() (*bool, bool)`

GetConsciousnessEnabledOk returns a tuple with the ConsciousnessEnabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsciousnessEnabled

`func (o *AGIConfigRequest) SetConsciousnessEnabled(v bool)`

SetConsciousnessEnabled sets ConsciousnessEnabled field to given value.

### HasConsciousnessEnabled

`func (o *AGIConfigRequest) HasConsciousnessEnabled() bool`

HasConsciousnessEnabled returns a boolean if a field has been set.

### GetSafetyMode

`func (o *AGIConfigRequest) GetSafetyMode() bool`

GetSafetyMode returns the SafetyMode field if non-nil, zero value otherwise.

### GetSafetyModeOk

`func (o *AGIConfigRequest) GetSafetyModeOk() (*bool, bool)`

GetSafetyModeOk returns a tuple with the SafetyMode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSafetyMode

`func (o *AGIConfigRequest) SetSafetyMode(v bool)`

SetSafetyMode sets SafetyMode field to given value.

### HasSafetyMode

`func (o *AGIConfigRequest) HasSafetyMode() bool`

HasSafetyMode returns a boolean if a field has been set.

### GetDivineAccess

`func (o *AGIConfigRequest) GetDivineAccess() bool`

GetDivineAccess returns the DivineAccess field if non-nil, zero value otherwise.

### GetDivineAccessOk

`func (o *AGIConfigRequest) GetDivineAccessOk() (*bool, bool)`

GetDivineAccessOk returns a tuple with the DivineAccess field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDivineAccess

`func (o *AGIConfigRequest) SetDivineAccess(v bool)`

SetDivineAccess sets DivineAccess field to given value.

### HasDivineAccess

`func (o *AGIConfigRequest) HasDivineAccess() bool`

HasDivineAccess returns a boolean if a field has been set.

### GetQuantumEnhanced

`func (o *AGIConfigRequest) GetQuantumEnhanced() bool`

GetQuantumEnhanced returns the QuantumEnhanced field if non-nil, zero value otherwise.

### GetQuantumEnhancedOk

`func (o *AGIConfigRequest) GetQuantumEnhancedOk() (*bool, bool)`

GetQuantumEnhancedOk returns a tuple with the QuantumEnhanced field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetQuantumEnhanced

`func (o *AGIConfigRequest) SetQuantumEnhanced(v bool)`

SetQuantumEnhanced sets QuantumEnhanced field to given value.

### HasQuantumEnhanced

`func (o *AGIConfigRequest) HasQuantumEnhanced() bool`

HasQuantumEnhanced returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


