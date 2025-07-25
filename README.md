import streamlit as st
import json
import time
from layout_validation import extract_plot_dimensions, clean_and_parse_layout, validate_layout
from vastu_zones import validate_vastu
import psutil
from gpt4all import GPT4All
from pathlib import Path
import gc
import os
from datetime import datetime
from collections import defaultdict
import pandas as pd

— Constants —

MODEL_PATH = os.path.expanduser(”~/Library/Application Support/nomic.ai/GPT4All/nous-capybara-7b.Q4_0.gguf”)
OUTPUT_FILE = “finetune_dataset.jsonl”
FAILED_FILE = “failed_dataset.jsonl”

— Title —

st.title(“🧠 Auto-Training Prompt Collector”)

— Load Local Model —

@st.cache_resource
def load_model():
MODEL_PATH = Path.home() / “Library/Application Support/nomic.ai/GPT4All”
MODEL_FILE = “nous-capybara-7b.Q4_0.gguf”

full_model_path = MODEL_PATH / MODEL_FILE
if not full_model_path.exists():
    raise FileNotFoundError(f"❌ Model file not found at: {full_model_path}")

return GPT4All(
    model_path=str(MODEL_PATH),
    model_name=MODEL_FILE,
    allow_download=False,
    verbose=True
)

— Upload Prompt File —

uploaded_file = st.file_uploader(“📂 Upload Prompt Batch File (.txt)”, type=[“txt”])

if uploaded_file:
content = uploaded_file.read().decode(“utf-8”)
prompts = [p.strip() for p in content.split(”\n\n”) if p.strip()]
st.success(f”📥 Loaded {len(prompts)} prompts.”)

batch_size = st.number_input("📦 Prompts per batch", min_value=1, max_value=20, value=5)

— Sidebar Settings —

cooldown_sec = st.sidebar.slider(“🧊 Cooldown time (sec)”, min_value=5, max_value=120, value=40)
skip_cooldown = st.sidebar.checkbox(“🚫 Skip cooldown between batches”, value=False)
show_raw = st.sidebar.checkbox(“🪵 Show Raw Model Output”, value=False)

— Process Batch —

def process_batch(batch, start_index=0, model=None):
passed, failed = [], []

for i, prompt in enumerate(batch):
    st.markdown(f"#### 🔹 Prompt {start_index + i + 1}")
    st.code(prompt)

    plot_width, plot_height = extract_plot_dimensions(prompt)
    if not plot_width or not plot_height:
        st.warning("⚠️ Could not extract plot dimensions")
        failed.append({"prompt": prompt, "reason": "Invalid plot size"})
        continue

    try:
        layout_raw = model.generate(prompt, max_tokens=800)
        if show_raw:
            st.text_area("🧾 Raw Model Output", layout_raw, height=200)

        layout = clean_and_parse_layout(layout_raw)
        if layout is None:
            raise ValueError("Model returned no layout")

        vastu_issues = validate_vastu(layout, plot_width, plot_height, entrance_direction="North")
        if vastu_issues:
            st.error("❌ Failed Vastu Compliance")
            failed.append({"prompt": prompt, "layout": layout, "issues": vastu_issues})
        else:
            st.success("✅ Passed Vastu Compliance")
            passed.append({
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": json.dumps(layout)}
                ]
            })

    except Exception as e:
        st.error(f"⚠️ Exception: {e}")
        failed.append({"prompt": prompt, "error": str(e)})

    time.sleep(1.5)

return passed, failed

— Run Button —

if st.button(“🚀 Run Batch”):
try:
model = load_model()
except Exception as e:
st.error(f”❌ Failed to load model: {e}”)
st.stop()

all_passed, all_failed = [], []
total_batches = (len(prompts) + batch_size - 1) // batch_size

for batch_index, i in enumerate(range(0, len(prompts), batch_size)):
    batch = prompts[i:i + batch_size]

    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    st.sidebar.markdown(
        f"**🧠 Batch {batch_index + 1}/{total_batches}**  \n"
        f"💾 **RAM Usage:** {mem.percent}%  \n"
        f"⚙️ **CPU Usage:** {cpu}%"
    )

    with st.spinner(f"Processing batch {batch_index + 1}..."):
        passed, failed = process_batch(batch, start_index=i, model=model)
    all_passed.extend(passed)
    all_failed.extend(failed)

    st.sidebar.info(f"✅ Batch {batch_index + 1} complete: {len(passed)} passed, {len(failed)} failed")

    if batch_index + 1 < total_batches and not skip_cooldown:
        st.info(f"🧊 Cooling down for {cooldown_sec} seconds...")
        gc.collect()
        time.sleep(cooldown_sec)

del model
gc.collect()

# --- Save Passed Prompts (Merge + De-duplicate) ---
existing_data, existing_prompts = [], set()
if os.path.exists(OUTPUT_FILE):
    backup_name = OUTPUT_FILE.rstrip(".jsonl") + f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.jsonl"
    os.rename(OUTPUT_FILE, backup_name)

    with open(backup_name, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                existing_data.append(entry)
                prompt_text = entry.get("messages", [{}])[0].get("content", "").strip().lower().replace("  ", " ")
                existing_prompts.add(prompt_text)
            except Exception:
                continue

new_entries = []
for entry in all_passed:
    prompt_text = entry.get("messages", [{}])[0].get("content", "").strip().lower().replace("  ", " ")
    if prompt_text not in existing_prompts:
        new_entries.append(entry)
        existing_prompts.add(prompt_text)

final_data = existing_data + new_entries

with open(OUTPUT_FILE, "w") as f:
    for entry in final_data:
        f.write(json.dumps(entry) + "\n")

with open(OUTPUT_FILE, "rb") as f:
    st.download_button("📥 Download Fine-Tune Dataset", f, file_name=OUTPUT_FILE)

# --- Save Failed Prompts ---
if all_failed:
    with open(FAILED_FILE, "w") as f:
        for entry in all_failed:
            f.write(json.dumps(entry) + "\n")
    with open(FAILED_FILE, "rb") as f:
        st.download_button("⚠️ Download Failed Dataset", f, file_name=FAILED_FILE)

# --- Error Summary by Category ---
error_groups = defaultdict(list)
for fail in all_failed:
    key = fail.get("reason") or fail.get("error", "Unknown Error")
    error_groups[key].append(fail["prompt"])

for err_type, examples in error_groups.items():
    st.error(f"{err_type}: {len(examples)} cases")

# --- CSV Export ---
df = pd.DataFrame([
    {"prompt": p.get("prompt"), "status": "failed"} for p in all_failed
] + [
    {"prompt": p["messages"][0]["content"], "status": "passed"} for p in all_passed
])

csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📊 Export CSV Summary", csv, file_name="prompt_summary.csv")

# --- Final Summary ---
st.markdown("### 📊 Summary")
st.success(f"🆕 New Prompts Added: {len(new_entries)}")
st.info(f"📁 Duplicates Skipped: {len(all_passed) - len(new_entries)}")
st.info(f"🟢 Passed: {len(all_passed)} / 🔴 Failed: {len(all_failed)} / 🧮 Total: {len(prompts)}")