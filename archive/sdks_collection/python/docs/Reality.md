# Reality


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Reality identifier | [optional] 
**dimensions** | **int** | Number of dimensions | [optional] 
**axioms** | **List[str]** | Governing axioms | [optional] 
**consciousness_level** | **float** | Base consciousness level | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.reality import Reality

# TODO update the JSON string below
json = "{}"
# create an instance of Reality from a JSON string
reality_instance = Reality.from_json(json)
# print the JSON string representation of the object
print(Reality.to_json())

# convert the object into a dict
reality_dict = reality_instance.to_dict()
# create an instance of Reality from a dict
reality_from_dict = Reality.from_dict(reality_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


