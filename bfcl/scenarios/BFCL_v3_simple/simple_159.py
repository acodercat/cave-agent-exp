from typing import List, Dict, Any, Union, Tuple, Set 
def get_act_details(act_name:str, amendment_year:int) -> str:
	"""
	get_act_details : Retrieve the details of a particular legal act based on its name and year of amendment if any.    
	Parameters:
	act_name (str): The name of the act.
	amendment_year (int): Year of amendment if any. If not provided, the latest amendment year will be considered.

	Required Parameter = [act_name,amendment_year,]

	"""
	return 'Success'

tools = [get_act_details]
