# CheckAlignmentRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**action** | **str** | The action to check for alignment | 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.check_alignment_request import CheckAlignmentRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CheckAlignmentRequest from a JSON string
check_alignment_request_instance = CheckAlignmentRequest.from_json(json)
# print the JSON string representation of the object
print(CheckAlignmentRequest.to_json())

# convert the object into a dict
check_alignment_request_dict = check_alignment_request_instance.to_dict()
# create an instance of CheckAlignmentRequest from a dict
check_alignment_request_from_dict = CheckAlignmentRequest.from_dict(check_alignment_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


