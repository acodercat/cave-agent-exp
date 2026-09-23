from typing import List, Dict, Any, Union, Tuple, Set 
def light_travel_time(distance_in_light_years:int, speed_of_light:int=None) -> str:
	"""
	light_travel_time : Calculate the time taken for light to travel from a celestial body to another.    
	Parameters:
	distance_in_light_years (int): The distance between the two celestial bodies in light years.
	speed_of_light (int): The speed of light in vacuum, in m/s. Default value is 299792458 m/s.

	Required Parameter = [distance_in_light_years,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def safeway_order(location:str, items:List[str], quantity:List[int]) -> str:
	"""
	safeway_order : Order specified items from a Safeway location.    
	Parameters:
	location (str): The location of the Safeway store, e.g. Palo Alto, CA.
	items (List[str]): List of items to order.
	quantity (List[int]): Quantity of each item in the order list.

	Required Parameter = [location,items,quantity,]

	"""
	return 'Success'

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

from typing import List, Dict, Any, Union, Tuple, Set 
def latest_exchange_rate(source_currency:str, target_currency:str, amount:float=None) -> str:
	"""
	latest_exchange_rate : Retrieve the latest exchange rate between two specified currencies.    
	Parameters:
	source_currency (str): The currency you are converting from.
	target_currency (str): The currency you are converting to.
	amount (float): The amount to be converted. If omitted, exchange rate of 1 unit source currency is given. Default is 1.

	Required Parameter = [source_currency,target_currency,]

	"""
	return 'Success'

tools = [light_travel_time, safeway_order, book_hotel, latest_exchange_rate]
