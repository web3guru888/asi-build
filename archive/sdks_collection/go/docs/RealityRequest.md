# RealityRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** | Name for the new reality | 
**Dimensions** | Pointer to **int32** | Number of spatial dimensions | [optional] [default to 4]
**Axioms** | Pointer to **[]string** | Mathematical axioms governing the reality | [optional] 
**ConsciousnessLevel** | Pointer to **float32** | Base consciousness level for the reality | [optional] [default to 1.0]

## Methods

### NewRealityRequest

`func NewRealityRequest(name string, ) *RealityRequest`

NewRealityRequest instantiates a new RealityRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRealityRequestWithDefaults

`func NewRealityRequestWithDefaults() *RealityRequest`

NewRealityRequestWithDefaults instantiates a new RealityRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *RealityRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *RealityRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *RealityRequest) SetName(v string)`

SetName sets Name field to given value.


### GetDimensions

`func (o *RealityRequest) GetDimensions() int32`

GetDimensions returns the Dimensions field if non-nil, zero value otherwise.

### GetDimensionsOk

`func (o *RealityRequest) GetDimensionsOk() (*int32, bool)`

GetDimensionsOk returns a tuple with the Dimensions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDimensions

`func (o *RealityRequest) SetDimensions(v int32)`

SetDimensions sets Dimensions field to given value.

### HasDimensions

`func (o *RealityRequest) HasDimensions() bool`

HasDimensions returns a boolean if a field has been set.

### GetAxioms

`func (o *RealityRequest) GetAxioms() []string`

GetAxioms returns the Axioms field if non-nil, zero value otherwise.

### GetAxiomsOk

`func (o *RealityRequest) GetAxiomsOk() (*[]string, bool)`

GetAxiomsOk returns a tuple with the Axioms field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAxioms

`func (o *RealityRequest) SetAxioms(v []string)`

SetAxioms sets Axioms field to given value.

### HasAxioms

`func (o *RealityRequest) HasAxioms() bool`

HasAxioms returns a boolean if a field has been set.

### GetConsciousnessLevel

`func (o *RealityRequest) GetConsciousnessLevel() float32`

GetConsciousnessLevel returns the ConsciousnessLevel field if non-nil, zero value otherwise.

### GetConsciousnessLevelOk

`func (o *RealityRequest) GetConsciousnessLevelOk() (*float32, bool)`

GetConsciousnessLevelOk returns a tuple with the ConsciousnessLevel field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsciousnessLevel

`func (o *RealityRequest) SetConsciousnessLevel(v float32)`

SetConsciousnessLevel sets ConsciousnessLevel field to given value.

### HasConsciousnessLevel

`func (o *RealityRequest) HasConsciousnessLevel() bool`

HasConsciousnessLevel returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


