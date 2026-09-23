from typing import List, Dict, Any, Union, Tuple, Set 
def get_crime_rate(city:str, state:str, type:str=None, year:int=None) -> str:
	"""
	get_crime_rate : Retrieve the official crime rate of a city.    
	Parameters:
	city (str): The name of the city.
	state (str): The state where the city is located.
	type (str): Optional. The type of crime. Default ''
	year (int): Optional. The year for the crime rate data. Defaults to 2024.

	Required Parameter = [city,state,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def poker_game_winner(players:List[str], cards:Dict[str, Any], type:str=None) -> str:
	"""
	poker_game_winner : Identify the winner in a poker game based on the cards.    
	Parameters:
	players (List[str]): Names of the players in a list.
	cards (Dict[str, Any]): An object containing the player name as key and the cards as values in a list.
	type (str): Type of poker game. Defaults to 'Texas Holdem'

	Required Parameter = [players,cards,]

	"""
	return 'Success'

tools = [get_crime_rate, poker_game_winner]
