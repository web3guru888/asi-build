# ThinkRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Prompt** | **string** | The thought prompt to process | 
**Context** | Pointer to **map[string]interface{}** | Additional context for the thought process | [optional] 

## Methods

### NewThinkRequest

`func NewThinkRequest(prompt string, ) *ThinkRequest`

NewThinkRequest instantiates a new ThinkRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewThinkRequestWithDefaults

`func NewThinkRequestWithDefaults() *ThinkRequest`

NewThinkRequestWithDefaults instantiates a new ThinkRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetPrompt

`func (o *ThinkRequest) GetPrompt() string`

GetPrompt returns the Prompt field if non-nil, zero value otherwise.

### GetPromptOk

`func (o *ThinkRequest) GetPromptOk() (*string, bool)`

GetPromptOk returns a tuple with the Prompt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPrompt

`func (o *ThinkRequest) SetPrompt(v string)`

SetPrompt sets Prompt field to given value.


### GetContext

`func (o *ThinkRequest) GetContext() map[string]interface{}`

GetContext returns the Context field if non-nil, zero value otherwise.

### GetContextOk

`func (o *ThinkRequest) GetContextOk() (*map[string]interface{}, bool)`

GetContextOk returns a tuple with the Context field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContext

`func (o *ThinkRequest) SetContext(v map[string]interface{})`

SetContext sets Context field to given value.

### HasContext

`func (o *ThinkRequest) HasContext() bool`

HasContext returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


