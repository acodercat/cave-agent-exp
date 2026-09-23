from typing import List, Dict, Any, Union, Tuple, Set 
def sports_ranking_get_current(team:str, league:str, season:str=None) -> str:
	"""
	sports_ranking_get_current : Retrieve the current ranking of a specific team in a particular league.    
	Parameters:
	team (str): The name of the team whose ranking is sought.
	league (str): The league in which the team participates.
	season (str): The season for which the ranking is sought. Defaults to the current season '2023-2024' if not provided.

	Required Parameter = [team,league,]

	"""
	return 'Success'

tools = [sports_ranking_get_current]
