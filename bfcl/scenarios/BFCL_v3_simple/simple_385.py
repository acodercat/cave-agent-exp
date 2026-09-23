from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_bookings_book_room(location:str, room_type:str, check_in_date:str, no_of_nights:int, no_of_rooms:int=1) -> str:
	"""
	hotel_bookings_book_room : Book a hotel room based on specific criteria like location, room type, and check-in and check-out dates.    
	Parameters:
	location (str): The city and state where you want to book the hotel, e.g. Los Angeles, CA
	room_type (str): Preferred type of room in the hotel, e.g. king size, queen size, deluxe, suite etc.
	check_in_date (str): Check-in date for the hotel. Format - DD-MM-YYYY.
	no_of_nights (int): Number of nights for the stay.
	no_of_rooms (int): Number of rooms to book. Default is 1.

	Required Parameter = [location,room_type,check_in_date,no_of_nights,]

	"""
	return 'Success'

tools = [hotel_bookings_book_room]
