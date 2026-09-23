from typing import List, Dict, Any, Union, Tuple, Set 
def soccer_get_last_match(team_name:str, include_stats:bool=None) -> str:
	"""
	soccer_get_last_match : Retrieve the details of the last match played by a specified soccer club.    
	Parameters:
	team_name (str): The name of the soccer club.
	include_stats (bool): If true, include match statistics like possession, shots on target etc. Default is false.

	Required Parameter = [team_name,]

	"""
	return 'Success'

tools = [soccer_get_last_match]
