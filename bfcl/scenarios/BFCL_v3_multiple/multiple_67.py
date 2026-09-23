from typing import List, Dict, Any, Union, Tuple, Set 
def translate(text:str, source_language:str, target_language:str) -> str:
	"""
	translate : Translate text from a specified source language to a specified target language.    
	Parameters:
	text (str): The text to be translated.
	source_language (str): The language the text is currently in.
	target_language (str): The language the text will be translated to.

	Required Parameter = [text,source_language,target_language,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def sentiment_analysis(text:str) -> str:
	"""
	sentiment_analysis : Analyze the sentiment of a specified text.    
	Parameters:
	text (str): The text whose sentiment is to be analyzed.

	Required Parameter = [text,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def word_count(text:str) -> str:
	"""
	word_count : Count the number of words in the given text.    
	Parameters:
	text (str): The text that the number of words is to be calculated.

	Required Parameter = [text,]

	"""
	return 'Success'

tools = [translate, sentiment_analysis, word_count]
