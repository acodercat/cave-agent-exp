from typing import List, Dict, Any, Union, Tuple, Set 
def sports_data_basketball_most_points_single_game(league:str) -> str:
	"""
	sports_data_basketball_most_points_single_game : Returns the record for the most points scored by a single player in one game of NBA, including the player name, points scored, and game date.    
	Parameters:
	league (str): The specific basketball league for which to fetch the record. In this case, 'NBA'.

	Required Parameter = [league,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sports_data_basketball_most_points_career(league:str) -> str:
	"""
	sports_data_basketball_most_points_career : Returns the record for the most points scored by a player in his career in NBA, including the player name, total points scored, and career span.    
	Parameters:
	league (str): The specific basketball league for which to fetch the record. In this case, 'NBA'.

	Required Parameter = [league,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sports_data_basketball_most_points_single_season(league:str) -> str:
	"""
	sports_data_basketball_most_points_single_season : Returns the record for the most points scored by a single player in one season of NBA, including the player name, points scored, and season.    
	Parameters:
	league (str): The specific basketball league for which to fetch the record. In this case, 'NBA'.

	Required Parameter = [league,]

	"""
	return 'Success'

tools = [sports_data_basketball_most_points_single_game, sports_data_basketball_most_points_career, sports_data_basketball_most_points_single_season]
