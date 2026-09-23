from typing import List, Dict, Any, Union, Tuple, Set 
def music_generator_generate_scale_progression(key:str, tempo:int, duration:int, scale_type:str='major') -> str:
	"""
	music_generator_generate_scale_progression : Generate a music scale progression in a specific key with a given tempo and duration.    
	Parameters:
	key (str): The key in which to generate the scale progression.
	tempo (int): The tempo of the scale progression in BPM.
	duration (int): The duration of each note in beats.
	scale_type (str): The type of scale to generate. Defaults to 'major'.

	Required Parameter = [key,tempo,duration,]

	"""
	return 'Success'

tools = [music_generator_generate_scale_progression]
