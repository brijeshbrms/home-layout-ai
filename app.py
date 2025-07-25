# Improved version of your Streamlit home layout generator app

import streamlit as st
import json, difflib, os, re, time, logging
from gpt4all import GPT4All
import plotly.graph_objects as go
from layout_validation import (
    validate_layout,
    validate_within_plot,
    total_room_area,
    validate_total_area,
    reposition_rooms_to_fit
)
from prompt_generator_words import generate_prompt
from vastu_zones import validate_vastu, rotate_zone

# ---------------------- Config ----------------------
DB_PATH = "layouts_db.json"
TRAIN_PATH = "layout_training_data.json"
LAYOUT_VERSION = "v2.0"
MODEL_DIR = os.path.expanduser("~/Library/Application Support/nomic.ai/GPT4All")
MODEL_OPTIONS = {
    "Nous-Capybara-7B": "nous-capybara-7b.Q4_0.gguf",
    "DeepSeek-Coder": "deepseek-coder-6.7b-instruct.Q4_0.gguf",
}
logging.basicConfig(level=logging.INFO, filename="app.log", format="%(asctime)s - %(message)s")

# ---------------------- Prompt Enhancer ----------------------
def enhance_prompt_with_feedback(original_prompt, feedback_notes):
    additions = []
    for note in feedback_notes:
        if "Master Bedroom" in note and "North" in note:
            additions.append("Avoid placing Master Bedroom in North direction.")
        elif "Kitchen" in note and "Southwest" in note:
            additions.append("Avoid placing Kitchen in Southwest direction.")
        elif "rooms could not fit" in note:
            additions.append("Ensure all rooms fit within the given plot size.")
    if additions:
        return original_prompt.strip() + "\n\nNotes:\n" + "\n".join(additions)
    return original_prompt

# ---------------------- Utilities ----------------------
def extract_plot_dimensions(prompt):
    match_feet_inches = re.search(r"(\d{1,2})[’'](\d{1,2})?[”\"]?\s*[xX×]\s*(\d{1,2})[’'](\d{1,2})?[”\"]?", prompt)
    match_feet_only = re.search(r"(\d{2,3})\s*[xX×]\s*(\d{2,3})\s*ft", prompt)
    if match_feet_inches:
        w_ft = int(match_feet_inches.group(1))
        w_in = int(match_feet_inches.group(2) or 0)
        h_ft = int(match_feet_inches.group(3))
        h_in = int(match_feet_inches.group(4) or 0)
        return round(w_ft + w_in / 12, 2), round(h_ft + h_in / 12, 2)
    elif match_feet_only:
        return int(match_feet_only.group(1)), int(match_feet_only.group(2))
    return None, None

def clean_and_parse_layout(text):
    try:
        # Step 1: Clean model reply
        text = text.strip().split("Assistant:")[-1].strip()

        # Remove index prefixes like `0:{` or `1 : {`
        text = re.sub(r'\d+\s*:\s*\{', '{', text)

        # Step 2: Extract JSON-like array
        match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            # If no [] found, try to wrap entire content
            if text.startswith('{') and text.endswith('}'):
                json_text = f"[{text}]"
            else:
                st.error("❌ No valid JSON array found in model output.")
                return None

        #json_text = match.group(0)

        # Step 3: Fix common formatting issues

        # Convert single quotes to double quotes
        json_text = json_text.replace("'", '"')

        # Fix missing quotes around keys
        json_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_ ]*)\s*:', r'\1 "\2":', json_text)

        # Fix missing commas between objects
        json_text = re.sub(r'\}\s*\{', '}, {', json_text)

        # Remove trailing commas
        json_text = re.sub(r',\s*([\}\]])', r'\1', json_text)

        # Step 4: Parse
        parsed = json.loads(json_text)

        # Step 5: Validate structure
        if isinstance(parsed, list) and all(isinstance(r, dict) for r in parsed):
            return parsed

        st.error("⚠️ Parsed content is not a valid list of room dictionaries.")

    except Exception as e:
        st.error(f"❌ Error parsing model output: {e}")
        logging.exception("Layout parse failure")
        logging.error(f"Failed JSON: {json_text}")  # Log raw text if parsing fails

    return None
def load_layout_db():
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return []

def save_to_db(prompt, layout, is_valid=False):
    db = load_layout_db()
    db.append({"prompt": prompt, "layout": layout, "layout_version": LAYOUT_VERSION, "timestamp": time.time(), "valid": is_valid})
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)

def save_for_training(prompt, layout, tags=None):
    tags = tags or {}
    try:
        with open(TRAIN_PATH, 'r') as f:
            data = json.load(f)
    except:
        data = []
    data.append({"prompt": prompt, "layout": layout, "tags": tags})
    with open(TRAIN_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_closest_layout(prompt, threshold=0.6):
    db = load_layout_db()
    prompts = [entry["prompt"] for entry in db]
    match = difflib.get_close_matches(prompt, prompts, n=1, cutoff=threshold)
    return next(entry["layout"] for entry in db if entry["prompt"] == match[0]) if match else None

# ---------------------- Model Call ----------------------

# Estimate token needs based on plot area
def estimate_max_tokens(plot_width, plot_height):
    area = plot_width * plot_height
    if area <= 1000:
        return 400
    elif area <= 2500:
        return 600
    elif area <= 5000:
        return 800
    else:
        return 1024

def call_local_model(prompt, model_filename, plot_width, plot_height, max_tokens_override=None):
    model_path = os.path.join(MODEL_DIR, model_filename)
    model = GPT4All(model_name=os.path.basename(model_path), model_path=MODEL_DIR, allow_download=False)

    max_tokens = max_tokens_override if max_tokens_override else estimate_max_tokens(plot_width, plot_height)

    layout_prompt = f"""### Instruction:
    You are a layout planning AI that outputs room layouts in strict JSON format only.
    Design a vastu-compliant home layout to fit inside a plot of {plot_width}x{plot_height} feet.
    Only return a valid JSON array like:
    [
    {{ "name": "Living Room", "x": 0, "y": 0, "width": 14, "height": 16 }},
    {{ "name": "Kitchen", "x": 15, "y": 0, "width": 10, "height": 10 }}
    ]
    ### User Input:
    {prompt}
    ### Format:
    Return *only* a JSON array. Do NOT include comments or explanations.

    ### Response:
    """

    layout = None
    with model:
        for temp in [0.7, 0.5]:  # Retry with lower temp
            response = model.generate(layout_prompt, max_tokens=max_tokens, temp=temp).strip()
            st.sidebar.expander("🔍 Raw Model Response", expanded=False).write(response)
            layout = clean_and_parse_layout(response)
            if layout:
                break
            st.warning(f"⚠️ Invalid JSON returned at temp={temp}. Retrying...")

    if layout:
        layout.insert(0, {"name": "Plot", "x": 0, "y": 0, "width": plot_width, "height": plot_height})
        return layout
    else:
        st.error("❌ Model failed to return valid JSON after multiple attempts.")
    return None

def draw_layout(layout):
    fig = go.Figure()

    # Separate plot and rooms
    plot = next((r for r in layout if r["name"].lower() == "plot"), None)
    rooms = [r for r in layout if r["name"].lower() != "plot"]

    # Draw plot boundary
    if plot:
        fig.add_shape(
            type="rect",
            x0=plot["x"],
            y0=plot["y"],
            x1=plot["x"] + plot["width"],
            y1=plot["y"] + plot["height"],
            line=dict(color="black", width=3),
            fillcolor="rgba(240,240,240,0.3)"
        )
        fig.add_annotation(
            x=plot["x"] + plot["width"] / 2,
            y=plot["y"] + plot["height"] - 1,
            text=f"Plot ({plot['width']}x{plot['height']} ft)",
            showarrow=False,
            font=dict(size=12, color="gray")
        )

    # Draw rooms
    for r in rooms:
        fig.add_shape(
            type="rect",
            x0=r["x"],
            y0=r["y"],
            x1=r["x"] + r["width"],
            y1=r["y"] + r["height"],
            line=dict(color="blue"),
            fillcolor="lightblue"
        )
        fig.add_annotation(
            x=r["x"] + r["width"] / 2,
            y=r["y"] + r["height"] / 2,
            text=r["name"],
            showarrow=False,
            font=dict(size=12)
        )
        fig.add_annotation(
            x=r["x"] + r["width"] / 2,
            y=r["y"] + r["height"] + 0.5,
            text=f"{r['width']}x{r['height']} ft",
            showarrow=False,
            font=dict(size=10),
            xanchor="center"
        )
    # Get plot boundary
    plot_width = plot["width"]
    plot_height = plot["height"]

    padding = 5  # adjust as needed to zoom out

        
    fig.update_layout(
        height=600,
        title="🏠 2D Layout",
        xaxis=dict(showgrid=False, visible=False,range=[-padding, plot_width + padding]),
        yaxis=dict(showgrid=False, visible=False,range=[-padding, plot_height + padding]    ),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="white"
    )

    st.plotly_chart(fig, use_container_width=True)



# ---------------------- UI ----------------------
st.set_page_config(page_title="🏠 Home Layout Generator", layout="centered")
st.title("🏠 Home Layout Generator (Multi-Model GPT4All)")

model_choice = st.selectbox("🧠 Select Model", list(MODEL_OPTIONS.keys()))
user_prompt = st.text_area("Prompt", height=300, placeholder="Describe your home layout...")
vastu_enabled = st.checkbox("Vastu Compliant?")
force_generate = st.checkbox("🛠 Force generate layout")
entrance_direction = st.selectbox("Select Entrance Direction", ["North", "East", "South", "West"]) if vastu_enabled else None

if st.button("🚀 Generate Layout"):
    plot_width, plot_height = extract_plot_dimensions(user_prompt)
    if not plot_width or not plot_height:
        st.error("❌ Could not extract plot dimensions from prompt.")
        st.stop()

    layout = None
    if not force_generate:
        layout = get_closest_layout(user_prompt)
        if layout:
            st.success("✅ Reused layout from cache")
            st.json(layout)
            draw_layout(layout)

    if not layout:
        layout = call_local_model(user_prompt, MODEL_OPTIONS[model_choice], plot_width, plot_height)

    if layout:
        is_valid, adjusted_layout, unplaced = validate_layout(layout, plot_width, plot_height)
        vastu_issues = validate_vastu(adjusted_layout, plot_width, plot_height, entrance_direction) if vastu_enabled else []

        if is_valid and not vastu_issues:
            st.success("✅ Layout fits plot & vastu compliant")
        else:
            st.warning("⚠️ Issues detected — improving prompt...")
            notes = [f"{i['room']} is in {i['zone']}: {i['reason']}" for i in vastu_issues]
            if unplaced:
                notes.append("Some rooms could not fit")
            improved_prompt = enhance_prompt_with_feedback(user_prompt, notes)
            st.subheader("🧠 Improved Prompt Used:")
            st.code(improved_prompt)
            layout = call_local_model(improved_prompt, MODEL_OPTIONS[model_choice], plot_width, plot_height)
            is_valid, adjusted_layout, unplaced = validate_layout(layout, plot_width, plot_height)

        st.json(adjusted_layout)
        draw_layout(adjusted_layout)
        save_to_db(user_prompt, adjusted_layout, is_valid=False)

        with st.form("tag_save"):
            vastu = st.checkbox("Vastu Compliant?")
            bhk_type = st.selectbox("House Type", ["1BHK", "2BHK", "3BHK", "Other"])
            plot_size = st.text_input("Plot Size", f"{plot_width}x{plot_height}")
            if not re.match(r"^\d{2,3}\s*[xX×]\s*\d{2,3}$", plot_size.strip()):
                st.error("❌ Cannot save: Plot size format is invalid.")
                st.stop()
            valid = st.checkbox("Layout Valid (fits in plot)?", value=is_valid)
            warning_notes = st.text_area("Warnings / Notes", value="\n".join([f"{i['room']} in {i['zone']} – {i['reason']}" for i in vastu_issues] if vastu_issues else []))
            unplaced_count = len(unplaced) if unplaced else 0
            submit = st.form_submit_button("💾 Save Layout for Training")
        if submit:
            tags = {
                "vastu": vastu,
                "type": bhk_type,
                "plot_size": plot_size,
                "valid": valid,
                "warnings": warning_notes.splitlines(),
                "unplaced": unplaced_count,
            }
            save_for_training(user_prompt, layout, tags)
            st.success("📁 Layout tagged and saved to training set")
