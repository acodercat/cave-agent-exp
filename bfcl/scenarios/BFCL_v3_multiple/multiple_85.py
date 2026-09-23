from typing import List, Dict, Any, Union, Tuple, Set 
def basketball_scores_get_scores(team:str, league:str, rounds:int) -> str:
	"""
	basketball_scores_get_scores : Retrieve basketball scores for a specific team and league within a certain range of rounds.    
	Parameters:
	team (str): The basketball team whose scores are to be retrieved.
	league (str): The league in which the team competes.
	rounds (int): Number of past rounds for which to retrieve the scores.

	Required Parameter = [team,league,rounds,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def soccer_scores_get_scores(team:str, league:str, rounds:int) -> str:
	"""
	soccer_scores_get_scores : Retrieve soccer scores for a specific team and league within a certain range of rounds.    
	Parameters:
	team (str): The soccer team whose scores are to be retrieved.
	league (str): The league in which the team competes.
	rounds (int): Number of past rounds for which to retrieve the scores.

	Required Parameter = [team,league,rounds,]

	"""
	return 'Success'

tools = [basketball_scores_get_scores, soccer_scores_get_scores]
