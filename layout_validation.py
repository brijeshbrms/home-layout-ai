# layout_validation.py

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