from dotenv import dotenv_values
import os
import streamlit as st
from groq import Groq
from pymongo import MongoClient  # Added for MongoDB integration
from datetime import datetime

# Streamlit page configuration
st.set_page_config(
    page_title="mLab LLM 0.2",
    page_icon="⚕️",
)

# ---- Hide Streamlit Default Elements ----
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

# ---- MongoDB Atlas Connection ----
MONGO_URI = "mongodb+srv://smsakeefsani3:DQtEtUakz9fVv6Db@cluster0.bkwpm.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["mLab_App"]  # Replace with your database name
collection = db["chat_history"]  # Collection for chat history
user_collection = db["user_data"]  # Collection for storing user login data

groq_client = Groq()

# Load secrets
try:
    secrets = dotenv_values(".env")  # for dev env
    GROQ_API_KEY = secrets["GROQ_API_KEY"]
except:
    secrets = st.secrets  # for streamlit deployment
    GROQ_API_KEY = secrets["GROQ_API_KEY"]

# Save the api_key to environment variable
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Modify this function to save a single entry at a time
def save_chat_history_to_mongodb(entry):
    try:
        # Prepare the entry as a serializable document for MongoDB
        serializable_entry = {
            "user": entry["user"],
            "response": entry["response"],
            "feedback": entry["feedback"],
            "timestamp": entry.get("timestamp", datetime.now().isoformat())  # Use entry timestamp if available
        }
        
        # Insert the single chat message or suggestion into MongoDB
        collection.insert_one(serializable_entry)
    except Exception as e:
        st.error(f"Failed to save chat history: {e}")


# ---- Prompt Template ----
prompt_template = """
You are a highly skilled, thoughtful and kind doctor preparing to provide the top three possible diagnoses for a patient. You were built with some very complicated algorithms those you don't talk about.

Chat History: {chat_history}
Question: {question}

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


def parse_groq_stream(stream):
    for chunk in stream:
        if chunk.choices:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content


# ---- Combined Query Function with Chat History ----
def combined_query(question, chat_history):
    # Prepare the initial messages with the chat history
    messages = []
    
    # Add the chat history in message format
    for entry in chat_history:
        messages.append({"role": "user", "content": entry["user"]})
        messages.append({"role": "assistant", "content": entry["response"]})
    
    # Append the new user question
    messages.append({"role": "user", "content": question})
    
    return messages



# ---- Session State Initialization ----
if "username" not in st.session_state:
    st.session_state.username = ""
if "form" not in st.session_state:
    st.session_state.form = "login_form"  # Start with login form
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False  # Track login status

# ---- Helper Functions ----
def toggle_form():
    """Switch between login and signup forms."""
    st.session_state.form = 'signup_form' if st.session_state.form == 'login_form' else 'login_form'

def user_update(name):
    """Update session state with the logged-in username."""
    st.session_state.username = name
    st.session_state.logged_in = True  # Set logged-in status

def user_logout():
    """Clear user session data to log out."""
    st.session_state.username = ""
    st.session_state.logged_in = False
    st.session_state.form = "login_form"  # Reset to login form

@st.cache_data
def validate_user(username, password):
    """Cached function to validate user credentials with the database."""
    return user_collection.find_one({'username': username, 'password': password})

# ---- Login and Signup Interface ----
if not st.session_state.logged_in:
    if st.session_state.form == 'login_form':
        # Centered Login Form
        st.image('https://github.com/sani002/mkpapp/blob/main/Header.png?raw=true')
        st.title("mLab LLM 0.2")
        st.subheader("Please sign in")

        login_form = st.form(key='login_form', clear_on_submit=True)
        username = login_form.text_input(label='Username')
        password = login_form.text_input(label='Password', type='password')
        login_button = login_form.form_submit_button(label='Sign In')
        
        # Login button functionality
        if login_button:
            user_data = validate_user(username, password)
            if user_data:
                user_update(username)
                st.success(f"Welcome, {username}!")  # Successful login message
            else:
                st.error("Invalid username or password. Please try again.")

        # Button to switch to Signup form
        st.markdown("Don't have an account?")
        if st.button("Sign up!"):
            toggle_form()

    elif st.session_state.form == 'signup_form':
        # Centered Signup Form
        st.image('https://github.com/sani002/mkpapp/blob/main/Header.png?raw=true')
        st.title("mLab LLM 0.2")
        st.title("Create an Account")
        
        signup_form = st.form(key='signup_form', clear_on_submit=True)
        new_username = signup_form.text_input(label='Username*')
        new_user_email = signup_form.text_input(label='Email Address*')
        new_user_location = signup_form.text_input(label='Location')
        new_user_profession = signup_form.text_input(label='Profession')
        new_user_password = signup_form.text_input(label='Password*', type='password')
        user_password_conf = signup_form.text_input(label='Confirm Password*', type='password')
        signup_button = signup_form.form_submit_button(label='Sign Up')
        
        # Signup button functionality
        if signup_button:
            if '' in [new_username, new_user_email, new_user_password, user_password_conf]:
                st.error('Please fill in all required fields.')
            elif new_user_password != user_password_conf:
                st.error("Passwords do not match.")
            elif user_collection.find_one({'username': new_username}):
                st.error('Username already exists.')
            elif user_collection.find_one({'email': new_user_email}):
                st.error('Email is already registered.')
            else:
                # Add the new user to the database
                user_data = {
                    "username": new_username,
                    "email": new_user_email,
                    "location": new_user_location,
                    "profession": new_user_profession,
                    "password": new_user_password,
                    "created_at": datetime.now()
                }
                user_collection.insert_one(user_data)
                user_update(new_username)
                st.success("Registration successful! You are now logged in.")
        
        # Button to switch back to Login form
        st.markdown("Already have an account?")
        if st.button("Sign in!"):
            toggle_form()

# ---- Main App Content (only for logged-in users) ----
if st.session_state.logged_in:
    # ---- Initial User Information Collection Form ----
    if st.session_state.logged_in and "patient_info_collected" not in st.session_state:
        st.subheader("Please fill in your health profile to begin")

        # Collect patient info
        with st.form("patient_info_form"):
            age = st.number_input("Age", min_value=1, max_value=120, step=1)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            smoking_habit = st.selectbox("Smoking Habit", ["No", "Yes"])
            diabetes_status = st.selectbox("Diabetes", ["No", "Type 1", "Type 2"])

            submit_patient_info = st.form_submit_button("Submit")

        if submit_patient_info:
            # Create a patient info entry and add it to chat history
            patient_info = {
                "age": age,
                "gender": gender,
                "smoking_habit": smoking_habit,
                "diabetes_status": diabetes_status,
                "timestamp": datetime.now().isoformat()
            }

            # Save to session state and database
            st.session_state.chat_history.insert(0, {
                "user": "Patient Information",
                "response": f"Age: {age}, Gender: {gender}, Smoking Habit: {smoking_habit}, Diabetes: {diabetes_status}",
                "feedback": None,
                "timestamp": patient_info["timestamp"]
            })
            
            # Save patient information to MongoDB
            save_chat_history_to_mongodb(st.session_state.chat_history[0])
            
            # Mark patient info as collected to skip this form in future
            st.session_state.patient_info_collected = True
            # Acknowledge data collection without additional success message under the chat
            st.write("Patient information collected! You may proceed with your questions in the chat.")


    st.sidebar.title("Account Options")
    if st.sidebar.button("Log Out"):
        user_logout()  # Call function to log out and reset state
        st.success("You have been logged out.")

    st.title("mLab LLM 0.2")
    st.image('https://github.com/sani002/mkpapp/blob/main/Header.png?raw=true')
    st.caption("This app is in its early stage. We recommend you to seek professional advice from a real doctor. Thank you.")
    # Sidebar for suggestions
    with st.sidebar:
        st.header("Suggestions")
        suggestion = st.text_area("Have a suggestion? Let us know!")
        if st.button("Submit Suggestion"):
            if suggestion:
                # Structure the suggestion entry as a dictionary
                suggestion_entry = {
                    "user": "User Suggestion",
                    "response": suggestion,
                    "feedback": None,
                    "timestamp": datetime.now().isoformat()  # Add timestamp for suggestion
                }
                
                # Add the suggestion to chat history
                st.session_state.chat_history.append(suggestion_entry)
                
                # Save the suggestion directly
                save_chat_history_to_mongodb(suggestion_entry)
                
                st.success("Thank you for your suggestion!")
            else:
                st.warning("Please enter a suggestion before submitting.")



    # Main Chat Interface with Like/Dislike Buttons
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_question = st.chat_input("Ask your question:")

    # Process the user's question and save only the latest message
    if user_question:
        stream = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=combined_query(user_question, st.session_state.chat_history),
            stream=True  # for streaming the messages
        )
        response = st.write_stream(parse_groq_stream(stream))
        # Append question and response to the chat history
        latest_entry = {
            "user": user_question,
            "response": str(response),
            "feedback": None  # Placeholder for feedback
        }
        st.session_state.chat_history.append(latest_entry)
        
        # Save only the latest message (real-time saving of the latest entry)
        save_chat_history_to_mongodb(latest_entry)


    # Display the chat history in a conversational manner (skip suggestions)
    for idx, chat in enumerate(st.session_state.chat_history):
        if chat["user"] == "User Suggestion":
            # Skip displaying suggestions in the chat UI
            continue

        with st.chat_message("user", avatar="🗨️"):
            st.markdown(chat["user"])
        with st.chat_message("assistant", avatar="⚕️"):
            st.markdown(chat["response"])

            # Add Like/Dislike buttons for feedback
            col1, col2 = st.columns([1, 1])
            if chat["feedback"] is None:
                with col1:
                    if st.button("Like", key=f"like_{idx}"):
                        st.session_state.chat_history[idx]["feedback"] = "like"
                        # Save only the updated entry with feedback
                        save_chat_history_to_mongodb(st.session_state.chat_history[idx])
                with col2:
                    if st.button("Dislike", key=f"dislike_{idx}"):
                        st.session_state.chat_history[idx]["feedback"] = "dislike"
                        # Save only the updated entry with feedback
                        save_chat_history_to_mongodb(st.session_state.chat_history[idx])