from typing import List, Dict, Any, Union, Tuple, Set 
def get_team_info(team:str, info:str) -> str:
	"""
	get_team_info : Retrieve information for a specific team, such as championships won.    
	Parameters:
	team (str): The name of the team.
	info (str): The information sought. E.g., 'championships_won'.

	Required Parameter = [team,info,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_player_record(player:str, stat:str) -> str:
	"""
	get_player_record : Retrieve record stats for a specific player and stat type.    
	Parameters:
	player (str): The name of the player.
	stat (str): The type of statistic. E.g., 'highest_scoring_game', 'total_championships'.

	Required Parameter = [player,stat,]

	"""
	return 'Success'

tools = [get_team_info, get_player_record]
