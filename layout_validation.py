# layout_validation.py

import re
import json
import streamlit as st

def clean_and_parse_layout(text):
    try:
        # Remove unwanted prefixes or artifacts
        text = text.strip()
        if "Assistant:" in text:
            text = text.split("Assistant:")[-1].strip()

        # Try to extract JSON array using regex if present in noisy text
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            json_text = text  # fallback

        # Standardize quotes and spacing
        json_text = json_text.replace("'", '"')
        json_text = re.sub(r',\s*}', '}', json_text)  # Remove trailing commas
        json_text = re.sub(r',\s*\]', ']', json_text)

        parsed = json.loads(json_text)

        if isinstance(parsed, list) and all(isinstance(r, dict) for r in parsed):
            return parsed
        else:
            st.error("❌ Output is not a valid list of room objects.")
            return None
    except Exception as e:
        st.error(f"❌ Error parsing model output: {e}")
        return None


def extract_plot_dimensions(prompt):
    """
    Extract plot width and height in inches from a prompt string.
    Returns: width, height as float (in feet)
    """
    match_feet_inches = re.search(r"(\d{1,2})[’'](\d{1,2})?[”\"]?\s*[xX×]\s*(\d{1,2})[’'](\d{1,2})?[”\"]?", prompt)
    match_feet_only = re.search(r"(\d{2,3})\s*[xX×]\s*(\d{2,3})\s*ft", prompt)

    if match_feet_inches:
        w_ft = int(match_feet_inches.group(1))
        w_in = int(match_feet_inches.group(2) or 0)
        h_ft = int(match_feet_inches.group(3))
        h_in = int(match_feet_inches.group(4) or 0)
        width = round(w_ft + w_in / 12, 2)
        height = round(h_ft + h_in / 12, 2)
        return width, height

    elif match_feet_only:
        width = int(match_feet_only.group(1))
        height = int(match_feet_only.group(2))
        return width, height

    return None, None  # If no match

def validate_layout(layout, plot_width, plot_height):
    # Remove 'Plot' room if already present
    rooms = [room for room in layout if room["name"].lower() != "plot"]

    # Reposition rooms to fit within plot
    repositioned, unplaced = reposition_rooms_to_fit(rooms, plot_width, plot_height)

    # Add back the Plot room as boundary
    plot_room = {
        "name": "Plot",
        "x": 0,
        "y": 0,
        "width": plot_width,
        "height": plot_height
    }
    full_layout = [plot_room] + repositioned

    # Check if all rooms are placed
    if unplaced:
        return False, full_layout, unplaced

    return True, full_layout, []

def total_room_area(rooms):
    return sum(r["width"] * r["height"] for r in rooms if r["name"].lower() != "plot")

def validate_within_plot(layout, plot_width, plot_height):
    for room in layout:
        if room["name"].lower() == "plot":
            continue
        if (room["x"] + room["width"] > plot_width or
            room["y"] + room["height"] > plot_height):
            return False
    return True

def validate_total_area(layout, plot_width, plot_height):
    plot_area = plot_width * plot_height
    used_area = total_room_area(layout)
    return used_area <= plot_area

def reposition_rooms_to_fit(rooms, plot_width, plot_height, spacing=1):
    x, y = 0, 0
    max_row_height = 0
    placed = []
    unplaced = []

    for room in rooms:
        width = room["width"]
        height = room["height"]

        if x + width > plot_width:
            x = 0
            y += max_row_height + spacing
            max_row_height = 0

        if y + height > plot_height:
            unplaced.append(room)
            continue

        placed.append({
            "name": room["name"],
            "x": x,
            "y": y,
            "width": width,
            "height": height
        })

        x += width + spacing
        max_row_height = max(max_row_height, height)

    return placed, unplaced