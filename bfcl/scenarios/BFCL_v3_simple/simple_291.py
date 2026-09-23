from typing import List, Dict, Any, Union, Tuple, Set 
def music_generator_generate_melody(key:str, start_note:str, length:int, tempo:int=None) -> str:
	"""
	music_generator_generate_melody : Generate a melody based on certain musical parameters.    
	Parameters:
	key (str): The key of the melody. E.g., 'C' for C major.
	start_note (str): The first note of the melody, specified in scientific pitch notation. E.g., 'C4'.
	length (int): The number of measures in the melody.
	tempo (int): The tempo of the melody, in beats per minute. Optional parameter. If not specified, defaults to 120.

	Required Parameter = [key,start_note,length,]

	"""
	return 'Success'

tools = [music_generator_generate_melody]
