from typing import List, Dict, Any, Union, Tuple, Set 
def property_valuation_get(location:str, propertyType:str, bedrooms:int, age:int) -> str:
	"""
	property_valuation_get : Get estimated value of a property based on location, specifications and age    
	Parameters:
	location (str): City and state where the property is located, e.g. San Diego, CA.
	propertyType (str): Type of property such as villa, condo, apartment, etc.
	bedrooms (int): Number of bedrooms required in the property.
	age (int): Age of the property in years.

	Required Parameter = [location,propertyType,bedrooms,age,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def realestate_find_properties(location:str, propertyType:str, bedrooms:int, budget:Dict[str, float]) -> str:
	"""
	realestate_find_properties : Find properties based on location, budget, and specifications    
	Parameters:
	location (str): City and state where the property is located, e.g. San Diego, CA.
	propertyType (str): Type of property such as villa, condo, apartment, etc.
	bedrooms (int): Number of bedrooms required in the property.
	budget (Dict[str, float]): Budget range for the property.

	Required Parameter = [location,propertyType,bedrooms,budget,]

	"""
	return 'Success'

tools = [property_valuation_get, realestate_find_properties]
