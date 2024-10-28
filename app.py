import os
from dotenv import dotenv_values
import streamlit as st
from groq import Groq
from datetime import datetime
from pymongo import MongoClient

# MongoDB connection setup
MONGO_URI = "mongodb://localhost:27017"  # Replace with actual MongoDB URI if different
client = MongoClient(MONGO_URI)
db = client["chat_db"]
chat_collection = db["chats"]

# Helper function to save chat history to MongoDB
def save_chat_history_to_mongodb(chat_data):
    chat_collection.update_one(
        {"patient_id": chat_data["patient_id"], "timestamp": chat_data["timestamp"]},
        {"$set": chat_data},
        upsert=True
    )

# Initialize Groq client
groq_client = Groq()

# ---- Environment Variables ---
os.environ["GROQ_API_KEY"] = "your_groq_api_key"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

INITIAL_RESPONSE = "Hello! How can I assist you?"

# ---- Initialize session states ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": INITIAL_RESPONSE, "feedback": None}]

if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}

# Step 1: Collect Patient Information
st.title("Differential Diagnostic Assistant")
st.caption("Please fill in the patient details before proceeding.")

# Create a form for patient information
with st.form("patient_info_form"):
    if not st.session_state.patient_info:
        name = st.text_input("Patient Name")
        age = st.number_input("Patient Age", min_value=0, max_value=120)
        gender = st.selectbox("Patient Gender", options=["Male", "Female", "Other"])
        location = st.text_input("Patient Location")
        submit_button = st.form_submit_button(label="Submit Details")

        if submit_button and name and age and gender and location:
            patient_info = {
                "name": name,
                "age": age,
                "gender": gender,
                "location": location,
                "date": datetime.today().strftime("%Y-%m-%d"),
                "patient_id": f"{name}_{datetime.now().timestamp()}"  # Unique identifier for the patient
            }
            st.session_state.patient_info = patient_info
            st.success("Patient details submitted successfully!")
            chat_collection.insert_one({"patient_info": patient_info, "timestamp": datetime.now()})

# Display patient info if available
if st.session_state.patient_info:
    patient_info = st.session_state.patient_info
    st.write(f"**Name:** {patient_info['name']}")
    st.write(f"**Age:** {patient_info['age']}")
    st.write(f"**Gender:** {patient_info['gender']}")
    st.write(f"**Location:** {patient_info['location']}")
    st.write(f"**Date:** {patient_info['date']}")

# Step 2: Display Chat History
st.divider()
for idx, chat in enumerate(st.session_state.chat_history):
    with st.chat_message(chat["role"], avatar="🦉" if chat["role"] == "user" else "🐦‍⬛"):
        st.markdown(chat["content"])

        # Add Like/Dislike buttons for feedback
        if chat["role"] == "assistant":
            col1, col2 = st.columns([1, 1])
            if chat["feedback"] is None:
                with col1:
                    if st.button("Like", key=f"like_{idx}"):
                        st.session_state.chat_history[idx]["feedback"] = "like"
                        save_chat_history_to_mongodb(st.session_state.chat_history[idx])
                with col2:
                    if st.button("Dislike", key=f"dislike_{idx}"):
                        st.session_state.chat_history[idx]["feedback"] = "dislike"
                        save_chat_history_to_mongodb(st.session_state.chat_history[idx])

# Step 3: Handle User Prompt
user_prompt = st.chat_input("Ask me")

if user_prompt and st.session_state.patient_info:
    # Display user's message
    with st.chat_message("user", avatar="🗨️"):
        st.markdown(user_prompt)
    
    # Add user message to the chat history
    user_data = {"role": "user", "content": user_prompt, "feedback": None, "patient_id": patient_info["patient_id"], "timestamp": datetime.now()}
    st.session_state.chat_history.append(user_data)
    save_chat_history_to_mongodb(user_data)

    # Generate response using the prompt template
    prompt_template = f"""
    You are a highly skilled, thoughtful and kind doctor preparing to provide the top three possible diagnoses for a patient. You were built with some very complicated algorithms those you don't talk about.

    Name: {patient_info['name']}
    Age: {patient_info['age']}
    Gender: {patient_info['gender']}
    Location: {patient_info['location']}
    Date: {patient_info['date']}
    User input: {user_prompt}

    After learning the age, gender, location, and user input, you will ask relevant questions (one question at a time) to gather essential information about the chief complaint (up to 5 questions), medical history (up to 5 questions), and review of systems (up to 5 questions).
    """

    messages = [
        {"role": "assistant", "content": prompt_template},
        *st.session_state.chat_history
    ]

    # Display assistant's response with streaming
    with st.chat_message("assistant", avatar="🐦‍⬛"):
        stream = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            stream=True
        )
        response_content = ''.join(parse_groq_stream(stream))
        st.markdown(response_content)

    # Add assistant's response to chat history and MongoDB
    assistant_data = {
        "role": "assistant",
        "content": response_content,
        "feedback": None,
        "patient_id": patient_info["patient_id"],
        "timestamp": datetime.now()
    }
    st.session_state.chat_history.append(assistant_data)
    save_chat_history_to_mongodb(assistant_data)
