# --- IMPORTS AND INITIALIZATION ---
from dotenv import load_dotenv
load_dotenv() # Load GEMINI_API_KEY from the .env file

from flask import Flask, render_template, request, jsonify
import time
import random
# Imports for the Gemini API (using the Google GenAI SDK)
from google import genai
from google.genai.errors import APIError

# --- NEW IMPORTS FOR HARDWARE INTEGRATION ---
import serial
import serial.tools.list_ports 
# You MUST install pyserial: pip install pyserial
# --------------------------------------------

# Initialize the Gemini Client
try:
    # Ensure this uses the key loaded from .env
    client = genai.Client() 
except Exception as e:
    print(f"Error during Gemini Client initialization: {e}") 
    client = None 

app = Flask(__name__)

# --- HARDWARE CONFIGURATION ---
# IMPORTANT: Change this to the actual port number your Arduino is using!
ARDUINO_PORT = 'COM3' 
BAUD_RATE = 9600
LAST_READ_WEIGHT = 0.0 

# --- SERIAL CONNECTION INITIALIZATION ---
ser = None
try:
    # Attempt to open the serial port
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    # Wait for the Arduino to reset after connecting
    time.sleep(2) 
    print(f"SUCCESS: Serial connection established on {ARDUINO_PORT}")
except serial.SerialException as e:
    print(f"ERROR: Could not open serial port {ARDUINO_PORT}.")
    print("Check if the Arduino is plugged in and if the port name is correct.")
    print(f"Details: {e}")
    # If connection fails, ser remains None, and we will return the last known weight (0.0)
# --- REAL WEIGHT READING FUNCTION ---
def read_arduino_weight():
    """Reads a single, most recent, parsed weight value from the Arduino's serial buffer."""
    global LAST_READ_WEIGHT

    if ser is None:
        # If the serial connection is not active, return the last valid reading
        return LAST_READ_WEIGHT 

    try:
        # 1. Check if new data is waiting
        if ser.in_waiting > 0:
            # Read until the newline character (\n) is received, decode bytes to string, and strip whitespace
            line = ser.readline().decode('utf-8').strip() 
            
            # 2. Parse the line: Look for the 'WEIGHT:' identifier (matching Arduino output)
            if line.startswith("WEIGHT:"):
                #Split the string and convert the weight part to a float
                weight_str = line.split(":")[1]
                weight_float = float(weight_str)
                
                # --- DEBUGGING PRINT ---
                #This line will show the live weight in your terminal
                print(f"| Serial Read: {line} | Parsed Weight: {weight_float:.2f} g")
                # -----------------------
                
                # Update and return the global weight
                LAST_READ_WEIGHT = weight_float
                return LAST_READ_WEIGHT
        
        #If no new line was available in this cycle, return the last known value
        return LAST_READ_WEIGHT

    except Exception as e:
        #Handle errors during reading (e.g., connection drop)
        print(f"Error reading serial data: {e}. Returning last known weight.")
        return LAST_READ_WEIGHT
# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weight', methods=['GET'])
def get_weight():
    """Returns the live weight reading from the Arduino."""
    return jsonify({'weight': read_arduino_weight()})

@app.route('/get_recipe', methods=['POST'])
def get_recipe():
    """Handles the inventory list and calls the Gemini API."""
    
    data = request.json
    inventory = data.get('inventory', [])
    
    if not inventory:
        return jsonify({'error': 'Inventory list is empty. Add ingredients.'}), 400
    if not client:
        return jsonify({'error': 'AI Client not initialized. Check GEMINI_API_KEY in .env file.'}), 500
        
    # 1. Prepare ingredients prompt for AI
    prompt_list = [f"{item['weight']} grams of {item['name']}" for item in inventory]
    inventory_string = ", ".join(prompt_list)
    
    # 2. AI Prompt
    user_prompt = (
        "You are a recipe generator. Generate a simple, step-by-step recipe that uses "
        f"ONLY the following ingredients and quantities: {inventory_string}. "
        "Provide the recipe title, a short description, and clear, numbered steps. "
        "Do not include any other ingredients."
    )
    print(f"Sending prompt to Gemini: {user_prompt}")
    
    try:
        # 3. Call Gemini API 
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt
        )
        # 4. Extract the response text
        recipe_text = response.text
        return jsonify({'recipe': recipe_text})

    except APIError as e:
        error_message = str(e)
        print(f"Gemini API Error: {error_message}")
        if "API key not valid" in error_message:
            browser_error = "Gemini API Key Error: Please check your key in the .env file."
        else:
            browser_error = "Gemini API Service Error. Please check your internet connection or free tier quota."
        return jsonify({'error': browser_error}), 500
    
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)