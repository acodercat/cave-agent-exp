from typing import List, Dict, Any, Union, Tuple, Set 
def get_song_lyrics(song_title:str, artist_name:str, lang:str=None) -> str:
	"""
	get_song_lyrics : Retrieve the lyrics of a song based on the artist's name and song title.    
	Parameters:
	song_title (str): The title of the song.
	artist_name (str): The name of the artist who performed the song.
	lang (str): The language of the lyrics. Default is English.

	Required Parameter = [song_title,artist_name,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def mix_paint_color(color1:str, color2:str, lightness:int=None) -> str:
	"""
	mix_paint_color : Combine two primary paint colors and adjust the resulting color's lightness level.    
	Parameters:
	color1 (str): The first primary color to be mixed.
	color2 (str): The second primary color to be mixed.
	lightness (int): The desired lightness level of the resulting color in percentage. The default level is set to 50.

	Required Parameter = [color1,color2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def finance_calculate_quarterly_dividend_per_share(total_payout:int, outstanding_shares:int) -> str:
	"""
	finance_calculate_quarterly_dividend_per_share : Calculate quarterly dividend per share for a company given total dividend payout and outstanding shares    
	Parameters:
	total_payout (int): The total amount of dividends paid out in USD
	outstanding_shares (int): Total number of outstanding shares

	Required Parameter = [total_payout,outstanding_shares,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def movie_details_brief(title:str, extra_info:bool=False) -> str:
	"""
	movie_details_brief : This function retrieves a brief about a specified movie.    
	Parameters:
	title (str): Title of the movie
	extra_info (bool): Option to get additional information like Director, Cast, Awards etc.

	Required Parameter = [title,]

	"""
	return 'Success'

tools = [get_song_lyrics, mix_paint_color, finance_calculate_quarterly_dividend_per_share, movie_details_brief]
