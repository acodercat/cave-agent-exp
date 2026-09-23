from typing import List, Dict, Any, Union, Tuple, Set 
def video_games_get_player_count(game_title:str, year:int, platform:str=None) -> str:
	"""
	video_games_get_player_count : Retrieves the number of active players for a specified video game and year.    
	Parameters:
	game_title (str): The title of the video game.
	year (int): The year in question.
	platform (str): The gaming platform (e.g. 'PC', 'Xbox', 'Playstation'). Default ''

	Required Parameter = [game_title,year,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def video_games_get_sales(game_title:str, year:int, platform:str=None) -> str:
	"""
	video_games_get_sales : Retrieves the sales figures for a specified video game and year.    
	Parameters:
	game_title (str): The title of the video game.
	year (int): The year in question.
	platform (str): The gaming platform (e.g. 'PC', 'Xbox', 'Playstation'). Default ''

	Required Parameter = [game_title,year,]

	"""
	return 'Success'

tools = [video_games_get_player_count, video_games_get_sales]
