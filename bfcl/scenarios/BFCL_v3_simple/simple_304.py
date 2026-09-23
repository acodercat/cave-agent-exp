from typing import List, Dict, Any, Union, Tuple, Set 
def player_stats_getLastGame(player_name:str, team:str, metrics:List[str]=None) -> str:
	"""
	player_stats_getLastGame : Get last game statistics for a specific player in basketball    
	Parameters:
	player_name (str): The name of the basketball player.
	team (str): The team that player currently plays for.
	metrics (List[str]): Specific metrics to retrieve. If no value is specified, all available metrics will be returned by default.

	Required Parameter = [player_name,team,]

	"""
	return 'Success'

tools = [player_stats_getLastGame]
