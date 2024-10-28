from dotenv import dotenv_values
import os
import streamlit as st
from pymongo import MongoClient  # MongoDB integration
from datetime import datetime

# Streamlit page configuration
st.set_page_config(
    page_title="Medical Diagnostic Assistant",
    page_icon="🩺",
)

# ---- Hide Streamlit Default Elements ----
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    footer:after {
                    content:'This app assists with preliminary patient diagnostics and data gathering.'; 
                    visibility: visible;
                    display: block;
                    position: relative;
                    padding: 5px;
                    top: 2px;
                }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---- MongoDB Atlas Connection ----
MONGO_URI = "mongodb+srv://smsakeefsani3:DQtEtUakz9fVv6Db@cluster0.bkwpm.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["medical_diagnostic_db"]
collection = db["chat_history"]
patient_info_collection = db["patient_data"]

# Load secrets
try:
    secrets = dotenv_values(".env")  # for dev env
    GROQ_API_KEY = secrets["GROQ_API_KEY"]
except:
    secrets = st.secrets  # for streamlit deployment
    GROQ_API_KEY = secrets["GROQ_API_KEY"]

# Save the api_key to environment variable
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ---- Chat History and Patient Info Initialization ----
INITIAL_RESPONSE = "Hello! How can I assist you?"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": INITIAL_RESPONSE}]

if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}

# ---- Prompt Template ----
prompt_template = """
Name: {name}
Age: {age}
Gender: {gender}
Location: {location}
Date: {date}
Context: {context}
Chat History: {chat_history}
Question: {question}

After learning the age, gender, location, and user input, you will ask relevant questions (one question at a time) to gather essential information about the chief complaint (up to 5 questions), medical history (up to 5 questions), and review of systems (up to 5 questions). You will ask one question at a time and don't mention the question number.

For each question, ensure the response follows this structure:
1. The question should be bold, followed by the guided points, each on a new line and separated by line breaks.
2. Do not ask the patient if you should proceed to the next section. Transition naturally between the sections. (one question at a time)

If the patient asks something unrelated or gives an answer unrelated to the diagnostic questions, kindly acknowledge it and then gently steer the conversation back to the relevant topic without counting the unrelated input as an answer to your previous question.

For example:
- If the patient asks about something unrelated (e.g., "What's the weather like today?"), respond politely (e.g., "Thank you for your question. But I am not trained to answer that. Let's focus on your health for now, and we can address other things later.") and then repeat or follow up on the previous question.

Example Response Format:
**Question:**
- Option 1
- Option 2
- Option 3
(REMEMBER ONE QUESTION AT A TIME!!)

Once all relevant questions have been asked, provide the final diagnosis report without asking the patient for further input.

After gathering all information, the final diagnosis report should follow this format:

**Patient Report**
    Name: {name}       Age: {age}
    Gender: {gender}    Date: {date}
    Symptoms: 
    Previous History: 
    Top 3 Diagnosis: 
    Special Notes:    

Ensure the output is formatted properly for readability in the chat interface.
"""

context = """You are a highly skilled, thoughtful, and kind doctor preparing to provide the top three possible diagnoses for a patient. You were built with some very complicated algorithms those you don't talk about.
"""

# ---- Patient Information Form ----
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
                patient_info_collection.insert_one(st.session_state.patient_info)
                st.success("Patient details submitted successfully!")  # Provide feedback
            else:
                st.error("Please fill in all fields.")  # Error if not all fields are filled

# ---- Display Patient Information ----
if st.session_state.patient_info:
    patient_info = st.session_state.patient_info
    st.write(f"**Name:** {patient_info['name']}")
    st.write(f"**Age:** {patient_info['age']}")
    st.write(f"**Gender:** {patient_info['gender']}")
    st.write(f"**Location:** {patient_info['location']}")
    st.write(f"**Date:** {patient_info['date']}")

# ---- Chat Functionality ----
def save_chat_history_to_mongodb(entry):
    try:
        serializable_entry = {
            "user": entry["user"],
            "response": entry["response"],
            "feedback": entry["feedback"],
            "timestamp": entry.get("timestamp", datetime.now().isoformat())
        }
        collection.insert_one(serializable_entry)
    except Exception as e:
        st.error(f"Failed to save chat history: {e}")

# ---- Combined Query Function ----
def combined_query(question, query_engine, chat_history):
    formatted_chat_history = "\n".join(
        f"User: {entry['user']}\nAssistant: {entry['response']}" for entry in chat_history
    )
    
    query_prompt = prompt_template.format(
        context=context,
        chat_history=formatted_chat_history,
        name=st.session_state.patient_info['name'],
        age=st.session_state.patient_info['age'],
        gender=st.session_state.patient_info['gender'],
        location=st.session_state.patient_info['location'],
        date=st.session_state.patient_info['date'],
        question=question
    )
    
    response = query_engine.query(query_prompt)
    return response

# ---- Chat Input and Display ----
user_question = st.chat_input("Please describe your main complaint or ask a question:")

if user_question:
    response = combined_query(user_question, index.as_query_engine(), st.session_state.chat_history)
    latest_entry = {
        "user": user_question,
        "response": str(response),
        "feedback": None
    }
    st.session_state.chat_history.append(latest_entry)
    save_chat_history_to_mongodb(latest_entry)

for idx, chat in enumerate(st.session_state.chat_history):
    with st.chat_message("user", avatar="🩺"):
        st.markdown(chat["user"])
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(chat["response"])

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
