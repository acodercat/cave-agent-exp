from typing import List, Dict, Any, Union, Tuple, Set 
def flight_book(test_from:str, to:str, airlines:str) -> str:
	"""
	flight_book : Book a flight for a specific route and airlines    
	Parameters:
	test_from (str): The departure city in full name.
	to (str): The arrival city in full name.
	airlines (str): The preferred airline.

	Required Parameter = [test_from,to,airlines,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_book(location:str, nights:int) -> str:
	"""
	hotel_book : Book a hotel for a specific location for the number of nights    
	Parameters:
	location (str): The city where the hotel is located.
	nights (int): Number of nights for the stay.

	Required Parameter = [location,nights,]

	"""
	return 'Success'

tools = [flight_book, hotel_book]
