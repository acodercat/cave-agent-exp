from typing import List, Dict, Any, Union, Tuple, Set 
def get_discoverer(discovery:str, detail:bool) -> str:
	"""
	get_discoverer : Get the person or team who made a particular scientific discovery    
	Parameters:
	discovery (str): The discovery for which the discoverer's information is needed.
	detail (bool): Optional flag to get additional details about the discoverer, such as birth date and nationality. Defaults to false.

	Required Parameter = [discovery,detail,]

	"""
	return 'Success'

tools = [get_discoverer]
