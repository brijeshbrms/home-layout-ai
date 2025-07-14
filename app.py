import streamlit as st
import requests
import json
import difflib
import plotly.graph_objects as go

# ---------------------- Config ----------------------
DB_PATH = "layouts_db.json"
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
API_KEY = st.secrets["huggingface_token"]
headers = {"Authorization": f"Bearer {API_KEY}"}

# ---------------------- Data Utils ----------------------
def load_layout_db():
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return []

def save_to_db(prompt, layout):
    db = load_layout_db()
    db.append({"prompt": prompt, "layout": layout})
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)

def get_closest_layout(prompt, threshold=0.6):
    db = load_layout_db()
    prompts = [entry["prompt"] for entry in db]
    closest_match = difflib.get_close_matches(prompt, prompts, n=1, cutoff=threshold)
    if closest_match:
        for entry in db:
            if entry["prompt"] == closest_match[0]:
                return entry["layout"]
    return None

# ---------------------- Mistral API Call ----------------------
def call_mistral_api(prompt):
    full_prompt = f"""
You are a layout generator assistant.
Return a JSON list of rooms with fields: name, x, y, width, height.
Each room must fit within plot size. Format:
[
  {{ "name": "Living Room", "x": 0, "y": 0, "width": 15, "height": 20 }},
  ...
]
User request: {prompt}
Respond ONLY with JSON.
"""
    response = requests.post(API_URL, headers=headers, json={"inputs": full_prompt})
    try:
        raw = response.json()[0]["generated_text"]
        json_start = raw.find("[")
        return json.loads(raw[json_start:])
    except:
        return None

# ---------------------- Plotting ----------------------
def draw_layout(layout):
    fig = go.Figure()
    for room in layout:
        fig.add_shape(
            type="rect",
            x0=room["x"], y0=room["y"],
            x1=room["x"] + room["width"], y1=room["y"] + room["height"],
            line=dict(color="blue"), fillcolor="lightblue"
        )
        fig.add_annotation(
            x=room["x"] + room["width"] / 2,
            y=room["y"] + room["height"] / 2,
            text=room["name"], showarrow=False
        )
    fig.update_layout(height=600, width=800, title="2D Layout")
    st.plotly_chart(fig)

# ---------------------- Streamlit App ----------------------
st.set_page_config(page_title="🏠 Home Layout AI", layout="centered")
st.title("🏠 Home Layout Generator (Free + Smart Caching)")

user_prompt = st.text_area("Enter your home layout request:", "Design a 2BHK on a 30x40 ft plot")

if st.button("Generate Layout"):
    with st.spinner("Searching local layouts..."):
        layout = get_closest_layout(user_prompt)

    if layout:
        st.success("Found similar layout in local cache 🎯")
        st.json(layout)
        draw_layout(layout)
    else:
        st.warning("No match found. Calling Mistral API...")
        layout = call_mistral_api(user_prompt)
        if layout:
            st.success("New layout generated and saved ✅")
            st.json(layout)
            draw_layout(layout)
            save_to_db(user_prompt, layout)
        else:
            st.error("Failed to generate layout. Try again.")

if st.checkbox("🔍 Browse all saved layouts"):
    db = load_layout_db()
    for entry in db:
        with st.expander(entry["prompt"]):
            st.json(entry["layout"])
