from typing import List, Dict, Any, Union, Tuple, Set 
def get_news(topic:str, quantity:int, region:str=None) -> str:
	"""
	get_news : Fetches the latest news on a specific topic.    
	Parameters:
	topic (str): The subject for the news topic.
	quantity (int): Number of articles to fetch.
	region (str): The geographical region for the news (Optional). default is 'USA'

	Required Parameter = [topic,quantity,]

	"""
	return 'Success'

tools = [get_news]
