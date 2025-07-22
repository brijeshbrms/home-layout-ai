# vastu_zones.py



def validate_vastu_compliance(layout_json: dict) -> bool:
    # Placeholder logic
    return True
    # Returns True/False based on your logic
# Define the Vastu zones and room recommendations

vastu_rules = {
    "NE": {
        "allowed": ["Entrance", "Temple", "Meditation", "Porch", "Balcony", "Veranda", "Underground Water Tank"],
        "avoid": ["Toilet", "Septic Tank", "Kitchen"]
    },
    "N": {
        "allowed": ["Living Room", "Entrance", "Bathroom", "Treasury", "Open Space"],
        "avoid": ["Bedroom"]
    },
    "NW": {
        "allowed": ["Guest Bedroom", "Toilet", "Dining Room", "Study Room", "Elder's Room", "Parking", "Cow Shed"],
        "avoid": []
    },
    "E": {
        "allowed": ["Bathroom", "Living Room", "Study Room", "Open Space"],
        "avoid": []
    },
    "Center": {
        "allowed": ["Open Space", "Tulsi Plant"],
        "avoid": ["Heavy Structure", "Water Tank"]
    },
    "W": {
        "allowed": ["Dining Room", "Toilet", "Bathroom", "Staircase", "Store Tank", "Study Room"],
        "avoid": ["Cellar"]
    },
    "SW": {
        "allowed": ["Master Bedroom", "Staircase", "Wardrobe", "Closet"],
        "avoid": ["Cellar", "Well"]
    },
    "S": {
        "allowed": ["Bedroom", "Staircase", "Store Room"],
        "avoid": ["Cellar", "Well"]
    },
    "SE": {
        "allowed": ["Kitchen", "Store Room", "Electrical Panel", "Fireplace"],
        "avoid": ["Well", "Toilet", "Septic Tank"]
    }
}

# Utility to determine which Vastu zone a room falls into
def get_vastu_zone(room, plot_width, plot_height):
    x = room["x"] + room["width"] / 2
    y = room["y"] + room["height"] / 2

    zone_x = min(2, max(0, int((x / plot_width) * 3)))
    zone_y = min(2, max(0, int((y / plot_height) * 3)))

    grid = [
        ["NW", "N", "NE"],
        ["W", "Center", "E"],
        ["SW", "S", "SE"]
    ]

    return grid[zone_y][zone_x]

#from vastu_utils import rotate_zone  # Make sure this import exists

def validate_vastu(layout, plot_width, plot_height, entrance_direction):
    violations = []

    for room in layout:
        name = room["name"]
        if name.lower() == "plot":
            continue

        # Step 1: Get the original unrotated zone based on X,Y
        zone = get_vastu_zone(room, plot_width, plot_height)

        # Step 2: Rotate the zone as per entrance direction (East, West, etc.)
        rotated_zone = rotate_zone(zone, entrance_direction)

        # Step 3: Validate based on rotated zone's rules
        allowed = vastu_rules.get(rotated_zone, {}).get("allowed", [])
        avoid = vastu_rules.get(rotated_zone, {}).get("avoid", [])

        # Step 4: Check if the room is in avoid list
        for keyword in avoid:
            if keyword.lower() in name.lower():
                violations.append({
                    "room": name,
                    "zone": rotated_zone,
                    "reason": f"Avoided in {rotated_zone} zone as per {entrance_direction} entrance"
                })

    return violations

def rotate_zone(original_zone, entrance_direction):
    # clockwise rotation map
    clockwise_rotation = {
        "North": {"N": "N", "NE": "NE", "E": "E", "SE": "SE", "S": "S", "SW": "SW", "W": "W", "NW": "NW"},
        "East":  {"N": "W", "NE": "NW", "E": "N", "SE": "NE", "S": "E", "SW": "SE", "W": "S", "NW": "SW"},
        "South": {"N": "S", "NE": "SW", "E": "W", "SE": "NW", "S": "N", "SW": "NE", "W": "E", "NW": "SE"},
        "West":  {"N": "E", "NE": "SE", "E": "S", "SE": "SW", "S": "W", "SW": "NW", "W": "N", "NW": "NE"}
    }
    return clockwise_rotation[entrance_direction].get(original_zone, original_zone)
