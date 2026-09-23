from typing import List, Dict, Any, Union, Tuple, Set 
def car_rental(location:str, days:int, car_type:str, pick_up:str=None) -> str:
	"""
	car_rental : Rent a car at the specified location for a specific number of days    
	Parameters:
	location (str): Location of the car rental.
	days (int): Number of days for which to rent the car.
	car_type (str): Type of the car to rent.
	pick_up (str): Location of where to pick up the car. Default ''

	Required Parameter = [location,days,car_type,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_book(location:str, roomType:str, nights:int, additional_services:List[str]=None) -> str:
	"""
	hotel_book : Book a hotel room given the location, room type, and number of nights and additional services    
	Parameters:
	location (str): Location of the hotel.
	roomType (str): Type of the room to be booked.
	nights (int): Number of nights to book the room for.
	additional_services (List[str]): Additional services to be added. Default empty array

	Required Parameter = [location,roomType,nights,]

	"""
	return 'Success'

tools = [car_rental, hotel_book]
