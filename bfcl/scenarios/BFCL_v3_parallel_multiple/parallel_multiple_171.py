from typing import List, Dict, Any, Union, Tuple, Set 
def air_quality(location:str, date:str) -> str:
	"""
	air_quality : Retrieve the air quality index for a specific location.    
	Parameters:
	location (str): The city that you want to get the air quality index for.
	date (str): The date you want to get the air quality index for. Default is today.

	Required Parameter = [location,date,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sports_ranking(team:str, league:str, season:int=None) -> str:
	"""
	sports_ranking : Fetch the ranking of a specific sports team in a specific league    
	Parameters:
	team (str): The name of the team.
	league (str): The name of the league.
	season (int): Optional parameter to specify the season, default is 2023 if not specified.

	Required Parameter = [team,league,]

	"""
	return 'Success'

tools = [air_quality, sports_ranking]
