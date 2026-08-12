from google import genai
import time
import os

# GitHub ke safe secrets se keys ki list automatic uthana
keys_env = os.environ.get("GEMINI_API_KEYS", "")
API_KEYS = [k.strip() for k in keys_env.split(",") if k.strip()]

input_file = "american.oxt"
output_file = "american_roman.oxt"
batch_size = 20
current_key_index = 0

def get_gemini_client():
    global current_key_index
    return genai.Client(api_key=API_KEYS[current_key_index])

def switch_key():
    global current_key_index
    old_index = current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    print(f"\n🔄 [KEY SWITCH] Key {old_index + 1} shifted to Key {current_key_index + 1}...")
    time.sleep(5)

def translate_batch_gemini(batch_items, batch_num, total_batches):
    prompt = (
        "You are an expert game translator. Translate the following lines into natural, conversational, "
        "and very easy WhatsApp-style Roman Urdu (Latin script) that a common Pakistani/Indian gamer can easily read (e.g., 'Main yahan fasa hua hoon'). "
        "Strictly follow these rules:\n"
        "1. Maintain the exact same line order and keep the hex keys (e.g., 0x1A2B3C4D) and tabs on the left completely UNTOUCHED.\n"
        "2. Keep the formatting tags (~z~ or ~w~) exactly where they are at the start of the text.\n"
        "3. Only output the translated lines, nothing else. Do not add any introductory or extra text.\n\n"
        "Lines to translate:\n" + "\n".join(batch_items)
    )
    
    for attempt in range(5):
        try:
            client = get_gemini_client()
            # 100% Clean Production Model Name Framework
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            translated_lines = response.text.strip().split('\n')
            if len(translated_lines) == len(batch_items):
                return [line.strip('"').strip("'") for line in translated_lines]
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str or "Quota" in error_str or "exhausted" in error_str.lower():
                switch_key()
            else:
                time.sleep(4)
    return batch_items

if os.path.exists(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        
    final_lines = list(all_lines)
    batch_items = []
    batch_indices = []
    
    for idx, line in enumerate(all_lines):
        clean_line = line.strip()
        if "~z~" in clean_line or "~w~" in clean_line:
            if not clean_line.startswith("//"):
                batch_items.append(clean_line)
                batch_indices.append(idx)

    total_batches = (len(batch_items) + batch_size - 1) // batch_size
    print(f"📋 Total Dialogues: {len(batch_items)} lines ({total_batches} batches). Starting on GitHub Cloud...")
    
    for i in range(0, len(batch_items), batch_size):
        current_batch_num = (i // batch_size) + 1
        current_batch = batch_items[i:i+batch_size]
        current_indices = batch_indices[i:i+batch_size]
        
        translated_batch = translate_batch_gemini(current_batch, current_batch_num, total_batches)
        
        for b_idx, trans_line in zip(current_indices, translated_batch):
            final_lines[b_idx] = trans_line + "\n"
            
        print(f"➔ Processed Batch {current_batch_num} of {total_batches} successfully.")
        time.sleep(3.5)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.writelines(final_lines)
    print("\n🎉 SUCCESS: File writing complete.")
