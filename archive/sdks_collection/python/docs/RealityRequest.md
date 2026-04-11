# RealityRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Name for the new reality | 
**dimensions** | **int** | Number of spatial dimensions | [optional] [default to 4]
**axioms** | **List[str]** | Mathematical axioms governing the reality | [optional] 
**consciousness_level** | **float** | Base consciousness level for the reality | [optional] [default to 1.0]

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.reality_request import RealityRequest

# TODO update the JSON string below
json = "{}"
# create an instance of RealityRequest from a JSON string
reality_request_instance = RealityRequest.from_json(json)
# print the JSON string representation of the object
print(RealityRequest.to_json())

# convert the object into a dict
reality_request_dict = reality_request_instance.to_dict()
# create an instance of RealityRequest from a dict
reality_request_from_dict = RealityRequest.from_dict(reality_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


