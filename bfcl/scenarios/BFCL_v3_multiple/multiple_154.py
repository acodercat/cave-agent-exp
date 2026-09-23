from typing import List, Dict, Any, Union, Tuple, Set 
def US_president_in_year(year:int, full_name:bool=True) -> str:
	"""
	US_president_in_year : Retrieve the name of the U.S. president in a given year.    
	Parameters:
	year (int): The year in question.
	full_name (bool): Option to return full name with middle initial, if applicable.

	Required Parameter = [year,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def find_card_in_deck(rank:str, suit:str, deck:List[Dict[str, str]]=None) -> str:
	"""
	find_card_in_deck : Locate a particular card in a deck based on rank and suit.    
	Parameters:
	rank (str): Rank of the card (e.g. Ace, Two, King).
	suit (str): Suit of the card (e.g. Hearts, Spades, Diamonds, Clubs).
	deck (List[Dict[str, str]]): Deck of cards. If not provided, the deck will be a standard 52 card deck by default

	Required Parameter = [rank,suit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def soccer_get_last_match(team_name:str, include_stats:bool=None) -> str:
	"""
	soccer_get_last_match : Retrieve the details of the last match played by a specified soccer club.    
	Parameters:
	team_name (str): The name of the soccer club.
	include_stats (bool): If true, include match statistics like possession, shots on target etc. Default is false.

	Required Parameter = [team_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def update_user_info(user_id:int, update_info:Dict[str, str], database:str='CustomerInfo') -> str:
	"""
	update_user_info : Update user information in the database.    
	Parameters:
	user_id (int): The user ID of the customer.
	update_info (Dict[str, str]): The new information to update.
	database (str): The database where the user's information is stored.

	Required Parameter = [user_id,update_info,]

	"""
	return 'Success'

tools = [US_president_in_year, find_card_in_deck, soccer_get_last_match, update_user_info]
