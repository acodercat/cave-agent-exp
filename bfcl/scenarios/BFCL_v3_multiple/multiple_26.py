from typing import List, Dict, Any, Union, Tuple, Set 
def game_scores_get(game:str, platform:str, level:int, player:str=None) -> str:
	"""
	game_scores_get : Retrieve scores and rankings based on player’s performance in a certain game.    
	Parameters:
	game (str): The name of the game.
	platform (str): The gaming platform e.g. Xbox, Playstation, PC
	level (int): The level of the game for which you want to retrieve the scores.
	player (str): The name of the player for whom you want to retrieve scores. Default ''

	Required Parameter = [game,platform,level,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def game_rewards_get(game:str, platform:str, mission:str=None, trophy:str=None) -> str:
	"""
	game_rewards_get : Retrieve information about different types of rewards that you can receive when playing a certain game.    
	Parameters:
	game (str): The name of the game.
	platform (str): The gaming platform e.g. Xbox, Playstation, PC
	mission (str): The mission for which you want to know the rewards. Default to ''
	trophy (str): The trophy level for which you want to know the rewards. Default to ''

	Required Parameter = [game,platform,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def game_missions_list(game:str) -> str:
	"""
	game_missions_list : List all missions for a certain game.    
	Parameters:
	game (str): The name of the game.

	Required Parameter = [game,]

	"""
	return 'Success'

tools = [game_scores_get, game_rewards_get, game_missions_list]
