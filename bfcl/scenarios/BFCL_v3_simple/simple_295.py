from typing import List, Dict, Any, Union, Tuple, Set 
def get_song_lyrics(song_title:str, artist_name:str, lang:str=None) -> str:
	"""
	get_song_lyrics : Retrieve the lyrics of a song based on the artist's name and song title.    
	Parameters:
	song_title (str): The title of the song.
	artist_name (str): The name of the artist who performed the song.
	lang (str): The language of the lyrics. Default is English.

	Required Parameter = [song_title,artist_name,]

	"""
	return 'Success'

tools = [get_song_lyrics]
