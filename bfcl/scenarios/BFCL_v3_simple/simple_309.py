from typing import List, Dict, Any, Union, Tuple, Set 
def nfl_data_player_record(player_name:str, season_year:int, team:str=None) -> str:
	"""
	nfl_data_player_record : Retrieve the record of an NFL player in a specified season.    
	Parameters:
	player_name (str): The name of the NFL player.
	season_year (int): The year of the NFL season.
	team (str): The NFL team that the player played for in that season. Default is all teams if not specified.

	Required Parameter = [player_name,season_year,]

	"""
	return 'Success'

tools = [nfl_data_player_record]
