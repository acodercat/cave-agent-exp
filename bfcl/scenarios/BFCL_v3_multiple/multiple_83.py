from typing import List, Dict, Any, Union, Tuple, Set 
def team_stats_get_top_scorer(team_name:str, competition:str=None) -> str:
	"""
	team_stats_get_top_scorer : Fetch the top scorer of a specified football team.    
	Parameters:
	team_name (str): The name of the football team.
	competition (str): Competition for which to fetch stats (optional). Default ''

	Required Parameter = [team_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def league_stats_get_top_scorer(league_name:str, season:str=None) -> str:
	"""
	league_stats_get_top_scorer : Fetch the top scorer of a specified football league.    
	Parameters:
	league_name (str): The name of the football league.
	season (str): Season for which to fetch stats (optional). Default ''

	Required Parameter = [league_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def player_stats_get_all_time_goals(player_name:str, team_name:str, competition:str=None) -> str:
	"""
	player_stats_get_all_time_goals : Fetch all-time goals scored by a particular football player for a specified team.    
	Parameters:
	player_name (str): The name of the football player.
	team_name (str): The name of the team for which player has played.
	competition (str): Competition for which to fetch stats (optional). Default ''

	Required Parameter = [player_name,team_name,]

	"""
	return 'Success'

tools = [team_stats_get_top_scorer, league_stats_get_top_scorer, player_stats_get_all_time_goals]
