from dotenv import load_dotenv
load_dotenv()  # loads .env into environment

import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import asyncio
import edge_tts
import subprocess
from dataclasses import dataclass
import argparse
import sys

SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'
GPT_MODEL = 'gpt-4.1'  # or 'gpt-3.5-turbo' if you prefer

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

    def speak(self, text):
        print(f"🔊 {text}")
        self.engine.say(text)
        self.engine.runAndWait()


class EdgeTTSEngine:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.announcement_file_path = "announcement.mp3"

    async def generate_text(self, text):
        communicate = edge_tts.Communicate(text=text, voice="en-US-GuyNeural")
        await communicate.save(self.announcement_file_path)

    def play_mp3_ffplay(self):
        return subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", self.announcement_file_path])

    def speak(self, text):
        print(f"🔊 {text}")
        self.loop.run_until_complete(self.generate_text(text))
        return self.play_mp3_ffplay()


class TriviaGenerator:
    def __init__(self, is_ballet=False, max_words=40):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.previous_trivia = []
        self.is_ballet = is_ballet 
        self.max_words = max_words

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
        #f'Previous trivia were: {". ".join(self.previous_trivia)}',
        return " ".join(prompt_parts)
    
    def generate_trivia(self, title):
        try:
            response = self.client.chat.completions.create(
                model=GPT_MODEL,
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
    args = parser.parse_args()
    is_ballet = args.ballet
    trivia_size = args.trivia_size
    no_title = args.no_title
    no_trivia = args.no_trivia

    engine = EdgeTTSEngine()
    trivia = TriviaGenerator(is_ballet=is_ballet, max_words=trivia_size)
    spotify = Spotify()

    print(f"🎶 Starting Spotify announcer with is_ballet set to {is_ballet}, trivia size set to {trivia_size} words, play title: {not no_title}...")
    
    try:
        while True:
            from requests.exceptions import ReadTimeout
            try:
                spotify_data = spotify.track_info()
                if spotify_data.is_new:
                    name = f'{spotify_data.title} by {spotify_data.artist}' 
                    if not no_title:
                        process_speak_name = engine.speak(spotify_data.title)
                    if not no_trivia:
                        trivia_text = trivia.generate_trivia(name)
                    if not no_title:
                        process_speak_name.wait()
                    if not no_trivia:
                        engine.speak(trivia_text).wait()
            except (ReadTimeout) as e:
                print("Network error:", e)
            except Exception as e:
                print("Unexpected error:", e)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nExiting Spotify announcer...")
        sys.exit(0)

if __name__ == '__main__':
    main()