# GetApiInfo200Response


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | [optional] 
**version** | **str** |  | [optional] 
**status** | **str** |  | [optional] 
**endpoints** | **object** |  | [optional] 

## Example

```python
from kenny_agi_sdk.kenny_agi_sdk.models.get_api_info200_response import GetApiInfo200Response

# TODO update the JSON string below
json = "{}"
# create an instance of GetApiInfo200Response from a JSON string
get_api_info200_response_instance = GetApiInfo200Response.from_json(json)
# print the JSON string representation of the object
print(GetApiInfo200Response.to_json())

# convert the object into a dict
get_api_info200_response_dict = get_api_info200_response_instance.to_dict()
# create an instance of GetApiInfo200Response from a dict
get_api_info200_response_from_dict = GetApiInfo200Response.from_dict(get_api_info200_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


