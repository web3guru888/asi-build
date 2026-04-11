# ThinkRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**prompt** | **str** | The thought prompt to process | 
**context** | **Dict[str, object]** | Additional context for the thought process | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.think_request import ThinkRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ThinkRequest from a JSON string
think_request_instance = ThinkRequest.from_json(json)
# print the JSON string representation of the object
print(ThinkRequest.to_json())

# convert the object into a dict
think_request_dict = think_request_instance.to_dict()
# create an instance of ThinkRequest from a dict
think_request_from_dict = ThinkRequest.from_dict(think_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


