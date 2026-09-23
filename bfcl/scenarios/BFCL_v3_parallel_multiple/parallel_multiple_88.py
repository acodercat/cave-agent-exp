from typing import List, Dict, Any, Union, Tuple, Set 
def library_search_book(book_name:str, city:str, availability:bool=None, genre:str='') -> str:
	"""
	library_search_book : Searches for a book in the library within the specified city.    
	Parameters:
	book_name (str): The name of the book to search for.
	city (str): The city to search within.
	availability (bool): If true, search for available copies. If false or omitted, search for any copy regardless of availability. Default false
	genre (str): The genre of the book to filter search (optional).

	Required Parameter = [book_name,city,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def library_reserve_book(book_id:str, branch_id:str, return_date:str='') -> str:
	"""
	library_reserve_book : Reserves a book in the library if available.    
	Parameters:
	book_id (str): The id of the book to reserve.
	branch_id (str): The id of the library branch to reserve from.
	return_date (str): The date the book is to be returned (optional).

	Required Parameter = [book_id,branch_id,]

	"""
	return 'Success'

tools = [library_search_book, library_reserve_book]
