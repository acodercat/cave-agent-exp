from typing import List, Dict, Any, Union, Tuple, Set 
def analyze_structure(building_id:str, floors:List[int], mode:str=None) -> str:
	"""
	analyze_structure : Analyze a structure of a building based on its Id and floor numbers.    
	Parameters:
	building_id (str): The unique identification number of the building.
	floors (List[int]): Floor numbers to be analyzed.
	mode (str): Mode of analysis, e.g. 'static' or 'dynamic'. Default is 'static'.

	Required Parameter = [building_id,floors,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def player_statistic(player_name:str, year:int, team_name:str=None) -> str:
	"""
	player_statistic : Retrieves detailed player's statistics for a specific year.    
	Parameters:
	player_name (str): The player's name.
	year (int): Year for which the statistics will be displayed.
	team_name (str): The name of the team(optional). Default is all if not specified.

	Required Parameter = [player_name,year,]

	"""
	return 'Success'

tools = [analyze_structure, player_statistic]
