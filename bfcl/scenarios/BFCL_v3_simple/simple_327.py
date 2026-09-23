from typing import List, Dict, Any, Union, Tuple, Set 
def sports_team_get_schedule(team_name:str, num_of_games:int, league:str, location:str=None) -> str:
	"""
	sports_team_get_schedule : Fetches the schedule of the specified sports team for the specified number of games in the given league.    
	Parameters:
	team_name (str): The name of the sports team.
	num_of_games (int): Number of games for which to fetch the schedule.
	league (str): The name of the sports league. If not provided, the function will fetch the schedule for all games, regardless of the league.
	location (str): Optional. The city or venue where games are to be held. If not provided, default that all venues will be considered.

	Required Parameter = [team_name,num_of_games,league,]

	"""
	return 'Success'

tools = [sports_team_get_schedule]
