from typing import List, Dict, Any, Union, Tuple, Set 
def game_list_get_games(release_year:int, multiplayer:bool, ESRB_rating:str) -> str:
	"""
	game_list_get_games : Get a list of video games based on release year, multiplayer functionality and ESRB rating    
	Parameters:
	release_year (int): The year the game was released.
	multiplayer (bool): Whether the game has multiplayer functionality.
	ESRB_rating (str): The ESRB rating of the game.

	Required Parameter = [release_year,multiplayer,ESRB_rating,]

	"""
	return 'Success'

tools = [game_list_get_games]
