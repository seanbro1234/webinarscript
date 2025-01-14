import streamlit as st
import openai
import requests
import subprocess
import os

# API Keys
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]  # Ensure this is set in Streamlit Cloud secrets
ELEVEN_LABS_API_KEY = st.secrets["ELEVEN_LABS_API_KEY"]  # Ensure this is set in Streamlit Cloud secrets
ELEVEN_LABS_VOICE_ID = "Fahco4VZzobUeiPqni1S"

# Display logo
st.image("https://datalawonline.co.uk/uploads/images/f-b-screen.png", width=200)
st.title("📄 Script Processor with Audio and Video Generation")

# Helper functions
def generate_section_content(chunk, notes, api_key):
    """
    Generates detailed content for a script section using OpenAI.
    Expands on the provided `chunk` and incorporates `notes`.
    """
    openai.api_key = api_key
    prompt = f"""
    You are assisting in creating a polished and engaging webinar script. The script should read as a single, continuous narrative with a professional and conversational tone.

    Expand on the following section:
    {chunk}

    Notes to incorporate:
    {notes}

    Guidelines:
    - Provide clear, detailed explanations and examples.
    - Ensure the section flows logically and connects to other parts of the script.
    - Avoid repeating the input text verbatim.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a scriptwriting assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        # Debugging OpenAI response
        st.write("DEBUG - OpenAI API Response:", response)
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return f"Error generating content: {e}"

def generate_audio_from_text(text, api_key, voice_id):
    """Converts text to speech using Eleven Labs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Content-Type": "application/json", "xi-api-key": api_key}
    payload = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to generate audio: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error during audio generation: {e}")
        return None

def get_audio_duration(audio_path):
    """Gets the duration of an audio file using FFmpeg."""
    try:
        result = subprocess.run(
            ["ffprobe", "-i", audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        st.error(f"Error retrieving audio duration: {e}")
        return None

# Main UI Logic
st.write("### Script Input")
introduction = st.text_area("Introduction", placeholder="Write your introduction here...", height=100)
if "chunks" not in st.session_state:
    st.session_state["chunks"] = [{"chunk": "", "notes": ""}]

def add_section():
    st.session_state["chunks"].append({"chunk": "", "notes": ""})

for i, section in enumerate(st.session_state["chunks"]):
    with st.expander(f"Webinar Section {i + 1}", expanded=True):
        section["chunk"] = st.text_area(f"Content for Section {i + 1}", key=f"chunk_{i}", value=section["chunk"])
        section["notes"] = st.text_area(f"Notes for Section {i + 1}", key=f"notes_{i}", value=section["notes"])

if st.button("➕ Add Section"):
    add_section()

conclusion = st.text_area("Conclusion", placeholder="Write your conclusion here...", height=100)

# Generate Script Button
if st.button("📜 Generate Script"):
    with st.spinner("Generating script..."):
        full_script = introduction + "\n\n"
        for section in st.session_state["chunks"]:
            content = generate_section_content(section["chunk"], section["notes"], OPENAI_API_KEY)
            # Debugging generated content
            st.write("DEBUG - Generated Content:", content)
            full_script += content + "\n\n"
        full_script += conclusion
        st.session_state["final_script"] = full_script
        st.success("Script generated!")

# Generate Audio Button
if "final_script" in st.session_state:
    st.write("### Review and Edit Script")
    script = st.text_area("Edit your script here:", value=st.session_state["final_script"], height=300)
    st.session_state["final_script"] = script

    if st.button("🔊 Generate Audio"):
        with st.spinner("Generating audio..."):
            audio = generate_audio_from_text(script, ELEVEN_LABS_API_KEY, ELEVEN_LABS_VOICE_ID)
            if audio:
                audio_file = "output_audio.mp3"
                with open(audio_file, "wb") as f:
                    f.write(audio)
                st.session_state["audio_path"] = audio_file
                st.audio(audio_file)
                st.success("Audio generated!")

# Debugging Secrets (Optional - Remove Before Making Public)
st.write("DEBUG - OPENAI_API_KEY:", st.secrets.get("OPENAI_API_KEY", "NOT FOUND"))
st.write("DEBUG - ELEVEN_LABS_API_KEY:", st.secrets.get("ELEVEN_LABS_API_KEY", "NOT FOUND"))
