from typing import List, Dict, Any, Union, Tuple, Set 
def sports_stats_get_performance(player_name:str, tournament:str, season:str, performance_indicator:List[str]=None) -> str:
	"""
	sports_stats_get_performance : Compute the performance score of a soccer player given his game stats for a specific tournament in a season.    
	Parameters:
	player_name (str): Name of the player.
	tournament (str): Name of the soccer tournament.
	season (str): Specific season in format 'YYYY-YYYY'.
	performance_indicator (List[str]): Array of performance indicators. Use as much as possible. Default to use all if not specified.

	Required Parameter = [player_name,tournament,season,]

	"""
	return 'Success'

tools = [sports_stats_get_performance]
