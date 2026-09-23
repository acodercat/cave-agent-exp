from typing import List, Dict, Any, Union, Tuple, Set 
def player_status_check(team:str, player_id:int, season:int=None) -> str:
	"""
	player_status_check : Check a player's status in a team for a particular season.    
	Parameters:
	team (str): The team where the player plays.
	player_id (int): The id of the player.
	season (int): The season for which player's status need to be checked. Optional. Default is season 2023.

	Required Parameter = [team,player_id,]

	"""
	return 'Success'

tools = [player_status_check]
