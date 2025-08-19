# SystemStatusPerformance


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cpu_usage** | **float** |  | [optional] 
**memory_usage** | **float** |  | [optional] 
**consciousness_level** | **float** |  | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.system_status_performance import SystemStatusPerformance

# TODO update the JSON string below
json = "{}"
# create an instance of SystemStatusPerformance from a JSON string
system_status_performance_instance = SystemStatusPerformance.from_json(json)
# print the JSON string representation of the object
print(SystemStatusPerformance.to_json())

# convert the object into a dict
system_status_performance_dict = system_status_performance_instance.to_dict()
# create an instance of SystemStatusPerformance from a dict
system_status_performance_from_dict = SystemStatusPerformance.from_dict(system_status_performance_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


