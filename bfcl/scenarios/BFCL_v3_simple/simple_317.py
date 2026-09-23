from typing import List, Dict, Any, Union, Tuple, Set 
def get_team_rank(team_name:str, league:str, season:str, type:str) -> str:
	"""
	get_team_rank : Get the team ranking in a sports league based on season and type.    
	Parameters:
	team_name (str): The name of the sports team.
	league (str): The name of the league in which the team competes.
	season (str): The season for which the team's ranking is sought.
	type (str): Type of the season: regular or playoff.

	Required Parameter = [team_name,league,season,type,]

	"""
	return 'Success'

tools = [get_team_rank]
