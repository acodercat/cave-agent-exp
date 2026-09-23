from typing import List, Dict, Any, Union, Tuple, Set 
def hotel_booking(hotel_name:str, location:str, start_date:str, end_date:str, rooms:int=1) -> str:
	"""
	hotel_booking : Books a hotel room for a specific date range.    
	Parameters:
	hotel_name (str): The name of the hotel.
	location (str): The city and state, e.g. New York, NY.
	start_date (str): The start date of the reservation. Use format 'YYYY-MM-DD'.
	end_date (str): The end date of the reservation. Use format 'YYYY-MM-DD'.
	rooms (int): The number of rooms to reserve.

	Required Parameter = [hotel_name,location,start_date,end_date,]

	"""
	return 'Success'

tools = [hotel_booking]
