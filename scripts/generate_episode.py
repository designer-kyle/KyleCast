import os
import openai
import glob
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# --- Config ---
MP3_DIR = "mp3"
FEED_PATH = "kylecast.xml"
AUTHOR = "Kyle Inabinette"
SHOW_URL = "https://designer-kyle.github.io/KyleCast/"
SHOW_TITLE = "KyleCast"

# --- Setup OpenAI ---
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Utility: Format pubDate ---
def format_rfc2822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

# --- Load feed ---
tree = ET.parse(FEED_PATH)
root = tree.getroot()
channel = root.find("channel")

# --- Find all .mp3 files not already in the feed ---
existing_guids = {item.find("guid").text for item in channel.findall("item")}
new_files = [f for f in glob.glob(f"{MP3_DIR}/*.mp3") if Path(f).stem not in existing_guids]

for file_path in new_files:
    filename = Path(file_path).name
    guid = Path(file_path).stem
    print(f"Transcribing {filename}...")

    # Transcribe
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text"
        )

    print("Generating episode metadata...")
    gpt = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You're a podcast producer. Return a concise title and 1-sentence description of the episode transcript."},
            {"role": "user", "content": transcript}
        ]
    )
    reply = gpt.choices[0].message.content.strip().split("\n", 1)
    title = reply[0].strip()
    description = reply[1].strip() if len(reply) > 1 else "No description."

    # File metadata
    size = os.path.getsize(file_path)
    pub_date = format_rfc2822(datetime.utcnow())
    url = f"{SHOW_URL}mp3/{filename}"

    # --- Create new <item> ---
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "enclosure", url=url, length=str(size), type="audio/mpeg")
    ET.SubElement(item, "guid").text = guid
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "author").text = AUTHOR
    ET.SubElement(item, "link").text = url

    # Insert at top of channel
    channel.insert(0, item)
    print(f"✅ Added {title} to feed.")

# --- Save feed ---
tree.write(FEED_PATH, encoding="UTF-8", xml_declaration=True)
