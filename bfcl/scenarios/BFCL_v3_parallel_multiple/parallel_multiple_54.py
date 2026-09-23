from typing import List, Dict, Any, Union, Tuple, Set 
def BattleReignGameAPI_update_player_equipment(attribute:str, level:int, playerID:int=123) -> str:
	"""
	BattleReignGameAPI_update_player_equipment : Modify the player's equipment level for specified attributes    
	Parameters:
	attribute (str): The attribute of the equipment to modify.
	level (int): The level to modify the attribute to.
	playerID (int): Player ID of the player. Default to 123

	Required Parameter = [attribute,level,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def GameGuideAPI_search_guide(game:str, condition:str='', type:str='') -> str:
	"""
	GameGuideAPI_search_guide : Search for game guides given specific conditions and preferences    
	Parameters:
	game (str): Name of the game.
	condition (str): Specific game conditions. (eg: 'snowy weather', 'hard mode').
	type (str): Specific type of guide. (eg: 'strategy', 'walkthrough')

	Required Parameter = [game,]

	"""
	return 'Success'

tools = [BattleReignGameAPI_update_player_equipment, GameGuideAPI_search_guide]
