from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_booking_book(city:str, from_date:str, to_date:str, adults:int, children:int, room_type:str='Standard') -> str:
	"""
	hotel_booking_book : Book a hotel room given the city, date, and the number of adults and children.    
	Parameters:
	city (str): The city where the hotel is located.
	from_date (str): The start date of the booking. The format is MM-DD-YYYY.
	to_date (str): The end date of the booking. The format is MM-DD-YYYY.
	adults (int): The number of adults for the booking.
	children (int): The number of children for the booking.
	room_type (str): The type of the room, default is 'Standard'. Options are 'Standard', 'Deluxe', 'Suite'.

	Required Parameter = [city,from_date,to_date,adults,children,]

	"""
	return 'Success'

tools = [hotel_booking_book]
