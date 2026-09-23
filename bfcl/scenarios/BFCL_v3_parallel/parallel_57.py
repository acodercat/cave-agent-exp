from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_booking_book(hotel_name:str, location:str, check_in:str, check_out:str, adults:int, children:int) -> str:
	"""
	hotel_booking_book : Book a hotel room at the specified location for the specified number of adults and children.    
	Parameters:
	hotel_name (str): The name of the hotel.
	location (str): The city where the hotel is located.
	check_in (str): The check-in date in the format yyyy-mm-dd.
	check_out (str): The check-out date in the format yyyy-mm-dd.
	adults (int): The number of adults for the booking.
	children (int): The number of children for the booking.

	Required Parameter = [hotel_name,location,check_in,check_out,adults,children,]

	"""
	return 'Success'

tools = [hotel_booking_book]
