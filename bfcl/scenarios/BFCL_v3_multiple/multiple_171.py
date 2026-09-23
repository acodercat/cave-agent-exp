from typing import List, Dict, Any, Union, Tuple, Set 
def poker_probability_full_house(deck_size:int, hand_size:int) -> str:
	"""
	poker_probability_full_house : Calculate the probability of getting a full house in a poker game.    
	Parameters:
	deck_size (int): The size of the deck. Default is 52.
	hand_size (int): The size of the hand. Default is 5.

	Required Parameter = [deck_size,hand_size,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def game_result_get_winner(teams:List[str], date:str, venue:str=None) -> str:
	"""
	game_result_get_winner : Get the winner of a specific basketball game.    
	Parameters:
	teams (List[str]): List of two teams who played the game.
	date (str): The date of the game, formatted as YYYY-MM-DD.
	venue (str): Optional: The venue of the game. Default is ''

	Required Parameter = [teams,date,]

	"""
	return 'Success'

tools = [poker_probability_full_house, game_result_get_winner]
