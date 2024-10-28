import os
from dotenv import dotenv_values
import streamlit as st
from groq import Groq
from datetime import datetime

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

# Initialize default values
INITIAL_RESPONSE = "Hello! How can I assist you?"

client = Groq()

# Initialize the chat history if not already set in the session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": INITIAL_RESPONSE}]

# Initialize feedback history if not already set
if "feedback" not in st.session_state:
    st.session_state.feedback = {}

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

# Step 3: Display Chat History with Like/Dislike for Every Later Reply (Not the Initial One)
st.divider()
if "chat_history" in st.session_state:
    for i, chat in enumerate(st.session_state.chat_history):
        role = chat["role"]
        avatar = "🗨️" if role == "user" else "⚕️"
        
        # Display each message with the appropriate role avatar
        with st.chat_message(role, avatar=avatar):
            st.markdown(chat["content"])

        # Add Like/Dislike buttons only for the assistant responses AFTER the first one
        if role == "assistant" and i > 0:  # Skip the initial response
            col1, col2 = st.columns(2)  # Two columns for buttons
            
            with col1:
                if st.button("👍 Like", key=f"like_{i}"):
                    st.session_state.feedback[f"like_{i}"] = "like"
                    st.success(f"Response {i + 1}: Liked!")
                    
            with col2:
                if st.button("👎 Dislike", key=f"dislike_{i}"):
                    st.session_state.feedback[f"dislike_{i}"] = "dislike"
                    st.error(f"Response {i + 1}: Disliked!")

# Step 4: Handle User Prompt
user_prompt = st.chat_input("Ask me")

if user_prompt and st.session_state.patient_info:
    # Display user's message
    with st.chat_message("user", avatar="🗨️"):
        st.markdown(user_prompt)
    
    # Add user message to the chat history
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    
    # Generate response using the prompt template
    prompt_template = f"""
    You are a highly skilled, thoughtful and kind doctor preparing to provide the top three possible diagnoses for a patient. You were built with some very complicated algorithms those you don't talk about.

    Name: {patient_info['name']}
    Age: {patient_info['age']}
    Gender: {patient_info['gender']}
    Location: {patient_info['location']}
    Date: {patient_info['date']}
    User input: {user_prompt}

    After learning the age, gender, location, and user input, you will ask relevant questions (one question at a time) to gather essential information about the chief complaint (up to 5 questions), medical history (up to 5 questions), and review of systems (up to 5 questions). You will ask one question at a time and don't mention the qustion number.

    For each question, ensure the response follows this structure:
    1. The question should be bold, followed by the guided points, each on a new line and separated by line breaks.
    2. Do not ask the patient if you should proceed to the next section. Transition naturally between the sections. (one question at a time)

    If the patient asks something unrelated or gives an answer unrelated to the diagnostic questions, kindly acknowledge it and then gently steer the conversation back to the relevant topic without counting the unrelated input as an answer to your previous question.

    For example:
    - If the patient asks about something unrelated (e.g., "What's the weather like today?"), respond politely (e.g., "Thank you for your question. But I am no trained to answer that. Let's focus on your health for now, and we can address other things later.") and then repeat or follow up on the previous question.

    Example Response Format:
    **Question:**
    - Option 1
    - Option 2
    - Option 3
    (REMEMBER ONE QUESTION AT A TIME!!)

    Once all relevant questions have been asked, provide the final diagnosis report without asking the patient for further input.

    After gathering all information, the final diagnosis report should follow this format:

    **Patient Report**
        Name: {patient_info['name']}       Age: {patient_info['age']}
        Gender: {patient_info['gender']}    Date: {patient_info['date']}
        Symptoms: 
        Previous History: 
        Top 3 Diagnosis: 
        Special Notes:    

    Ensure the output is formatted properly for readability in the chat interface.
    """

    # Use the template and chat history to create the messages for the LLM
    messages = [
        {"role": "assistant", "content": prompt_template},  # Prompt template is enough
        *st.session_state.chat_history
    ]

    # Display assistant's response with streaming
    with st.chat_message("assistant", avatar='⚕️'):
        stream = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            stream=True  # for streaming the message
        )
        response = st.write_stream(parse_groq_stream(stream))

    # Add the assistant's response to the chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response})
