from typing import List, Dict, Any, Union, Tuple, Set 
def game_valuation(game_name:str, release_year:int, condition:str=None) -> str:
	"""
	game_valuation : Get the current market value of a vintage video game.    
	Parameters:
	game_name (str): The name of the game.
	release_year (int): The year the game was released.
	condition (str): The condition of the game. Default is 'Used'.

	Required Parameter = [game_name,release_year,]

	"""
	return 'Success'

tools = [game_valuation]
