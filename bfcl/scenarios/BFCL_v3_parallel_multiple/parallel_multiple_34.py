from typing import List, Dict, Any, Union, Tuple, Set 
def get_current_time(location:str) -> str:
	"""
	get_current_time : Fetches current time for a given location    
	Parameters:
	location (str): The location for which to fetch current time

	Required Parameter = [location,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def translate_text(text:str, from_lang:str, to_lang:str) -> str:
	"""
	translate_text : Translates a given text from one language to another    
	Parameters:
	text (str): The text that needs to be translated
	from_lang (str): The source language from which to translate
	to_lang (str): The target language to which to translate

	Required Parameter = [text,from_lang,to_lang,]

	"""
	return 'Success'

tools = [get_current_time, translate_text]
