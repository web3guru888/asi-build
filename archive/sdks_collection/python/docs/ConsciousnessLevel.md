# ConsciousnessLevel


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**level** | **str** |  | [optional] 
**value** | **float** | Numeric consciousness value | [optional] 
**active** | **bool** | Whether consciousness processing is active | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.consciousness_level import ConsciousnessLevel

# TODO update the JSON string below
json = "{}"
# create an instance of ConsciousnessLevel from a JSON string
consciousness_level_instance = ConsciousnessLevel.from_json(json)
# print the JSON string representation of the object
print(ConsciousnessLevel.to_json())

# convert the object into a dict
consciousness_level_dict = consciousness_level_instance.to_dict()
# create an instance of ConsciousnessLevel from a dict
consciousness_level_from_dict = ConsciousnessLevel.from_dict(consciousness_level_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


