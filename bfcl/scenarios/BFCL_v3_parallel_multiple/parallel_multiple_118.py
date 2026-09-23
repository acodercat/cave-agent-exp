from typing import List, Dict, Any, Union, Tuple, Set 
def audio_generate(frequency:int, amplitude:float, duration:float=None) -> str:
	"""
	audio_generate : Generate an audio signal given a frequency, amplitude, and duration.    
	Parameters:
	frequency (int): Frequency of the audio signal in Hz.
	amplitude (float): Amplitude of the audio signal.
	duration (float): Duration of the audio signal in seconds. Default is 1 second if not specified.

	Required Parameter = [frequency,amplitude,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def music_generate(key:str, tempo:int, time_signature:str=None) -> str:
	"""
	music_generate : Generate a piece of music given a key, tempo, and time signature.    
	Parameters:
	key (str): The key of the piece, e.g., C Major.
	tempo (int): Tempo of the piece in beats per minute.
	time_signature (str): Time signature of the piece, e.g., 4/4. Default is '4/4' if not specified.

	Required Parameter = [key,tempo,]

	"""
	return 'Success'

tools = [audio_generate, music_generate]
