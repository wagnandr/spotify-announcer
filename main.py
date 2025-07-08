from dotenv import load_dotenv
load_dotenv()  # loads .env into environment

import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import asyncio
import edge_tts
import subprocess

SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'

# Spotify client
class SpotifyData:
    def __init__(self, is_new, title, artist):
        self.is_new = is_new 
        self.title = title
        self.artist = artist

class Spotify:
    def __init__(self):
        self.client = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SPOTIFY_SCOPE))
        self.last_track_id = None
    
    def track_info(self):
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


class ETTSEngine:
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
    def __init__(self, is_ballet=False):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.previous_trivia = []
        self.is_ballet = is_ballet 

    def generate_prompt(self, title):
        prompt_parts = [
            'Give a short description (max. 40 words) about the following song thereby embedding them into the full music piece.',
        ]
        if self.is_ballet:
            prompt_parts.append('Where in the story is it happening? What would happen before, e.g., in a ballet?')
            prompt_parts.append('Assume the user has understood the events in the ballet so far.')
        prompt_parts.append(f'The song is: {title}')
        #f'Previous trivia were: {". ".join(self.previous_trivia)}',
        return " ".join(prompt_parts)
    
    def generate_trivia(self, title):
        try:
            response = self.client.chat.completions.create(
                #model="gpt-3.5-turbo",
                model="gpt-4.1",
                messages=[{"role": "user", "content": self.generate_prompt(title)}]
            )
            trivia = response.choices[0].message.content.strip()
            self.previous_trivia.append(trivia)
            return trivia
        except Exception as e:
            print("GPT error:", e)
            return ""


engine = ETTSEngine()
trivia = TriviaGenerator(is_ballet=True)
spotify = Spotify()


def main_loop():
    while True:
        spotify_data = spotify.track_info()
        if spotify_data.is_new:
            name = f'{spotify_data.title} by {spotify_data.artist}' 
            process_speak_name = engine.speak(spotify_data.title)
            trivia_text = trivia.generate_trivia(name)
            process_speak_name.wait()
            engine.speak(trivia_text).wait()
        time.sleep(5)

if __name__ == '__main__':
    print("🎶 Starting Spotify announcer...")
    main_loop()