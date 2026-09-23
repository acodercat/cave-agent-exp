from typing import List, Dict, Any, Union, Tuple, Set 
def property_records_get(address:str, parcel_number:str, county:str, include_owner:bool=False) -> str:
	"""
	property_records_get : Fetch property records based on location, parcel number and county.    
	Parameters:
	address (str): Address of the property.
	parcel_number (str): Parcel number of the property.
	county (str): County where the property is located.
	include_owner (bool): Include owner's name in the property record. Default is false.

	Required Parameter = [address,parcel_number,county,]

	"""
	return 'Success'

tools = [property_records_get]
