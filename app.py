import streamlit as st
import json, difflib, os, re
from gpt4all import GPT4All
import plotly.graph_objects as go
from layout_validation import (
    validate_layout,
    validate_within_plot,
    total_room_area,
    validate_total_area,reposition_rooms_to_fit
)
from prompt_generator_words import generate_prompt
from vastu_zones import validate_vastu, rotate_zone

# ---------------------- clean_and_parse_layout ----------------------
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
        text = text.strip().split("Assistant:")[-1].strip()
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        json_text = match.group(0) if match else text
        json_text = json_text.replace("'", '"')
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*\]', ']', json_text)
        parsed = json.loads(json_text)
        if isinstance(parsed, list) and all(isinstance(r, dict) for r in parsed):
            return parsed
        st.error("❌ Output is not a valid list of room objects.")
    except Exception as e:
        st.error(f"❌ Error parsing model output: {e}")
    return None

# ---------------------- Config ----------------------
DB_PATH = "layouts_db.json"
TRAIN_PATH = "layout_training_data.json"
LAYOUT_VERSION = "v2.0"
MODEL_OPTIONS = {
    "Nous-Capybara-7B": "nous-capybara-7b.Q4_0.gguf",
    "DeepSeek-Coder": "deepseek-coder-6.7b-instruct.Q4_0.gguf",
}
MODEL_DIR = os.path.expanduser("~/Library/Application Support/nomic.ai/GPT4All")

# ---------------------- Utils ----------------------
def load_layout_db():
    try:
        with open(DB_PATH, 'r') as f: return json.load(f)
    except: return []

def save_to_db(prompt, layout):
    db = load_layout_db()
    db.append({"prompt": prompt, "layout": layout, "layout_version": LAYOUT_VERSION})
    with open(DB_PATH, 'w') as f: json.dump(db, f, indent=2)

def save_for_training(prompt, layout, tags=None):
    tags = tags or {}
    try:
        with open(TRAIN_PATH, 'r') as f: data = json.load(f)
    except: data = []
    data.append({"prompt": prompt, "layout": layout, "tags": tags})
    with open(TRAIN_PATH, 'w') as f: json.dump(data, f, indent=2)

def get_closest_layout(prompt, threshold=0.6):
    db = load_layout_db()
    prompts = [entry["prompt"] for entry in db]
    match = difflib.get_close_matches(prompt, prompts, n=1, cutoff=threshold)
    return next(entry["layout"] for entry in db if entry["prompt"] == match[0]) if match else None

# ---------------------- Model Integration ----------------------
def call_local_model(prompt, model_filename, plot_width, plot_height):
    model_path = os.path.join(MODEL_DIR, model_filename)
    model = GPT4All(model_name=os.path.basename(model_path), model_path=MODEL_DIR, allow_download=False)
    layout_prompt = f"""
    You are a home layout assistant. Design a vastu-compliant home layout that fits all rooms within the given plot size ({plot_width}x{plot_height} ft). Avoid placing all rooms in a straight line. Distribute rooms spatially in multiple directions.

    Return ONLY a JSON list of room objects like:
    [
      {{ "name": "Living Room", "x": 0, "y": 0, "width": 15, "height": 20 }},
      ...
    ]

    User: {prompt}
    """
    with model:
        response = model.generate(layout_prompt, max_tokens=1024, temp=0.7)
    st.subheader("🔎 Raw Model Output")
    st.code(response or "⚠️ No response", language="text")
    try:
        layout = clean_and_parse_layout(response)
        if not layout:
            raise ValueError("No JSON array found.")
        layout.insert(0, {"name": "Plot", "x": 0, "y": 0, "width": plot_width, "height": plot_height})
        return layout
    except Exception as e:
        st.error(f"❌ Layout parsing failed: {e}")
        return None

# ---------------------- Plotting ----------------------
def draw_layout(layout):
    if vastu:
        vastu_issues = validate_vastu(layout, plot_width, plot_height, entrance_direction)
        if vastu_issues:
            st.subheader("🟠 Vastu Compliance Warnings")
            for issue in vastu_issues:
                st.warning(f"{issue['room']} is in {issue['zone']}: {issue['reason']}")
        else:
            st.success("🧿 Vastu compliant ✅")
    fig = go.Figure()
    plot = next((r for r in layout if r["name"].lower() == "plot"), None)
    rooms = [r for r in layout if r["name"].lower() != "plot"]
    if plot:
        fig.add_shape(type="rect", x0=plot["x"], y0=plot["y"], x1=plot["x"] + plot["width"], y1=plot["y"] + plot["height"], line=dict(color="black", width=3), fillcolor="rgba(240,240,240,0.3)")
        fig.add_annotation(x=plot["x"] + plot["width"] / 2, y=plot["y"] + plot["height"] - 1, text=f"Plot ({plot['width']}x{plot['height']} ft)", showarrow=False, font=dict(size=12, color="gray"))
    for r in rooms:
        fig.add_shape(type="rect", x0=r["x"], y0=r["y"], x1=r["x"] + r["width"], y1=r["y"] + r["height"], line=dict(color="blue"), fillcolor="lightblue")
        fig.add_annotation(x=r["x"] + r["width"] / 2, y=r["y"] + r["height"] / 2, text=r["name"], showarrow=False, font=dict(size=12))
        fig.add_annotation(x=r["x"] + r["width"] / 2, y=r["y"] + r["height"] + 0.5, text=f"{r['width']}x{r['height']} ft", showarrow=False, font=dict(size=10), xanchor="center")
    if plot:
        cx, cy = plot["x"] + plot["width"] / 2, plot["y"] + plot["height"] / 2
        directions = [("North", cx, plot["y"] + plot["height"] + 1), ("South", cx, plot["y"] - 2), ("East", plot["x"] + plot["width"] + 1, cy), ("West", plot["x"] - 2, cy)]
        for name, x, y in directions:
            fig.add_annotation(text=name, x=x, y=y, showarrow=False, font=dict(size=10, color="gray"), xanchor="center", yanchor="middle", bgcolor="white")
    fig.update_layout(height=600, title="🏠 2D Layout", xaxis=dict(range=[0, plot["width"] + 2 if plot else 50], showgrid=False, visible=False), yaxis=dict(range=[0, plot["height"] + 2 if plot else 50], showgrid=False, visible=False), margin=dict(l=20, r=20, t=40, b=20), plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------- Streamlit UI ----------------------
st.set_page_config(page_title="🏠 Home Layout Generator (Offline)", layout="centered")
st.title("🏠 Home Layout Generator (Multi-Model GPT4All)")

model_choice = st.selectbox("🧠 Select Model", list(MODEL_OPTIONS.keys()))
user_prompt = st.text_area("Prompt", height=300, placeholder="Paste your custom layout prompt here...")
layout = None
vastu = st.checkbox("Vastu Compliant?")
force_generate = st.checkbox("🛠 Force generate from model (ignore cache)")
entrance_direction = st.selectbox("Select Entrance Direction", ["North", "East", "South", "West"]) if vastu else None

if st.button("🚀 Generate Layout"):
    layout = None
    if not force_generate:
        with st.spinner("🔎 Searching local cache..."):
            layout = get_closest_layout(user_prompt)

    if layout:
        st.success("✅ Reused layout from cache")
        st.json(layout)
        draw_layout(layout)
    else:
        with st.spinner("🤖 Generating via model..."):
            plot_width, plot_height = extract_plot_dimensions(user_prompt)
            if not plot_width or not plot_height:
                st.error("❌ Could not extract plot dimensions from prompt.")
                st.stop()
            layout = call_local_model(user_prompt, MODEL_OPTIONS[model_choice], plot_width, plot_height)

        if layout:
            is_valid, adjusted_layout, unplaced = validate_layout(layout, plot_width, plot_height)
            if is_valid:
                st.success("✅ Layout fits plot 🟢")
                st.json(adjusted_layout)
                draw_layout(adjusted_layout)
                if vastu:
                    vastu_issues = validate_vastu(adjusted_layout, plot_width, plot_height, entrance_direction)
                    if vastu_issues:
                        st.subheader("🟠 Vastu Warnings")
                        for issue in vastu_issues:
                            st.warning(f"{issue['room']} is in {issue['zone']}: {issue['reason']}")
                    else:
                        st.success("🧿 Vastu compliant ✅")
                save_to_db(user_prompt, adjusted_layout)
            else:
                st.error("🚫 Rooms exceed plot bounds or area")
                st.json(adjusted_layout)
                if unplaced:
                    st.warning("📛 Rooms couldn't fit:")
                    for r in unplaced:
                        st.markdown(f"- **{r['name']}** ({r['width']}x{r['height']} ft)")
        else:
            st.error("❌ Model failed to generate layout")

if layout:
    with st.form("tag_save"):
        vastu = st.checkbox("Vastu Compliant?")
        bhk_type = st.selectbox("House Type", ["1BHK", "2BHK", "3BHK", "Other"])
        plot_size = st.text_input("Plot Size", f"{plot_width}x{plot_height}")
        submit = st.form_submit_button("💾 Save Layout for Training")
        if submit:
            save_for_training(user_prompt, layout, {"vastu": vastu, "type": bhk_type, "plot_size": plot_size})
            st.success("📁 Layout tagged and saved")

if st.checkbox("📚 View All Saved Layouts"):
    for entry in load_layout_db():
        with st.expander(entry["prompt"]):
            st.caption(f'🧩 Layout Version: {entry.get("layout_version", "v1.0")}')
            st.json(entry["layout"])
