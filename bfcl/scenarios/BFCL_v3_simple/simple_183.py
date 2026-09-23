from typing import List, Dict, Any, Union, Tuple, Set 
def lawsuit_search(entity:str, county:str, state:str=None) -> str:
	"""
	lawsuit_search : Retrieve all lawsuits involving a particular entity from specified jurisdiction.    
	Parameters:
	entity (str): The entity involved in lawsuits.
	county (str): The jurisdiction for the lawsuit search for example Alameda county.
	state (str): The state for the lawsuit search. Default is California.

	Required Parameter = [entity,county,]

	"""
	return 'Success'

tools = [lawsuit_search]
