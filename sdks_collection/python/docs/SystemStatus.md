# SystemStatus


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **str** |  | [optional] 
**modules** | **Dict[str, str]** | Status of individual modules | [optional] 
**performance** | [**SystemStatusPerformance**](SystemStatusPerformance.md) |  | [optional] 
**last_updated** | **datetime** |  | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.system_status import SystemStatus

# TODO update the JSON string below
json = "{}"
# create an instance of SystemStatus from a JSON string
system_status_instance = SystemStatus.from_json(json)
# print the JSON string representation of the object
print(SystemStatus.to_json())

# convert the object into a dict
system_status_dict = system_status_instance.to_dict()
# create an instance of SystemStatus from a dict
system_status_from_dict = SystemStatus.from_dict(system_status_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


