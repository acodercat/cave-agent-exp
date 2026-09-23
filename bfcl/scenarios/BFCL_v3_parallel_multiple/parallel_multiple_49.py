from typing import List, Dict, Any, Union, Tuple, Set 
def melody_generator(note_sequence:List[str], instrument:str='Bass') -> str:
	"""
	melody_generator : Create a melody based on specified notes.    
	Parameters:
	note_sequence (List[str]): The sequence of notes for the melody.
	instrument (str): The instrument to play the melody, e.g. Bass.

	Required Parameter = [note_sequence,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def beat_generator(genre:str, bpm:int, scale:str='Major') -> str:
	"""
	beat_generator : Generate a beat based on specified genre and beats per minute.    
	Parameters:
	genre (str): The genre of the beat, e.g. Hip Hop.
	bpm (int): The beats per minute of the beat.
	scale (str): The scale for the beat, e.g. Major.

	Required Parameter = [genre,bpm,]

	"""
	return 'Success'

tools = [melody_generator, beat_generator]
