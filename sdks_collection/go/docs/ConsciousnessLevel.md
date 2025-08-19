# ConsciousnessLevel

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Level** | Pointer to **string** |  | [optional] 
**Value** | Pointer to **float32** | Numeric consciousness value | [optional] 
**Active** | Pointer to **bool** | Whether consciousness processing is active | [optional] 

## Methods

### NewConsciousnessLevel

`func NewConsciousnessLevel() *ConsciousnessLevel`

NewConsciousnessLevel instantiates a new ConsciousnessLevel object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConsciousnessLevelWithDefaults

`func NewConsciousnessLevelWithDefaults() *ConsciousnessLevel`

NewConsciousnessLevelWithDefaults instantiates a new ConsciousnessLevel object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetLevel

`func (o *ConsciousnessLevel) GetLevel() string`

GetLevel returns the Level field if non-nil, zero value otherwise.

### GetLevelOk

`func (o *ConsciousnessLevel) GetLevelOk() (*string, bool)`

GetLevelOk returns a tuple with the Level field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLevel

`func (o *ConsciousnessLevel) SetLevel(v string)`

SetLevel sets Level field to given value.

### HasLevel

`func (o *ConsciousnessLevel) HasLevel() bool`

HasLevel returns a boolean if a field has been set.

### GetValue

`func (o *ConsciousnessLevel) GetValue() float32`

GetValue returns the Value field if non-nil, zero value otherwise.

### GetValueOk

`func (o *ConsciousnessLevel) GetValueOk() (*float32, bool)`

GetValueOk returns a tuple with the Value field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValue

`func (o *ConsciousnessLevel) SetValue(v float32)`

SetValue sets Value field to given value.

### HasValue

`func (o *ConsciousnessLevel) HasValue() bool`

HasValue returns a boolean if a field has been set.

### GetActive

`func (o *ConsciousnessLevel) GetActive() bool`

GetActive returns the Active field if non-nil, zero value otherwise.

### GetActiveOk

`func (o *ConsciousnessLevel) GetActiveOk() (*bool, bool)`

GetActiveOk returns a tuple with the Active field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActive

`func (o *ConsciousnessLevel) SetActive(v bool)`

SetActive sets Active field to given value.

### HasActive

`func (o *ConsciousnessLevel) HasActive() bool`

HasActive returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


