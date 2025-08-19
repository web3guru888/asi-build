# WebSocketMessage

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Type** | **string** |  | 
**Data** | Pointer to **map[string]interface{}** | Message-specific data | [optional] 
**Timestamp** | **time.Time** |  | 

## Methods

### NewWebSocketMessage

`func NewWebSocketMessage(type_ string, timestamp time.Time, ) *WebSocketMessage`

NewWebSocketMessage instantiates a new WebSocketMessage object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewWebSocketMessageWithDefaults

`func NewWebSocketMessageWithDefaults() *WebSocketMessage`

NewWebSocketMessageWithDefaults instantiates a new WebSocketMessage object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetType

`func (o *WebSocketMessage) GetType() string`

GetType returns the Type field if non-nil, zero value otherwise.

### GetTypeOk

`func (o *WebSocketMessage) GetTypeOk() (*string, bool)`

GetTypeOk returns a tuple with the Type field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetType

`func (o *WebSocketMessage) SetType(v string)`

SetType sets Type field to given value.


### GetData

`func (o *WebSocketMessage) GetData() map[string]interface{}`

GetData returns the Data field if non-nil, zero value otherwise.

### GetDataOk

`func (o *WebSocketMessage) GetDataOk() (*map[string]interface{}, bool)`

GetDataOk returns a tuple with the Data field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetData

`func (o *WebSocketMessage) SetData(v map[string]interface{})`

SetData sets Data field to given value.

### HasData

`func (o *WebSocketMessage) HasData() bool`

HasData returns a boolean if a field has been set.

### GetTimestamp

`func (o *WebSocketMessage) GetTimestamp() time.Time`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *WebSocketMessage) GetTimestampOk() (*time.Time, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *WebSocketMessage) SetTimestamp(v time.Time)`

SetTimestamp sets Timestamp field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


