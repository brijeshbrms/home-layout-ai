import json, os, time, gc
from gpt4all import GPT4All
from layout_utils import clean_and_parse_layout
from layout_validation import validate_layout
from vastu_zones import validate_vastu

# --- Config ---
PROMPT_FILE = "prompts/test_prompts_100.json"
MODEL_DIR = os.path.expanduser("~/Library/Application Support/nomic.ai/GPT4All")
model_filename = "nous-capybara-7b.Q4_0.gguf"
MODEL_PATH = os.path.join(MODEL_DIR, model_filename)


RESP_FILE = "results/responses.jsonl"
LAYOUT_FILE = "results/layouts_clean.jsonl"
FAIL_LOG = "results/failed_prompts.log"
MAX_TOKENS = 700
TEMP = 0.7
BATCH_SIZE = 20

os.makedirs("results", exist_ok=True)

def build_prompt(user_prompt):
    return f"""### Instruction:
You are a layout planning AI that returns room layouts in strict JSON format.
{user_prompt}

Return only a valid JSON array like:
[
  {{ "name": "Living Room", "x": 0, "y": 0, "width": 14, "height": 16 }},
  ...
]
### Response:"""


def save_jsonl(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def run_batch(prompts):
    print(f"🚀 Loading model: {os.path.basename(MODEL_PATH)}")
    model = GPT4All(model_name=os.path.basename(MODEL_PATH), model_path=os.path.dirname(MODEL_PATH), allow_download=False)

    with model:
        for i, prompt_entry in enumerate(prompts):
            prompt = prompt_entry["prompt"]
            layout_prompt = build_prompt(prompt)

            try:
                print(f"\n🧪 Prompt {i+1}/{len(prompts)}")
                response = model.generate(layout_prompt, max_tokens=MAX_TOKENS, temp=TEMP).strip()

                save_jsonl(RESP_FILE, {"prompt": prompt, "raw_response": response})

                layout = clean_and_parse_layout(response)
                if layout:
                    plot = next((r for r in layout if r["name"].lower() == "plot"), None)
                    if plot:
                        is_valid, adjusted_layout, unplaced = validate_layout(layout, plot["width"], plot["height"])
                        vastu_issues = validate_vastu(adjusted_layout, plot["width"], plot["height"], ENTRANCE_DIRECTION)

                        tags = {
                            "valid": is_valid,
                            "unplaced_count": len(unplaced),
                            "vastu_issues": vastu_issues
                        }

                        save_jsonl(LAYOUT_FILE, {
                            "prompt": prompt,
                            "layout": adjusted_layout,
                            "tags": tags
                        })

                        print(f"✅ Saved | Valid: {is_valid} | Vastu Issues: {len(vastu_issues)} | Unplaced: {len(unplaced)}")
                    else:
                        print("⚠️ No plot found in layout.")
                        with open(FAIL_LOG, "a") as f:
                            f.write(f"❌ No plot found: {prompt}\n")
                else:
                    with open(FAIL_LOG, "a") as f:
                        f.write(f"❌ Failed JSON parse: {prompt}\n")

                time.sleep(1.5)

            except Exception as e:
                with open(FAIL_LOG, "a") as f:
                    f.write(f"❌ Exception: {prompt[:80]} — {e}\n")

    del model
    gc.collect()

if __name__ == "__main__":
    with open(PROMPT_FILE, "r") as f:
        all_prompts = json.load(f)

    total = len(all_prompts)
    print(f"📦 Starting batch test of {total} prompts")

    for i in range(0, total, BATCH_SIZE):
        batch = all_prompts[i:i+BATCH_SIZE]
        print(f"\n⚙️ Batch {i+1} to {i+len(batch)}")
        run_batch(batch)
        print("🧹 Cooling system...")
        time.sleep(5)