from typing import List, Dict, Any, Union, Tuple, Set 
def book_hotel(hotel_name:str, location:str, room_type:str, start_date:str, stay_duration:int, view:str='No preference') -> str:
	"""
	book_hotel : Book a room in a specific hotel with particular preferences    
	Parameters:
	hotel_name (str): The name of the hotel.
	location (str): The location of the hotel.
	room_type (str): The type of room preferred.
	start_date (str): The starting date of the stay in format MM-DD-YYYY.
	stay_duration (int): The duration of the stay in days.
	view (str): The preferred view from the room, can be ignored if no preference. If none provided, assumes no preference.

	Required Parameter = [hotel_name,location,room_type,start_date,stay_duration,]

	"""
	return 'Success'

tools = [book_hotel]
