import os
import json 
import random # Added for random ID generation and volume
from flask import Flask, render_template, request, jsonify, redirect, url_for # Added redirect and url_for
from dotenv import load_dotenv

from google import genai
from google.genai import types

# --- Load environment variables from the .env file ---
load_dotenv() 

app = Flask(__name__)

# Global in-memory storage for newly created predictions
# This is a simple way to store the data for the immediate next request (the redirect)
temp_predictions = {} 

try:
    # Check if the API key is available in the environment variables
    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY is not set.")
    
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    client = None


def generate_six_digit_id():
    """Generates a unique 6-digit integer ID not currently in temporary storage."""
    while True:
        # Generate a random number between 100000 and 999999
        new_id = random.randint(100000, 999999)
        # Ensure the ID is not already used in the temporary store
        if new_id not in temp_predictions:
            return new_id


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    print("START PREDICT")
    topic = request.form.get("topic")
    print("TOPIC", topic)
    duration = request.form.get("duration")   


    print("TOPIC", topic, "DURATION", duration)


    if not topic:
        return jsonify({"result": "Please provide a prediction title."}) 

    if client is None:
        return jsonify({"result": "LLM client failed to initialize. Check if GEMINI_API_KEY is set correctly."})

    # --- Define the desired output structure (Schema remains the same) ---
    output_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "category": types.Schema(type=types.Type.STRING, description="The main topic category (e.g., Technology, Culture, Economics)."),
            "frequency": types.Schema(type=types.Type.STRING, description="A prediction of how often this topic will be discussed (e.g., Daily, Monthly, Annually)."),
            "can_end_early": types.Schema(type=types.Type.BOOLEAN, description="Determines whether the event can come true at any point in time rather than having to wait till the end of its time")
        },
        # Ensure prediction_text is expected, which guides the model to include it
        required=["category", "frequency", "can_end_early"] 
    )
    
    # --- New Combined Prompt ---
    full_prompt = (
        "You are a mystical, predictive MetaBall. A user has provided a **TITLE** of an event. "
        "Analyze this title and output a suitable **Category** (from the exact list: "
        "['financials', 'crypto', 'sports', 'mentions', 'world', 'entertainment', 'social', 'climate and weather']), "
        "and the **Frequency** this type of event occurs (e.g., 'Yearly' for a league winner, 'Daily' for breaking news). "
        "Options for  **Frequency** are: ['Daily', 'one_off', 'weekly', 'hourly', 'custom'] so only these values can be used for **Frequency**"
        "Also provide a boolean (True or False) value for **can_end_early**. This is dependant on whether the event can come true at anytime during"
        " the bid period. For example, if the bid is that it is going to rain in the next week, as soon as it rains, the bid is over so you set can_end_early to True, whereas if it "
        "were a bid on a team winning a football match, the bid is only won at the end of the match so you would set it to False"
        "Generate a JSON object that strictly conforms to the provided schema.\n\n"
        f"Analyze this prediction title: '{topic}'"
    )
    
    json_text = ""

    try:
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = [
                {
                    "role": "user", 
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=output_schema
            )
        )

        json_text = response.text.strip()
        
        # --- RESILIENCY FIX: Aggressively isolate JSON object ---
        
        # 1. Strip common markdown code fences before parsing
        if json_text.startswith("```json"):
            json_text = json_text.lstrip("```json").rstrip("```").strip()
        elif json_text.startswith("```"):
            json_text = json_text.lstrip("```").rstrip("```").strip()
            
        # 2. Find the start and end of the JSON object ({...}) to exclude any preamble or postscript text.
        try:
            start_index = json_text.index('{')
            end_index = json_text.rindex('}')
            # Slice the string to include only the content between the first { and last }
            json_text = json_text[start_index:end_index + 1]
        except ValueError:
            # If the braces are not found, use the original text and let json.loads handle the error
            pass
        # --- END RESILIENCY FIX ---

        llm_data = json.loads(json_text)

        # --- REDIRECT LOGIC: Return URL in JSON instead of a Flask redirect (302) ---
        
        new_id = generate_six_digit_id()
        # Generate a random volume score (required by the existing compare_events logic)
        category = llm_data["category"]
        frequency = llm_data["frequency"]
        can_close_early = llm_data.get("can_end_early", False)

        print("BOOLEAN:", can_close_early)
        new_event = {
            "id": new_id,
            "title": topic,
            "category":category,
            "frequency": frequency,
            "duration": duration,
            "can_close_early": can_close_early
        }

        interpolated_volume = generate_six_digit_id()
        
        new_event["final_volume"] = interpolated_volume
        
        # Store the new event data temporarily using the integer ID as the key
        temp_predictions[new_id] = new_event
        
        # Generate the target URL
        redirect_url = url_for('compare_events', event_id=new_id)
        
        # Return the URL in a JSON response for the client-side JavaScript to handle
        print(f"DEBUG: Returning redirect URL to client: {redirect_url}")
        return jsonify({"redirect_url": redirect_url, "result": "Success"})


    except Exception as e:
        debug_message = f"Error: LLM Generation or Parsing failed. Raw response was: {json_text}"
        print(f"Gemini Prediction Error: {e}. Raw Text: {json_text}")
        return jsonify({"result": debug_message})


DATA_FILE = 'data2.json'

def load_all_events():
    """Loads all data from the JSON file and merges it with temporary predictions."""
    # Load static data
    all_events = []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            all_events = json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found. Using only temporary data.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {DATA_FILE}. Using only temporary data.")
        
    # Merge with temporary predictions
    # Note: temp_predictions keys are integers, and the values are dicts with integer 'id' fields.
    all_events.extend(list(temp_predictions.values()))
    print("ALL_EVENTS_LENGTH:", len(all_events))
    return all_events

@app.route("/compare/<int:event_id>")
def compare_events(event_id):
    # 1. Load all data (including the new prediction)
    all_events = load_all_events()

    # 2. Find the user-specified event (the central column item)
    main_event = next((e for e in all_events if e.get("id") == event_id), None)

    if not main_event:
        return f"Error: Event with ID {event_id} not found.", 404
    
    # Ensure the main event has a volume attribute
    main_volume = main_event.get("final_volume")
    if main_volume is None or not isinstance(main_volume, (int, float)):
        return f"Error: Main event (ID {event_id}) does not have a valid 'final_volume' attribute for comparison.", 400

    # 3. Find two similarly scored events based on volume
    
    # Filter out the main event and any events without a valid volume
    comparable_events = [
        e for e in all_events 
        if e.get("id") != event_id
    ]

    # Calculate the similarity score (absolute difference in volume)
    # The event is "more similar" if the absolute difference is smaller.
    def volume_difference(event):
        return abs(event.get("final_volume") - main_volume)

    # Sort the comparable events using the difference function
    comparable_events.sort(key=volume_difference)

    # Take the two most similar events
    # Use dummy data if static data runs out, to prevent index errors
    DUMMY_EVENT = {"id": 0, "title": "No Similar Event Found", "category": "N/A", "frequency": "N/A", "final_volume": 0}
    
    similar_events = []
    used_categories = set()
    used_series = set()



    for event in comparable_events:
        category = event.get("category")
        series = event.get("series")
        
        # Only add the event if its category hasn't been used yet
        if category not in used_categories:
            if series not in used_series:
                similar_events.append(event)
                used_categories.add(series)
                #used_categories.add(category)

        
        
        # Stop once we have collected 8 similar events
        if len(similar_events) == 8:
            break
    

    all_events_for_template = similar_events[:4] + [main_event] + similar_events[4:]
    # 4. Render the new template, passing the three events
    return render_template(
        "compare.html",
        all_events = all_events_for_template,
        main_event = main_event
    )

if __name__ == "__main__":
    app.run(debug=True)
