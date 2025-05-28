import os
import openai
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import wave
import contextlib

openai.api_key = os.getenv("OPENAI_API_KEY")

MP3_DIR = Path("mp3")
FEED_PATH = Path("kylecast.xml")
RAW_URL_PREFIX = "https://raw.githubusercontent.com/designer-kyle/KyleCast/main/mp3"

def get_file_size(path):
    return str(path.stat().st_size)

def get_audio_duration(path):
    with contextlib.closing(wave.open(str(path), 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
    total = timedelta(seconds=int(duration))
    return str(total)

def already_in_feed(filename):
    with open(FEED_PATH, "r") as f:
        return filename in f.read()

def transcribe(mp3_path):
    print(f"Transcribing {mp3_path.name}...")
    with mp3_path.open("rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript["text"]

def extract_metadata(transcript):
    print("Extracting metadata with GPT...")
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a podcast assistant. Based on the transcript, generate a suitable episode title, a one-sentence summary, and 3-5 comma-separated tags."},
            {"role": "user", "content": transcript}
        ]
    )
    return response.choices[0].message.content.strip().split("\n")

def create_item_xml(file_name, file_url, length, pub_date, title, description, duration):
    return f"""
    <item>
      <title>{title}</title>
      <itunes:summary>{description}</itunes:summary>
      <enclosure url=\"{file_url}\" length=\"{length}\" type=\"audio/mpeg\"/>
      <guid>{file_name}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>
    """

def insert_into_feed(xml_snippet):
    with open(FEED_PATH, "r") as f:
        contents = f.read()
    updated = contents.replace("</channel>", xml_snippet + "\n</channel>")
    with open(FEED_PATH, "w") as f:
        f.write(updated)

def main():
    for mp3_path in MP3_DIR.glob("*.mp3"):
        if already_in_feed(mp3_path.name):
            print(f"Skipping {mp3_path.name} — already in feed.")
            continue

        transcript = transcribe(mp3_path)
        title, description, *tags = extract_metadata(transcript)

        file_url = f"{RAW_URL_PREFIX}/{mp3_path.name.replace(' ', '%20')}"
        file_length = get_file_size(mp3_path)
        pub_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        duration = get_audio_duration(mp3_path)

        item_xml = create_item_xml(mp3_path.name, file_url, file_length, pub_date, title, description, duration)
        insert_into_feed(item_xml)
        print(f"✅ Added {title} to feed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--rich', action='store_true', help='Use enhanced metadata generation')
    args = parser.parse_args()
    main()
