from typing import List, Dict, Any, Union, Tuple, Set 
def multiplayer_game_finder(platform:str, rating:float, genre:str=None) -> str:
	"""
	multiplayer_game_finder : Locate multiplayer games that match specific criteria such as rating, platform compatibility, genre, etc.    
	Parameters:
	platform (str): The platform you want the game to be compatible with, e.g. Windows 10, PS5.
	rating (float): Desired minimum game rating on a 5.0 scale.
	genre (str): Desired game genre, e.g. Action, Adventure, Racing. Default is 'Action'.

	Required Parameter = [platform,rating,]

	"""
	return 'Success'

tools = [multiplayer_game_finder]
