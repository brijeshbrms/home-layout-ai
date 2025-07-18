from num2words import num2words

def num_to_words_ft(n):
    """Convert number to words followed by 'feet'"""
    return num2words(n).replace("-", " ") + " feet"

def hybrid_room_description(room):
    width_num = room["width"]
    height_num = room["height"]
    width_word = num_to_words_ft(width_num)
    height_word = num_to_words_ft(height_num)
    return f'- {room["name"]} ({width_num}x{height_num} ft / {width_word} by {height_word})'

def generate_prompt(plot_width, plot_height, rooms):
    """
    Generate a layout design prompt with both numbers and words.
    """
    plot_size_text = f"{plot_width}x{plot_height} ft ({num_to_words_ft(plot_width)} by {num_to_words_ft(plot_height)})"

    room_lines = [
        hybrid_room_description(r)
        for r in rooms
    ]

    prompt = f"""Design a 2BHK home layout for a plot of {plot_size_text}.
Include the following rooms:
""" + "\n".join(room_lines)

    return prompt