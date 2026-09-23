from typing import List, Dict, Any, Union, Tuple, Set 
def social_media_analytics_most_followed(topic:str, sub_topics:List[str]=None, region:str=None) -> str:
	"""
	social_media_analytics_most_followed : Find the most followed Twitter user related to certain topics.    
	Parameters:
	topic (str): The main topic of interest.
	sub_topics (List[str]): Sub-topics related to main topic, Optional. Default is an empty list.
	region (str): Region of interest for twitter search, Optional. Default is 'global'.

	Required Parameter = [topic,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_probability(total_outcomes:int, favorable_outcomes:int, round_to:int=2) -> str:
	"""
	calculate_probability : Calculate the probability of an event.    
	Parameters:
	total_outcomes (int): Total number of possible outcomes.
	favorable_outcomes (int): Number of outcomes considered as 'successful'.
	round_to (int): Number of decimal places to round the result to.

	Required Parameter = [total_outcomes,favorable_outcomes,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def concert_info_get(location:str, date:str, genre:str) -> str:
	"""
	concert_info_get : Retrieve information about concerts based on specific genre, location and date.    
	Parameters:
	location (str): The city where the concert will take place.
	date (str): Time frame to get the concert for.
	genre (str): Genre of the concert.

	Required Parameter = [location,date,genre,]

	"""
	return 'Success'

tools = [social_media_analytics_most_followed, calculate_probability, concert_info_get]
