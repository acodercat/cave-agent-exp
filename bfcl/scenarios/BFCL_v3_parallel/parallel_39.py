from typing import List, Dict, Any, Union, Tuple, Set 
def museum_info_get_info(location:str, details:List[str]) -> str:
	"""
	museum_info_get_info : Retrieve specific details about museums, such as opening hours and ticket prices.    
	Parameters:
	location (str): City where the museum is located.
	details (List[str]): List of details to retrieve about the museum.

	Required Parameter = [location,details,]

	"""
	return 'Success'

tools = [museum_info_get_info]
