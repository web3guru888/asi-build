# Response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Success** | **bool** | Whether the operation was successful | 
**Message** | **string** | Human-readable response message | 
**Data** | Pointer to **map[string]interface{}** | Response data (varies by endpoint) | [optional] 
**Timestamp** | **time.Time** | ISO 8601 timestamp of the response | 

## Methods

### NewResponse

`func NewResponse(success bool, message string, timestamp time.Time, ) *Response`

NewResponse instantiates a new Response object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewResponseWithDefaults

`func NewResponseWithDefaults() *Response`

NewResponseWithDefaults instantiates a new Response object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSuccess

`func (o *Response) GetSuccess() bool`

GetSuccess returns the Success field if non-nil, zero value otherwise.

### GetSuccessOk

`func (o *Response) GetSuccessOk() (*bool, bool)`

GetSuccessOk returns a tuple with the Success field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSuccess

`func (o *Response) SetSuccess(v bool)`

SetSuccess sets Success field to given value.


### GetMessage

`func (o *Response) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *Response) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *Response) SetMessage(v string)`

SetMessage sets Message field to given value.


### GetData

`func (o *Response) GetData() map[string]interface{}`

GetData returns the Data field if non-nil, zero value otherwise.

### GetDataOk

`func (o *Response) GetDataOk() (*map[string]interface{}, bool)`

GetDataOk returns a tuple with the Data field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetData

`func (o *Response) SetData(v map[string]interface{})`

SetData sets Data field to given value.

### HasData

`func (o *Response) HasData() bool`

HasData returns a boolean if a field has been set.

### GetTimestamp

`func (o *Response) GetTimestamp() time.Time`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *Response) GetTimestampOk() (*time.Time, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *Response) SetTimestamp(v time.Time)`

SetTimestamp sets Timestamp field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


