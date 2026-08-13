import os
import re
import json
import time
import requests

# 1. 9 Gemini API Keys Loading
KEYS_ENV = os.environ.get("GEMINI_API_KEYS", "")
API_KEYS = [k.strip() for k in KEYS_ENV.split(",") if k.strip()]

if not API_KEYS:
    print("❌ Error: GEMINI_API_KEYS Secret nahi mila.")
    exit(1)

print(f"✅ Total {len(API_KEYS)} Gemini API Keys loaded successfully! Rocket speed unlocked 🚀")

input_file = "american.oxt"
output_file = "american_roman.oxt"
checkpoint_file = "translation_checkpoint.json"
batch_size = 20  # Wapas 20 ki speed par aagaye!
MODEL_NAME = "gemini-1.5-flash-latest"

curr_key_idx = 0

# 2. Strict Prompt for Natural Pakistani Urdu
SYSTEM_PROMPT = """You are a native Pakistani video game localization expert for Max Payne 3.
Translate English game dialogues into NATURAL, FLUENT, and DRAMATIC Pakistani Roman Urdu (WhatsApp style).

STRICT OUTPUT FORMAT:
You MUST respond with ONLY a valid JSON object matching the exact input keys. Do not add markdown formatting or conversational filler.

TRANSLATION & VOCABULARY RULES:
1. Translate into natural spoken Pakistani dialogue tone (NO LITERAL WORD-FOR-WORD TRANSLATION).
2. STRICTLY FORBIDDEN HINDI WORDS:
   - NEVER use 'shareer' -> use 'jism' or 'body'
   - NEVER use 'samay' -> use 'waqt' or 'time'
   - NEVER use 'dard nivaarak' -> use 'painkillers'
   - NEVER use 'swasthya' -> use 'sehat'
   - NEVER use 'karya' -> use 'kaam'
   - NEVER use 'bhavnaon' -> use 'ehsaas'
   - NEVER use 'khojne' -> use 'dhoondne'
   - NEVER use 'vishesh' -> use 'khaas'
   - NEVER use 'vah' -> use 'woh'
   - NEVER use 'ladaai' -> use 'larai'
   - NEVER use 'badi' / 'bada' -> use 'bari' / 'bara'
3. KEEP GAMING TERMS: Keep 'painkillers', 'ammo', 'guns', 'checkpoint', 'comfort zone', 'health', 'plan B' in English as used in normal Urdu conversation.
4. FORMATTING TAGS: Keep all formatting tags (~z~, ~w~, ~n~, ~a~, ~g~, ~b~) EXACTLY as they are in the source text."""

# 3. Fail-Safe Python Auto-Corrector
HINDI_TO_URDU = {
    r'\bsamay\b': 'waqt',
    r'\bshareer\b': 'jism',
    r'\bdard nivaarak\b': 'painkillers',
    r'\bswasthya\b': 'sehat',
    r'\bkarya\b': 'kaam',
    r'\bbhavnaon\b': 'ehsaas',
    r'\bkhojne\b': 'dhoondne',
    r'\bvishesh\b': 'khaas',
    r'\bvah\b': 'woh',
    r'\bladaai li\b': 'larai hui',
    r'\bladaai\b': 'larai',
    r'\bbadi\b': 'bari',
    r'\bbada\b': 'bara',
}

def clean_hindi_words(text):
    if not isinstance(text, str):
        return text
    for pattern, replacement in HINDI_TO_URDU.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# 4. Gemini Translation Function (With Fast Key Rotation)
def translate_batch(batch_dict):
    global curr_key_idx
    
    prompt = f"Translate the following JSON values to natural Pakistani Roman Urdu. Return a JSON object with the same keys:\n{json.dumps(batch_dict, ensure_ascii=False)}"
    
    payload = {
        "contents": [{"parts": [{"text": SYSTEM_PROMPT}, {"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2}
    }
    headers = {"Content-Type": "application/json"}
    
    max_attempts = len(API_KEYS) * 2 
    
    for attempt in range(max_attempts):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEYS[curr_key_idx]}"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                res_data = response.json()
                content = res_data['candidates'][0]['content']['parts'][0]['text']
                
                try:
                    parsed = json.loads(content.strip())
                    if isinstance(parsed, dict) and parsed:
                        cleaned_parsed = {k: clean_hindi_words(v) for k, v in parsed.items()}
                        return cleaned_parsed
                except json.JSONDecodeError:
                    print(f"\n⚠️ Format Error. Retrying...", end="", flush=True)
                    
            elif response.status_code == 429:
                print(f"\n⚠️ Key #{curr_key_idx + 1} Limit Hit. Switching to next key...", end="", flush=True)
                curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
                time.sleep(1)
                continue
                
            else:
                print(f"\n⚠️ ERROR {response.status_code}: {response.text[:100]}", flush=True)
                
        except Exception as e:
            print(f"\n⚠️ Connection Error: {str(e)[:50]}...", end="", flush=True)
            
        curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
        time.sleep(2)
        
    print("\n❌ Saari keys thak gayin. Process pause kar rahe hain.")
    exit(1)

# 5. Main Processing Logic
if os.path.exists(input_file):
    print(f"📁 Reading file: {input_file}", flush=True)
    
    saved_data = {}
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r", encoding="utf-8") as f: 
            try:
                saved_data = json.load(f)
                saved_data = {k: clean_hindi_words(v) for k, v in saved_data.items()}
                print(f"🔄 Checkpoint Loaded: {len(saved_data)} lines pehle se completed hain.", flush=True)
            except Exception:
                saved_data = {}

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f: all_lines = f.readlines()
    pending_batch = {}
    total = 0

    for line in all_lines:
        if re.search(r'=\s*~(z|w)~', line):
            total += 1
            k = line.split('=', 1)[0].strip()
            if k not in saved_data:
                pending_batch[k] = line.split('=', 1)[1].strip()
                
            if len(pending_batch) >= batch_size:
                print(f"\n🚀 Translating with Gemini... ({len(saved_data)}/{total})", flush=True)
                res = translate_batch(pending_batch)
                if res:
                    saved_data.update(res)
                    with open(checkpoint_file, "w", encoding="utf-8") as cf: 
                        json.dump(saved_data, cf, ensure_ascii=False, indent=2)
                    print("✅ [Batch Saved Successfully]", flush=True)
                pending_batch = {}
                time.sleep(1.0) # Speed is back! Sirf 1 sec ka delay.

    if pending_batch:
        res = translate_batch(pending_batch)
        if res:
            saved_data.update(res)
            with open(checkpoint_file, "w", encoding="utf-8") as cf: 
                json.dump(saved_data, cf, ensure_ascii=False, indent=2)

    print("\n🔨 Rebuilding american_roman.oxt file...", flush=True)
    count = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for line in all_lines:
            if re.search(r'=\s*~(z|w)~', line):
                k = line.split('=', 1)[0].strip()
                if k in saved_data:
                    clean_text = clean_hindi_words(saved_data[k])
                    out.write(f"{k} = {clean_text}\n")
                    count += 1
                else: out.write(line)
            else: out.write(line)
            
    print(f"\n🎉 BOOM! SUCCESS! {count} lines Perfect Gemini Roman Urdu mein convert ho gayin!", flush=True)
else:
    print(f"❌ Error: '{input_file}' file nahi mili.", flush=True)
