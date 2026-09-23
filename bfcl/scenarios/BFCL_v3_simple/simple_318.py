from typing import List, Dict, Any, Union, Tuple, Set 
def get_team_ranking(team_name:str, year:int, gender:str=None) -> str:
	"""
	get_team_ranking : Retrieve the FIFA ranking of a specific soccer team for a certain year.    
	Parameters:
	team_name (str): The name of the soccer team.
	year (int): The year for which the ranking is to be retrieved.
	gender (str): The gender of the team. It can be either 'men' or 'women'. Default is 'men'.

	Required Parameter = [team_name,year,]

	"""
	return 'Success'

tools = [get_team_ranking]
