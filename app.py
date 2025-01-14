import streamlit as st
import openai
import requests
import subprocess
import os

# API Keys
OPENAI_API_KEY = "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"
ELEVEN_LABS_API_KEY = "sk_dce058f72c80d27257de740e8225e98db7619ee5548e053c"
ELEVEN_LABS_VOICE_ID = "Fahco4VZzobUeiPqni1S"

# Display logo
st.image("https://datalawonline.co.uk/uploads/images/f-b-screen.png", width=200)
st.title("📄 Script Processor with Audio and Video Generation")

# Helper functions
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

def calculate_default_durations(sections, total_audio_duration):
    """Calculates default durations for sections based on word count."""
    word_counts = [len(section.split()) for section in sections]
    total_words = sum(word_counts)
    return [(count / total_words) * total_audio_duration for count in word_counts]

def generate_video_with_ffmpeg(audio_path, section_images, section_durations):
    """Generates a video by combining images with audio using FFmpeg."""
    try:
        audio_duration = get_audio_duration(audio_path)
        total_video_duration = sum(section_durations)

        # Extend last slide if total video duration is less than the audio
        if total_video_duration < audio_duration:
            section_durations[-1] += audio_duration - total_video_duration

        # Resize images for consistency
        resized_images = []
        for i, image in enumerate(section_images):
            resized_image = f"resized_{i}.jpg"
            subprocess.run(["ffmpeg", "-y", "-i", image, "-vf", "scale=1280:720", resized_image])
            resized_images.append(resized_image)

        # Create the `image_list.txt` file
        with open("image_list.txt", "w") as f:
            for image, duration in zip(resized_images, section_durations):
                f.write(f"file '{image}'\n")
                f.write(f"duration {duration}\n")
            f.write(f"file '{resized_images[-1]}'\n")  # Repeat the last image

        # Generate the video with improved keyframe handling
        video_path = "final_video.mp4"
        ffmpeg_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "image_list.txt",
            "-i", audio_path, "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-g", "15", "-c:a", "aac", "-shortest", video_path
        ]
        result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            st.error(f"FFmpeg error: {result.stderr}")
            return None
        return video_path
    except Exception as e:
        st.error(f"Error during video generation: {e}")
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
            full_script += section["chunk"] + "\n\n"
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

# Generate Video
if "audio_path" in st.session_state:
    st.write("### Upload Images and Set Slide Timings")
    images, durations = [], []

    intro_image = st.file_uploader("Upload Introduction Image", type=["jpg", "png"])
    if intro_image:
        path = "intro.jpg"
        with open(path, "wb") as f:
            f.write(intro_image.getbuffer())
        images.append(path)

    for i, section in enumerate(st.session_state["chunks"]):
        img = st.file_uploader(f"Upload Image for Section {i + 1}", type=["jpg", "png"], key=f"img_{i}")
        if img:
            path = f"section_{i + 1}.jpg"
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            images.append(path)

    concl_image = st.file_uploader("Upload Conclusion Image", type=["jpg", "png"])
    if concl_image:
        path = "conclusion.jpg"
        with open(path, "wb") as f:
            f.write(concl_image.getbuffer())
        images.append(path)

    if len(images) == len(st.session_state["chunks"]) + 2:
        audio_duration = get_audio_duration(st.session_state["audio_path"])
        default_durations = calculate_default_durations(
            [introduction] + [section["chunk"] for section in st.session_state["chunks"]] + [conclusion],
            audio_duration
        )

        user_durations = []
        for i, (image, default_duration) in enumerate(zip(images, default_durations)):
            user_duration = st.number_input(
                f"Duration for Slide {i + 1} (seconds)",
                value=default_duration,
                step=1.0,
                key=f"duration_{i}"
            )
            user_durations.append(user_duration)

        if len(user_durations) == len(images) and st.button("🎥 Generate Video"):
            with st.spinner("Generating video..."):
                video = generate_video_with_ffmpeg(st.session_state["audio_path"], images, user_durations)
                if video:
                    st.video(video)
                    st.download_button("Download Video", data=open(video, "rb").read(), file_name="final_video.mp4")
