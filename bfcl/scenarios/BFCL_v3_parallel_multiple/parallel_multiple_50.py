from typing import List, Dict, Any, Union, Tuple, Set 
def sport_analysis_last_game_performance(team:str, details:List[str]) -> str:
	"""
	sport_analysis_last_game_performance : Analyzes the team's performance in their most recent game.    
	Parameters:
	team (str): The sports team that needs to be analyzed.
	details (List[str]): Key performance indicators that you want for the analysis

	Required Parameter = [team,details,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sport_analysis_compare_ppg(team:str, seasons:List[str]) -> str:
	"""
	sport_analysis_compare_ppg : Compares a team's average points per game in two different seasons.    
	Parameters:
	team (str): The sports team that needs to be compared.
	seasons (List[str]): The seasons that you want to compare the ppg.

	Required Parameter = [team,seasons,]

	"""
	return 'Success'

tools = [sport_analysis_last_game_performance, sport_analysis_compare_ppg]
