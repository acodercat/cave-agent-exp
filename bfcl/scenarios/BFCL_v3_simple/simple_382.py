from typing import List, Dict, Any, Union, Tuple, Set 
def book_hotel(hotel_name:str, location:str, room_type:str, start_date:str, nights:int) -> str:
	"""
	book_hotel : Book a room of specified type for a particular number of nights at a specific hotel, starting from a specified date.    
	Parameters:
	hotel_name (str): The name of the hotel.
	location (str): The city in which the hotel is located.
	room_type (str): The type of room to be booked.
	start_date (str): The start date for the booking.
	nights (int): The number of nights for which the booking is to be made.

	Required Parameter = [hotel_name,location,room_type,start_date,nights,]

	"""
	return 'Success'

tools = [book_hotel]
