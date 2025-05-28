# === Podcast Episode Generator (OpenAI + GitHub Actions Compatible) ===

import os
import sys
import openai
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# === CONFIGURATION ===
FEED_PATH = "kylecast.xml"
MP3_DIR = "mp3"
OPENAI_MODEL = "whisper-1"
GUID_PREFIX = "auto-episode-"
BASE_URL = "https://designer-kyle.github.io/kylecast"

# === HELPERS ===
def get_newest_mp3():
    mp3_files = sorted(Path(MP3_DIR).glob("*.mp3"), key=os.path.getmtime, reverse=True)
    return mp3_files[0] if mp3_files else None

def transcribe_audio(file_path):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(
            model=OPENAI_MODEL,
            file=audio_file,
            response_format="text"
        )
    return transcript.strip()

def parse_title_and_description(transcript):
    lines = transcript.split(". ")
    title = lines[0].strip()[:80] if lines else "Untitled Episode"
    description = transcript[:400] + "..." if len(transcript) > 400 else transcript
    return title, description

def load_or_create_feed():
    if not os.path.exists(FEED_PATH):
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = "KyleCast"
        ET.SubElement(channel, "link").text = f"{BASE_URL}/{FEED_PATH}"
        ET.SubElement(channel, "description").text = "A private feed of strategy, voice notes, and podcast drafts by Kyle."
        ET.SubElement(channel, "language").text = "en-us"
        ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        return ET.ElementTree(root)
    return ET.parse(FEED_PATH)

def add_episode_to_feed(tree, file_path, title, description):
    channel = tree.getroot().find("channel")
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "enclosure", {
        "url": f"{BASE_URL}/{file_path.as_posix()}",
        "length": str(file_path.stat().st_size),
        "type": "audio/mpeg"
    })
    guid = f"{GUID_PREFIX}{file_path.stem}"
    ET.SubElement(item, "guid").text = guid
    pub_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    ET.SubElement(item, "pubDate").text = pub_date
    channel.insert(0, item)
    channel.find("lastBuildDate").text = pub_date

# === MAIN ===
def main():
    mp3_path = get_newest_mp3()
    if not mp3_path:
        print("No new .mp3 files found.")
        sys.exit(0)

    print(f"Processing: {mp3_path}")
    transcript = transcribe_audio(mp3_path)
    title, description = parse_title_and_description(transcript)

    tree = load_or_create_feed()
    add_episode_to_feed(tree, mp3_path, title, description)
    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
    print(f"✅ Feed updated with: {title}")

if __name__ == "__main__":
    main()
