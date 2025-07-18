import json
from pathlib import Path
from app_modules.generator import call_local_model  # adjust path if needed
from app_modules.vastu_rules import apply_vastu_rules  # optional
from app_modules.layout_renderer import render_layout_plotly  # optional

MODEL_PATH = "models/Nous-Capybara-7B-GGUF/capybara.Q4_K_M.gguf"  # adjust as needed
PROMPT_FILE = "vastu_3bhk_prompts_batch.txt"
OUTPUT_FOLDER = "test_results"

Path(OUTPUT_FOLDER).mkdir(exist_ok=True)

def load_prompts(file_path):
    with open(file_path, "r") as f:
        prompts = [line.strip() for line in f if line.strip()]
    return prompts

def run_batch_test():
    prompts = load_prompts(PROMPT_FILE)

    for i, prompt in enumerate(prompts):
        print(f"Processing prompt {i + 1}/{len(prompts)}...")

        try:
            # Call your local model
            layout = call_local_model(prompt, MODEL_PATH)

            # Save layout output
            with open(f"{OUTPUT_FOLDER}/layout_{i + 1}.json", "w") as out_file:
                json.dump(layout, out_file, indent=2)

            # Optional: Render layout to HTML for visual inspection
            # fig = render_layout_plotly(layout)
            # fig.write_html(f"{OUTPUT_FOLDER}/layout_{i + 1}.html")

        except Exception as e:
            print(f"Error processing prompt {i + 1}: {e}")

    print("✅ Batch testing completed.")

if __name__ == "__main__":
    run_batch_test()
