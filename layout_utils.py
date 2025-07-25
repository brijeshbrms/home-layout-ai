import json, re, logging

def clean_and_parse_layout(text):
    try:
        text = text.strip().split("Assistant:")[-1].strip()
        text = re.sub(r'\d+\s*:\s*\{', '{', text)
        match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if not match:
            return None
        json_text = match.group(0).replace("'", '"')
        json_text = re.sub(r'([a-zA-Z0-9_])\s*:\s*("[^"]*")', r'"\1": \2', json_text)
        json_text = re.sub(r'([a-zA-Z0-9_])\s*:\s*(\d+)', r'"\1": \2', json_text)
        json_text = re.sub(r'\}\s*\{', '}, {', json_text)
        json_text = re.sub(r',\s*([\}\]])', r'\1', json_text)
        parsed = json.loads(json_text)
        return parsed if isinstance(parsed, list) else None
    except Exception as e:
        logging.exception("❌ JSON parse failed")
        return None
