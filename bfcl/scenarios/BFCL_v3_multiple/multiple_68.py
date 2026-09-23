from typing import List, Dict, Any, Union, Tuple, Set 
def library_search_books(location:str, genre:str, title:str=None) -> str:
	"""
	library_search_books : Search for a book in a given library with optional parameters    
	Parameters:
	location (str): Name or city of library
	genre (str): Genre of the book
	title (str): Title of the book. Default ''

	Required Parameter = [location,genre,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def google_books_search(genre:str, title:str=None) -> str:
	"""
	google_books_search : Search for a book in the Google Books library with optional parameters    
	Parameters:
	genre (str): Genre of the book
	title (str): Title of the book. Default ''

	Required Parameter = [genre,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def openlibrary_books_search(genre:str, title:str=None) -> str:
	"""
	openlibrary_books_search : Search for a book in the Open Library with optional parameters    
	Parameters:
	genre (str): Genre of the book
	title (str): Title of the book. Default ''

	Required Parameter = [genre,]

	"""
	return 'Success'

tools = [library_search_books, google_books_search, openlibrary_books_search]
