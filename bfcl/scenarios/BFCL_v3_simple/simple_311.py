from typing import List, Dict, Any, Union, Tuple, Set 
def sports_db_find_athlete(name:str, sport:str, team:str=None) -> str:
	"""
	sports_db_find_athlete : Find the profile information of a sports athlete based on their full name.    
	Parameters:
	name (str): The full name of the athlete.
	team (str): The team the athlete belongs to. Default to all teams if not specified.
	sport (str): The sport that athlete plays.

	Required Parameter = [name,sport,]

	"""
	return 'Success'

tools = [sports_db_find_athlete]
