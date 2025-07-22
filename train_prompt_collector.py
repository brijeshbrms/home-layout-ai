import streamlit as st
import json
import time
from layout_validation import extract_plot_dimensions, clean_and_parse_layout, validate_layout
from vastu_zones import validate_vastu
import psutil
from gpt4all import GPT4All
import gc
import os

MODEL_NAME = "nous-capybara-7b.Q4_0.gguf"

st.title("🧠 Auto-Training Prompt Collector")



@st.cache_resource
def load_model():
    model_name = "nous-capybara-7b.Q4_0.gguf"
    model_path = "/Users/brijeshkumaryadav/Library/Application Support/nomic.ai/GPT4All"
    
    return GPT4All(
        model_name=model_name,
        model_path=model_path,
        allow_download=False
    )


uploaded_file = st.file_uploader("📂 Upload Prompt Batch File (.txt)", type=["txt"])

if uploaded_file:
    prompts = uploaded_file.read().decode("utf-8").strip().split("\n")
    prompts = [p.strip() for p in prompts if p.strip()]
    st.success(f"Loaded {len(prompts)} prompts.")

    batch_size = st.number_input("Prompts per batch", min_value=1, max_value=20, value=5)

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

cooldown_sec = st.sidebar.slider("🧨 Cooldown time between batches (seconds)", min_value=5, max_value=120, value=40, step=5)
skip_cooldown = st.sidebar.checkbox("🚫 Skip cooldown between batches", value=False)

if st.button("🚀 Run Batch"):
    model = load_model()
    all_passed, all_failed = [], []

    total_batches = (len(prompts) + batch_size - 1) // batch_size

    for batch_index, i in enumerate(range(0, len(prompts), batch_size)):
        batch = prompts[i:i + batch_size]

        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        st.sidebar.markdown(
            f"**🧠 Batch {batch_index + 1}/{total_batches}**  \n"
            f"📠 **RAM Usage:** {mem.percent}%  \n"
            f"⚙️ **CPU Usage:** {cpu}%"
        )

        st.markdown(f"### 🚀 Processing Batch {batch_index + 1} of {total_batches}")
        passed, failed = process_batch(batch, start_index=i, model=model)
        all_passed.extend(passed)
        all_failed.extend(failed)

        if batch_index + 1 < total_batches and not skip_cooldown:
            st.info(f"🧨 Cooling down for {cooldown_sec} seconds before next batch...")
            gc.collect()
            time.sleep(cooldown_sec)

    if all_passed:
        output_file = "finetune_dataset.jsonl"
        with open(output_file, "w") as f:
            for entry in all_passed:
                f.write(json.dumps(entry) + "\n")
        with open(output_file, "rb") as f:
            st.download_button("📅 Download Fine-Tune Dataset", f, file_name=output_file)

    st.markdown("### 📊 Summary")
    st.info(f"🟢 Passed: {len(all_passed)} / 🔴 Failed: {len(all_failed)} / 🧲 Total: {len(prompts)}")