import os
from dotenv import dotenv_values
import streamlit as st
from groq import Groq
from datetime import datetime
from pymongo import MongoClient

st.image('https://github.com/sani002/mkpapp/blob/main/Header.png?raw=true')

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            footer:after {
                            content:'This app is in its early stage. We recommend you to seek professional advice from a real doctor. Thank you.'; 
                            visibility: visible;
                            display: block;
                            position: relative;
                            padding: 5px;
                            top: 2px;
                        }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Add CSS styling for center alignment
st.markdown(
    """
    <style>
    .center {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def parse_groq_stream(stream):
    for chunk in stream:
        if chunk.choices:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

# ---- Environment Variables ---
os.environ["GROQ_API_KEY"] = "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"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# MongoDB Atlas Connection
MONGO_URI = "mongodb+srv://smsakeefsani3:DQtEtUakz9fVv6Db@cluster0.bkwpm.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["greyfiles_db"]  # Replace with your database name
collection = db["chat_history"]  # Collection for chat history

# Save chat history entry to MongoDB
def save_chat_history_to_mongodb(entry):
    collection.insert_one(entry)

# Initialize default values
INITIAL_RESPONSE = "Hello! How can I assist you?"

client = Groq()

# Initialize the chat history if not already set in the session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": INITIAL_RESPONSE, "feedback": None}]

# Initialize patient information if not already set in the session state
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}

# Step 1: Collect Patient Information
st.title("Differential Diagnostic Assistant")
st.caption("Please fill in the patient details before proceeding.")

# Create a form for patient information
with st.form("patient_info_form"):
    if not st.session_state.patient_info:  # Only display the form if patient info is not set
        name = st.text_input("Patient Name")
        age = st.number_input("Patient Age", min_value=0, max_value=120)
        gender = st.selectbox("Patient Gender", options=["Male", "Female", "Other"])
        location = st.text_input("Patient Location")
        submit_button = st.form_submit_button(label="Submit Details")

        if submit_button:  # Handle submission
            if name and age and gender and location:  # Validate inputs
                st.session_state.patient_info = {
                    "name": name,
                    "age": age,
                    "gender": gender,
                    "location": location,
                    "date": datetime.today().strftime("%Y-%m-%d")
                }
                st.success("Patient details submitted successfully!")  # Provide feedback
            else:
                st.error("Please fill in all fields.")  # Error if not all fields are filled

# Step 2: Display Patient Information
if st.session_state.patient_info:
    patient_info = st.session_state.patient_info
    st.write(f"**Name:** {patient_info['name']}")
    st.write(f"**Age:** {patient_info['age']}")
    st.write(f"**Gender:** {patient_info['gender']}")
    st.write(f"**Location:** {patient_info['location']}")
    st.write(f"**Date:** {patient_info['date']}")

# Step 3: Display Chat History
st.divider()
for idx, chat in enumerate(st.session_state.chat_history):
    role = chat["role"]
    avatar = "🗨️" if role == "user" else "⚕️"
    with st.chat_message(role, avatar=avatar):
        st.markdown(chat["content"])

    # Add Like/Dislike buttons for feedback
    if chat["feedback"] is None:  # Only show buttons if no feedback yet
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Like", key=f"like_{idx}"):
                st.session_state.chat_history[idx]["feedback"] = "like"
                latest_entry = {
                    "user": st.session_state.chat_history[idx - 1]["content"] if idx > 0 else None,
                    "response": str(chat["content"]),
                    "feedback": "like",
                    "patient_info": st.session_state.patient_info
                }
                save_chat_history_to_mongodb(latest_entry)
        with col2:
            if st.button("Dislike", key=f"dislike_{idx}"):
                st.session_state.chat_history[idx]["feedback"] = "dislike"
                latest_entry = {
                    "user": st.session_state.chat_history[idx - 1]["content"] if idx > 0 else None,
                    "response": str(chat["content"]),
                    "feedback": "dislike",
                    "patient_info": st.session_state.patient_info
                }
                save_chat_history_to_mongodb(latest_entry)

# Step 4: Handle User Prompt
user_prompt = st.chat_input("Ask me")

if user_prompt and st.session_state.patient_info:
    # Display user's message
    with st.chat_message("user", avatar="🗨️"):
        st.markdown(user_prompt)
    
    # Add user message to the chat history
    st.session_state.chat_history.append({"role": "user", "content": user_prompt, "feedback": None})
    
    # Generate response using the prompt template
    prompt_template = f"""
    You are a highly skilled, thoughtful and kind doctor preparing to provide the top three possible diagnoses for a patient.
    
    Name: {patient_info['name']}
    Age: {patient_info['age']}
    Gender: {patient_info['gender']}
    Location: {patient_info['location']}
    Date: {patient_info['date']}
    User input: {user_prompt}

    After learning the age, gender, location, and user input, you will ask relevant questions (one question at a time).
    """
    # Prepare messages for the model by excluding the `feedback` key
    messages_for_model = [
        {k: v for k, v in message.items() if k != "feedback"} for message in st.session_state.chat_history
    ]

    # Display assistant's response with streaming
    with st.chat_message("assistant", avatar='⚕️'):
        stream = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "assistant", "content": prompt_template}] + messages_for_model,
            stream=True  # for streaming the message
        )
        response = st.write_stream(parse_groq_stream(stream))

    # Add the assistant's response to the chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response, "feedback": None})
