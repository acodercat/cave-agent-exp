from typing import List, Dict, Any, Union, Tuple, Set 
def boardgame_get_info(name:str, parameters:List[str], language:str=None) -> str:
	"""
	boardgame_get_info : Retrieve detailed information of a board game.    
	Parameters:
	name (str): Name of the board game.
	parameters (List[str]): Game characteristics interested.
	language (str): The preferred language for the game information, default is English

	Required Parameter = [name,parameters,]

	"""
	return 'Success'

tools = [boardgame_get_info]
