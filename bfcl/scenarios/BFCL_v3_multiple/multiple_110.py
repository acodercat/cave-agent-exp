from typing import List, Dict, Any, Union, Tuple, Set 
def get_collectables_in_season(game_name:str, season:str, item_type:str=None) -> str:
	"""
	get_collectables_in_season : Retrieve a list of collectable items in a specific game during a specified season.    
	Parameters:
	game_name (str): Name of the game.
	season (str): The season for which to retrieve the collectable items.
	item_type (str): The type of item to search for. Default is 'all'. Possible values: 'all', 'bug', 'fish', 'sea creatures', etc.

	Required Parameter = [game_name,season,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def mutation_type_find(snp_id:str, species:str=None) -> str:
	"""
	mutation_type_find : Finds the type of a genetic mutation based on its SNP (Single Nucleotide Polymorphism) ID.    
	Parameters:
	snp_id (str): The ID of the Single Nucleotide Polymorphism (SNP) mutation.
	species (str): Species in which the SNP occurs, default is 'Homo sapiens' (Humans).

	Required Parameter = [snp_id,]

	"""
	return 'Success'

tools = [get_collectables_in_season, mutation_type_find]
