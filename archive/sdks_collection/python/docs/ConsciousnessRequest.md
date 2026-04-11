# ConsciousnessRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**target_level** | **str** | Target consciousness level | [optional] [default to 'ENLIGHTENED']

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.consciousness_request import ConsciousnessRequest

# TODO update the JSON string below
json = "{}"
# create an instance of ConsciousnessRequest from a JSON string
consciousness_request_instance = ConsciousnessRequest.from_json(json)
# print the JSON string representation of the object
print(ConsciousnessRequest.to_json())

# convert the object into a dict
consciousness_request_dict = consciousness_request_instance.to_dict()
# create an instance of ConsciousnessRequest from a dict
consciousness_request_from_dict = ConsciousnessRequest.from_dict(consciousness_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


