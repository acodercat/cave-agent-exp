from typing import List, Dict, Any, Union, Tuple, Set 
def PokemonGO_get_moves(pokemon:str, move:str=None) -> str:
	"""
	PokemonGO_get_moves : Retrieve the set of moves a Pokemon can learn. The optional parameter checks if the Pokemon can learn a specified move.    
	Parameters:
	pokemon (str): The name of the Pokemon.
	move (str): An optional parameter that checks if the Pokemon can learn this specific move. default is 'Run'

	Required Parameter = [pokemon,]

	"""
	return 'Success'

tools = [PokemonGO_get_moves]
