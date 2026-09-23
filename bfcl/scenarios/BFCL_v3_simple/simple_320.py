from typing import List, Dict, Any, Union, Tuple, Set 
def sports_ranking_get_team_position(team:str, season:str, detailed:bool=False) -> str:
	"""
	sports_ranking_get_team_position : Retrieve a team's position and stats in the basketball league for a given season.    
	Parameters:
	team (str): The name of the team.
	season (str): The season for which data should be fetched.
	detailed (bool): Flag to retrieve detailed stats or just the position.

	Required Parameter = [team,season,]

	"""
	return 'Success'

tools = [sports_ranking_get_team_position]
