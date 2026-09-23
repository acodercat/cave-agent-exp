from typing import List, Dict, Any, Union, Tuple, Set 
def music_generate(key:str, tempo:int, time_signature:str=None) -> str:
	"""
	music_generate : Generate a piece of music given a key, tempo, and time signature.    
	Parameters:
	key (str): The key of the piece, e.g., C Major.
	tempo (int): Tempo of the piece in beats per minute.
	time_signature (str): Time signature of the piece, e.g., 4/4. Default '4/4'

	Required Parameter = [key,tempo,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def audio_generate(frequency:float, amplitude:float, duration:int=None) -> str:
	"""
	audio_generate : Generate an audio signal given a frequency, amplitude, and duration.    
	Parameters:
	frequency (float): Frequency of the audio signal in Hz.
	amplitude (float): Amplitude of the audio signal.
	duration (int): Duration of the audio signal in seconds. Default 1

	Required Parameter = [frequency,amplitude,]

	"""
	return 'Success'

tools = [music_generate, audio_generate]
