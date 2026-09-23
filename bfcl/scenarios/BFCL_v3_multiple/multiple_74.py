from typing import List, Dict, Any, Union, Tuple, Set 
def art_auction_fetch_artwork_price(artwork_name:str, artist:str, platform:str='all') -> str:
	"""
	art_auction_fetch_artwork_price : Fetch the price of a specific artwork on the auction platform.    
	Parameters:
	artwork_name (str): The name of the artwork to be searched.
	artist (str): The artist's name to ensure the precise artwork is fetched.
	platform (str): The platform where the artwork's price should be fetched from.

	Required Parameter = [artwork_name,artist,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def library_search_book(title:str, author:str, platform:str='all') -> str:
	"""
	library_search_book : Search for a specific book in the library.    
	Parameters:
	title (str): The title of the book to be searched.
	author (str): The author of the book to ensure the precise book is fetched.
	platform (str): The library where the book should be fetched from.

	Required Parameter = [title,author,]

	"""
	return 'Success'

tools = [art_auction_fetch_artwork_price, library_search_book]
