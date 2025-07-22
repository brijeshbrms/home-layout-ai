🏡 Home Layout AI – Vastu-Compliant Home Design Generator

An intelligent, locally-run AI application that generates 2D home layout designs based on user prompts, ensuring Vastu compliance. Powered by GPT4All running fully offline using models like Nous-Capybara-7B and built with Streamlit.

⸻

🚀 Features
	•	✅ Offline Local LLM (GPT4All) inference for layout generation
	•	📐 Extracts plot size directly from natural language prompts
	•	🧭 Vastu-compliant validation using custom directional zoning (NE/NW/SW/SE)
	•	📊 Real-time RAM & CPU usage tracking while running batches
	•	🔄 Batch prompt processor to automate fine-tuning dataset generation
	•	🧠 Prompt generator module to dynamically create training prompts
	•	💾 Generates .jsonl dataset files for LLM training or analysis

⸻

📂 Project Structure

├── app.py                        # Streamlit app for layout generation
├── train_prompt_collector.py     # Batch processing and prompt collector
├── layout_validation.py          # Layout and plot validation logic
├── vastu_zones.py                # Vastu zone rules and validation
├── prompt_generator_words.py     # Prompt auto-generation logic
├── test_batch_prompts.py         # Batch prompt testing utility
├── finetune_dataset.jsonl        # Output dataset for LLM fine-tuning
├── vastu_3bhk_prompts_batch.txt  # Sample batch input file
├── layouts_db.json               # Layout cache file


⸻

🧠 Model Info
	•	🔧 Model Used: nous-capybara-7b.Q4_0.gguf
	•	🗂 Path: ~/Library/Application Support/nomic.ai/GPT4All/nous-capybara-7b.Q4_0.gguf
	•	⚙️ Make sure to download and place the model in the path above.

You can customize model names in the code using MODEL_FILE and MODEL_NAME variables.

⸻

🛠️ Setup Instructions

1. Clone the repository

git clone https://github.com/yourusername/home-layout-ai.git
cd home-layout-ai

2. Set up virtual environment (recommended)

python3 -m venv venv
source venv/bin/activate  # For Mac/Linux
venv\Scripts\activate     # For Windows

3. Install dependencies

pip install -r requirements.txt

4. Download your model manually

Place nous-capybara-7b.Q4_0.gguf inside:

~/Library/Application Support/nomic.ai/GPT4All/

5. Run the Streamlit App

streamlit run app.py  # for the main UI

6. Run the Prompt Collector (Batch Processing)

streamlit run train_prompt_collector.py


⸻

🧪 Sample Prompt

Design a 3BHK for a 30' x 50' plot. Master Bedroom in SW, Kitchen in SE, Living Room in NE.


⸻

📦 Output Format (Finetune Dataset)

Each passed layout is stored as:

{
  "messages": [
    {"role": "user", "content": "<your prompt>"},
    {"role": "assistant", "content": "<generated layout JSON>"}
  ]
}

Used for training or fine-tuning LLMs.

⸻

📊 Real-Time Monitoring
	•	View RAM and CPU usage in the Streamlit sidebar.
	•	Toggle cooldown and set wait time between batches.

⸻

📥 Dataset Generation Flow
	1.	Upload a .txt file with prompts (1 per line)
	2.	Configure batch size and cooldown
	3.	Run batch processing
	4.	Download fine-tune ready .jsonl file

⸻

📸 Screenshots

[Add screenshots here of app.py UI, layout outputs, batch processing, and summary stats.]

⸻

🧱 Roadmap
	•	Dynamic prompt parser
	•	Vastu-compliance engine
	•	Batch mode with live system stats
	•	Add 2D Plotly visualization (next)
	•	Hugging Face Space integration

⸻

🧑‍💻 Author

Brijesh Kumar Yadav
Engineer | Project Manager | AI Builder
📧 [Optional email]
🔗 [LinkedIn Profile]
🔗 GitHub

⸻

📄 License

This project is licensed under the MIT License.

⸻

🙏 Acknowledgements
	•	GPT4All by Nomic AI
	•	Streamlit
	•	Plotly
	•	Open-source Vastu reference materials