from typing import List, Dict, Any, Union, Tuple, Set 
def soccer_stat_get_player_stats(player_name:str, season:str, league:str=None) -> str:
	"""
	soccer_stat_get_player_stats : Retrieve soccer player statistics for a given season.    
	Parameters:
	player_name (str): Name of the player.
	season (str): Soccer season, usually specified by two years.
	league (str): Optional - the soccer league, defaults to all leagues if not specified.

	Required Parameter = [player_name,season,]

	"""
	return 'Success'

tools = [soccer_stat_get_player_stats]
