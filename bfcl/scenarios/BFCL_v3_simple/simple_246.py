from typing import List, Dict, Any, Union, Tuple, Set 
def science_history_get_discovery_details(discovery:str, method_used:str=None) -> str:
	"""
	science_history_get_discovery_details : Retrieve the details of a scientific discovery based on the discovery name.    
	Parameters:
	discovery (str): The name of the discovery, e.g. Gravity
	method_used (str): The method used for the discovery, default value is 'default' which gives the most accepted method.

	Required Parameter = [discovery,]

	"""
	return 'Success'

tools = [science_history_get_discovery_details]
