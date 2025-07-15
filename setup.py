from setuptools import setup

setup(
    name="spotify-announcer",
    version="0.1.0",
    py_modules=["main"],
    install_requires=[
        "python-dotenv",
        "spotipy",
        "openai",
        "edge-tts",
        "pyttsx3",
        "requests",
        "pydub",
        "simpleaudio",
    ],
    entry_points={
        "console_scripts": [
            "spotify-announcer = main:main",
        ],
    },
)