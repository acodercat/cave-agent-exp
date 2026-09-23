from typing import List, Dict, Any, Union, Tuple, Set 
def get_team_score(team_name:str, league:str, include_player_stats:bool=False) -> str:
	"""
	get_team_score : Retrieves the latest game score, individual player stats, and team stats for a specified sports team.    
	Parameters:
	team_name (str): The name of the sports team.
	league (str): The league that the team is part of.
	include_player_stats (bool): Indicates if individual player statistics should be included in the result. Default is false.

	Required Parameter = [team_name,league,]

	"""
	return 'Success'

tools = [get_team_score]
