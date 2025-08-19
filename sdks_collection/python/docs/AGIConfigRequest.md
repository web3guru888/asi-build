# AGIConfigRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name identifier for the AGI instance | [optional] [default to 'KennyAGI']
**consciousness_enabled** | **bool** | Enable consciousness operations | [optional] [default to True]
**safety_mode** | **bool** | Enable safety constraints and monitoring | [optional] [default to True]
**divine_access** | **bool** | Enable divine mathematics access (requires elevated permissions) | [optional] [default to False]
**quantum_enhanced** | **bool** | Enable quantum computing enhancements | [optional] [default to False]

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.agi_config_request import AGIConfigRequest

# TODO update the JSON string below
json = "{}"
# create an instance of AGIConfigRequest from a JSON string
agi_config_request_instance = AGIConfigRequest.from_json(json)
# print the JSON string representation of the object
print(AGIConfigRequest.to_json())

# convert the object into a dict
agi_config_request_dict = agi_config_request_instance.to_dict()
# create an instance of AGIConfigRequest from a dict
agi_config_request_from_dict = AGIConfigRequest.from_dict(agi_config_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


