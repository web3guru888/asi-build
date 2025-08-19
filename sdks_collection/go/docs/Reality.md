# Reality

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | Pointer to **string** | Reality identifier | [optional] 
**Dimensions** | Pointer to **int32** | Number of dimensions | [optional] 
**Axioms** | Pointer to **[]string** | Governing axioms | [optional] 
**ConsciousnessLevel** | Pointer to **float32** | Base consciousness level | [optional] 

## Methods

### NewReality

`func NewReality() *Reality`

NewReality instantiates a new Reality object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRealityWithDefaults

`func NewRealityWithDefaults() *Reality`

NewRealityWithDefaults instantiates a new Reality object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *Reality) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *Reality) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *Reality) SetName(v string)`

SetName sets Name field to given value.

### HasName

`func (o *Reality) HasName() bool`

HasName returns a boolean if a field has been set.

### GetDimensions

`func (o *Reality) GetDimensions() int32`

GetDimensions returns the Dimensions field if non-nil, zero value otherwise.

### GetDimensionsOk

`func (o *Reality) GetDimensionsOk() (*int32, bool)`

GetDimensionsOk returns a tuple with the Dimensions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDimensions

`func (o *Reality) SetDimensions(v int32)`

SetDimensions sets Dimensions field to given value.

### HasDimensions

`func (o *Reality) HasDimensions() bool`

HasDimensions returns a boolean if a field has been set.

### GetAxioms

`func (o *Reality) GetAxioms() []string`

GetAxioms returns the Axioms field if non-nil, zero value otherwise.

### GetAxiomsOk

`func (o *Reality) GetAxiomsOk() (*[]string, bool)`

GetAxiomsOk returns a tuple with the Axioms field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAxioms

`func (o *Reality) SetAxioms(v []string)`

SetAxioms sets Axioms field to given value.

### HasAxioms

`func (o *Reality) HasAxioms() bool`

HasAxioms returns a boolean if a field has been set.

### GetConsciousnessLevel

`func (o *Reality) GetConsciousnessLevel() float32`

GetConsciousnessLevel returns the ConsciousnessLevel field if non-nil, zero value otherwise.

### GetConsciousnessLevelOk

`func (o *Reality) GetConsciousnessLevelOk() (*float32, bool)`

GetConsciousnessLevelOk returns a tuple with the ConsciousnessLevel field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsciousnessLevel

`func (o *Reality) SetConsciousnessLevel(v float32)`

SetConsciousnessLevel sets ConsciousnessLevel field to given value.

### HasConsciousnessLevel

`func (o *Reality) HasConsciousnessLevel() bool`

HasConsciousnessLevel returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


