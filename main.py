from dotenv import load_dotenv
load_dotenv()  # loads .env into environment

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import asyncio
import edge_tts
import subprocess
from dataclasses import dataclass
import argparse
import sys
import tempfile
from requests.exceptions import ReadTimeout

SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'

@dataclass
class SpotifyData:
    """Data class to hold Spotify track information."""
    is_new: bool
    title: str
    artist: str

class Spotify:
    def __init__(self):
        self.client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SPOTIFY_SCOPE))
        self.last_track_id = None
    
    def track_info(self) -> SpotifyData:
        is_new = False
        title = None
        artist = None
        playback = self.client.current_playback()
        if playback and playback['is_playing']:
            track = playback['item']
            if track:
                is_new = track['id'] != self.last_track_id
                self.last_track_id = track['id']
                title = track['name']
                artist = ', '.join(a['name'] for a in track['artists'])
        return SpotifyData(is_new, title, artist)
        
    def current_playback(self):
        return self.client.current_playback()

    def pause(self):
        return self.client.pause_playback()

    def resume(self):
        return self.client.start_playback()


class TTSEngine:
    def __init__(self):
        import pyttsx3
        self.engine = pyttsx3.init()

    async def speak(self, text):
        print(f"🔊 {text}")
        self.engine.say(text)
        self.engine.runAndWait()


class EdgeTTSEngine:
    def __init__(self, volume=0.5):
        self.volume = volume

    async def generate_text_to_file(self, text, file_path):
        communicate = edge_tts.Communicate(text=text, voice="en-US-GuyNeural")
        await communicate.save(file_path)

    async def speak(self, text):
        print(f"🔊 {text}")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
            await self.generate_text_to_file(text, tmp.name)
            process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(self.volume * 100)), tmp.name]
            )
            process.wait()


class TriviaGenerator:
    def __init__(self, is_ballet=False, max_words=40, use_previous_trivia=False, gpt_model='gpt-4.1'):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.previous_trivia = []
        self.is_ballet = is_ballet 
        self.max_words = max_words
        self.use_previous_trivia = use_previous_trivia
        self.gpt_model = gpt_model 

    def generate_prompt(self, title):
        prompt_parts = []
        if self.is_ballet:
            prompt_parts.append(f'Give a short description (max. {self.max_words} words) about the following song thereby embedding them into the full music piece.')
            prompt_parts.append('Where in the story is it happening? What would happen before, e.g., in a ballet?')
            prompt_parts.append('Assume the user has understood the events in the ballet so far.')
        else:
            prompt_parts.append(f'Give a short description (max. {self.max_words} words) about the following song thereby embedding them into the given genre.')
            prompt_parts.append(f'Maybe add some details about the song, its creator, historical context or other trivia.')
            prompt_parts.append(f'If you do not know the song, its fine, just say nothing.')
        prompt_parts.append(f'The song is: {title}')
        if self.use_previous_trivia:
            prompt_parts.append('If it is useful to backreference previous trivia, do so.')
            prompt_parts.append(f'Previous trivia were: {". ".join(self.previous_trivia)}')
        return " ".join(prompt_parts)
    
    def generate_trivia(self, title):
        try:
            response = self.client.chat.completions.create(
                model=self.gpt_model,
                messages=[{"role": "user", "content": self.generate_prompt(title)}]
            )
            trivia = response.choices[0].message.content.strip()
            self.previous_trivia.append(trivia)
            return trivia
        except Exception as e:
            print("GPT error:", e)
            return ""


def main():
    parser = argparse.ArgumentParser(description="Spotify Announcer CLI")
    parser.add_argument(
        '--ballet', 
        action='store_true', 
        help='Set the is_ballet parameter to True'
    )
    parser.add_argument(
        '--trivia-size',
        type=int,
        default=40,
        help='Maximum number of words for the trivia (default: 40)'
    )
    parser.add_argument(
        '--no-title',
        action='store_true',
        help='Do not play the title before the trivia'
    )
    parser.add_argument(
        '--no-trivia',
        action='store_true',
        help='Do not play any trivia'
    )
    parser.add_argument(
        '--use-previous-trivia',
        action='store_true',
        help='Include previous trivia in the prompt for generating new trivia'
    )
    parser.add_argument(
        '--tts',
        choices=['edge', 'pyttsx3'],
        default='edge',
        help='Choose TTS engine: "edge" (default) or "pyttsx3"'
    )
    parser.add_argument(
        '--gpt-model',
        choices=['gpt-4.1', 'gpt-3.5-turbo'],
        default='gpt-4.1',
        help='Choose OpenAI GPT model: "gpt-4.1" (default) or "gpt-3.5-turbo"'
    )
    parser.add_argument(
        '--volume',
        type=float,
        default=0.5,
        help='Set the TTS volume (0.0 to 1.0, default: 0.5)'
    )
    args = parser.parse_args()
    is_ballet = args.ballet
    trivia_size = args.trivia_size
    no_title = args.no_title
    no_trivia = args.no_trivia
    tts_choice = args.tts
    use_previous_trivia = args.use_previous_trivia
    gpt_model = args.gpt_model
    volume = args.volume

    engine = EdgeTTSEngine(volume=volume) if tts_choice == 'edge' else TTSEngine()
    trivia = TriviaGenerator(is_ballet=is_ballet, max_words=trivia_size, use_previous_trivia=use_previous_trivia, gpt_model=gpt_model)
    spotify = Spotify()

    print(f"🎶 Starting Spotify announcer with is_ballet set to {is_ballet}, trivia size set to {trivia_size} words, play title: {not no_title}, TTS engine: {tts_choice}, GPT model: {gpt_model}...")

    async def announcer_loop():
        while True:
            try:
                spotify_data = spotify.track_info()
                if spotify_data.is_new:
                    name = f'{spotify_data.title} by {spotify_data.artist}' 
                    if not no_title:
                        await engine.speak(spotify_data.title)
                    if not no_trivia:
                        trivia_text = trivia.generate_trivia(name)
                        await engine.speak(trivia_text)
            except (ReadTimeout) as e:
                print("Network error:", e)
            await asyncio.sleep(5)

    try:
        asyncio.run(announcer_loop())
    except KeyboardInterrupt:
        print("\nExiting Spotify announcer...")
        sys.exit(0)

if __name__ == '__main__':
    main()