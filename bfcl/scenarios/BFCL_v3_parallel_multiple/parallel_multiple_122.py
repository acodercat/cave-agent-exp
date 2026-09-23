from typing import List, Dict, Any, Union, Tuple, Set 
def games_update_find(game:str, platform:str, region:str=None) -> str:
	"""
	games_update_find : Find the latest updates or patches for a specific game on a specified gaming platform.    
	Parameters:
	game (str): The name of the game.
	platform (str): The gaming platform, e.g. Xbox, Playstation, PC.
	region (str): The region of the update (optional, default is 'global')

	Required Parameter = [game,platform,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def games_reviews_find(game:str, region:str=None) -> str:
	"""
	games_reviews_find : Find reviews for a specific game.    
	Parameters:
	game (str): The name of the game.
	region (str): The region where the reviews are coming from (optional, default is 'global')

	Required Parameter = [game,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def games_price_find(game:str, platform:str) -> str:
	"""
	games_price_find : Find the current price for a specific game on a specified gaming platform.    
	Parameters:
	game (str): The name of the game.
	platform (str): The gaming platform, e.g. Xbox, Playstation, PC.

	Required Parameter = [game,platform,]

	"""
	return 'Success'

tools = [games_update_find, games_reviews_find, games_price_find]
