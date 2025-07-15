# Spotify Song Announcer 

A CLI tool that announces the currently playing Spotify track and provides trivia using OpenAI and text-to-speech (TTS).

## Features

- Announces the current Spotify track using TTS (Edge or pyttsx3).
- Generates short trivia about the track using OpenAI GPT.
- Supports ballet-specific trivia mode.
- Optionally includes previous trivia for context.
- CLI switches for customizing behavior.

## Requirements

- Python 3.8+
- [Spotify Developer credentials](https://developer.spotify.com/)
- OpenAI API key
- Python packages: `spotipy`, `openai`, `python-dotenv`, `edge-tts`, `pyttsx3`, `requests`, `pydub`, `simpleaudio`

## Installation

The recommended way is to install with [pipx](https://pypa.github.io/pipx/):

```bash
pipx install .
```

## Setup

1. Create a `.env` file with your credentials:
    ```
    SPOTIPY_CLIENT_ID=your_spotify_client_id
    SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
    SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
    OPENAI_API_KEY=your_openai_api_key
    ```

## Usage

```bash
spotify-announcer [options]
```

### Options

- `--ballet`  
  Enable ballet-specific trivia mode.

- `--trivia-size N`  
  Set maximum number of words for trivia (default: 40).

- `--no-title`  
  Do not play the title before the trivia.

- `--no-trivia`  
  Do not play any trivia.

- `--use-previous-trivia`  
  Include previous trivia in the prompt for generating new trivia.

- `--tts edge|pyttsx3`  
  Choose TTS engine: `edge` (default) or `pyttsx3`.

- `--gpt-model gpt-4.1|gpt-3.5-turbo`  
  Choose OpenAI GPT model.

- `--volume FLOAT`  
  Set the TTS volume (0.0 to 1.0, default: 0.5).

## Example

```bash
spotify-announcer --ballet --trivia-size 30 --tts pyttsx3
```

## License

MIT