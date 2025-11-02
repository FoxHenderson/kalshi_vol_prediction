import os
import json 
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from google import genai
from google.genai import types

# --- Load environment variables from the .env file ---
load_dotenv() 

app = Flask(__name__)

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
    return random.randint(100000, 999999)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    topic = request.form.get("topic")

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
            "prediction_text": types.Schema(type=types.Type.STRING, description="A creative, short prediction based on the topic, category, and frequency.")
        },
        required=["category", "frequency"]
    )
    
    # --- New Combined Prompt ---
    # Simplified prompt to instruct model to generate JSON directly based on schema
    full_prompt = (
        "You are a mystical, predictive MetaBall. A user has provided a **TITLE** of an event. "
        "Analyze this title and output a suitable **Category** (from the exact list: "
        "['financials', 'crypto', 'sports', 'mentions', 'world', 'entertainment', 'social', 'climate and weather']), "
        "and the **Frequency** this type of event occurs (e.g., 'Yearly' for a league winner, 'Daily' for breaking news). "
        "Generate a JSON object that strictly conforms to the provided schema and contains ONLY the required fields.\n\n"
        f"Analyze this prediction title: '{topic}'"
    )
    
    # FIX: Initialize json_text before the try block to avoid UnboundLocalError
    json_text = ""

    try:
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            # FIX: Use the standard Python list-of-dicts structure for contents
            # This is more robust against the positional argument error.
            contents = [
                {
                    "role": "user", 
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            config=types.GenerateContentConfig(
                # CRITICAL FIX: Force model to output raw JSON text based on schema
                response_mime_type="application/json",
                response_schema=output_schema
            )
        )

        # CRITICAL FIX: Read the JSON text directly from the response
        # This will safely assign a value to json_text
        json_text = response.text.strip()
        
        # DEBUGGING: Print the raw output to the server console
        print(f"RAW LLM JSON: {json_text}")

        # RESILIENCY FIX: Strip common markdown code fences before parsing
        if json_text.startswith("```json"):
            json_text = json_text.lstrip("```json").rstrip("```").strip()
        elif json_text.startswith("```"):
            json_text = json_text.lstrip("```").rstrip("```").strip()
        # End RESILIENCY FIX

        llm_data = json.loads(json_text)


        interpolated_volume = generate_six_digit_id()

        new_id = "USER_INPUT"
        new_event = {
            "id": new_id,
            "title": topic,
            "category": llm_data["category"],
            "frequency": llm_data["frequency"],
            "volume": interpolated_volume,
            "is_dynamic": True
        }


        temp_predictions[new_id] = new_event
        return redirect(url_for("compare_events", event_id=new_id))


      #  final_prediction = (
       #     f"**TITLE:** {topic}<br>"
        #    f"**CATEGORY:** {llm_data['category']}<br>"
         #   f"**FREQUENCY:** {llm_data['frequency']}"
        #)
        #return jsonify({"result": final_prediction})
        
    except Exception as e:
        # If there's an error in parsing the response.text, it lands here.
        # json_text is now guaranteed to exist, even if it's empty.
        debug_message = f"Error: Parsing failed. Raw response was: {json_text}"
        print(f"Gemini Prediction Error (Parsing Failed): {e}. Raw Text: {json_text}")
        return jsonify({"result": debug_message})







DATA_FILE = 'similar_events.json'

def load_all_events():
    """Loads and returns all data from the JSON file."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found. Returning empty list.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {DATA_FILE}. Returning empty list.")
        return []

    all_events.extend(list(temp_predictions.values()))

    return all_events

@app.route("/<int:event_id>")
def compare_events(event_id):
    # 1. Load all data
    all_events = load_all_events()

    # 2. Find the user-specified event (the central column item)
    main_event = next((e for e in all_events if e.get("id") == event_id), None)

    if not main_event:
        return f"Error: Event with ID {event_id} not found.", 404
    
    # Ensure the main event has a volume attribute
    main_volume = main_event.get("volume")
    if main_volume is None or not isinstance(main_volume, (int, float)):
        return f"Error: Main event (ID {event_id}) does not have a valid 'volume' attribute for comparison.", 400

    # 3. Find two similarly scored events based on volume
    
    # Filter out the main event and any events without a valid volume
    comparable_events = [
        e for e in all_events 
        if e.get("id") != event_id and isinstance(e.get("volume"), (int, float))
    ]

    # Calculate the similarity score (absolute difference in volume)
    # The event is "more similar" if the absolute difference is smaller.
    def volume_difference(event):
        return abs(event.get("volume") - main_volume)

    # Sort the comparable events using the difference function
    comparable_events = [
        e for e in all_events 
        if e.get("id") != event_id and isinstance(e.get("volume"), (int, float))
    ]

    # Calculate the similarity score (absolute difference in volume)
    def volume_difference(event):
        return abs(event.get("volume") - main_volume)

    # Sort the comparable events using the difference function
    comparable_events.sort(key=volume_difference)

    # Take the two most similar events
    # Use dummy data if static data runs out, to prevent index errors
    DUMMY_EVENT = {"id": 0, "title": "No Similar Event Found", "category": "N/A", "frequency": "N/A", "volume": 0}
    
    left_event = comparable_events[0] if len(comparable_events) > 0 else DUMMY_EVENT
    right_event = comparable_events[1] if len(comparable_events) > 1 else DUMMY_EVENT

    # 4. Render the new template, passing the three events
    return render_template(
        "compare.html",
        left_event=left_event,
        main_event=main_event,
        right_event=right_event
    )

if __name__ == "__main__":
    app.run(debug=True)


if __name__ == "__main__":
    app.run(debug=True)




