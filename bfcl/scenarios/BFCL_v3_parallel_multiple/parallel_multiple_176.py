from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_bmi(weight:int, height:int, system:str=None) -> str:
	"""
	calculate_bmi : Calculate the Body Mass Index (BMI) for a person based on their weight and height.    
	Parameters:
	weight (int): The weight of the person in kilograms.
	height (int): The height of the person in centimeters.
	system (str): The system of units to be used, 'metric' or 'imperial'. Default is 'metric'.

	Required Parameter = [weight,height,]

	"""
	return 'Success'

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

from typing import List, Dict, Any, Union, Tuple, Set 
def sentiment_analysis(text:str, language:str) -> str:
	"""
	sentiment_analysis : Perform sentiment analysis on a given piece of text.    
	Parameters:
	text (str): The text on which to perform sentiment analysis.
	language (str): The language in which the text is written.

	Required Parameter = [text,language,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def get_time_difference(place1:str, place2:str) -> str:
	"""
	get_time_difference : Get the time difference between two places.    
	Parameters:
	place1 (str): The first place for time difference.
	place2 (str): The second place for time difference.

	Required Parameter = [place1,place2,]

	"""
	return 'Success'

tools = [calculate_bmi, hotel_booking, sentiment_analysis, get_time_difference]
