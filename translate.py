from google import genai
import time
import os

# GitHub Secrets se keys retrieve karna
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
    print(f"\n🔄 [KEY SWITCH] Limit reached on Key {old_index + 1}. Switching to Key {current_key_index + 1}...", flush=True)
    time.sleep(5)

def translate_batch_gemini(batch_keys, batch_texts, batch_num, total_batches):
    # Strict prompt to force direct conversational Roman Urdu lines match
    prompt = (
        "You are an expert game translator. Translate the English text of the following lines into natural, conversational, "
        "and very easy WhatsApp-style Roman Urdu (Latin script) that a common gamer can read (e.g., 'Main yahan fasa hua hoon').\n\n"
        "STRICT RULES:\n"
        "1. Translate ONLY the spoken text. Do NOT add any hex keys, equal signs (=), or notes.\n"
        "2. Do NOT remove or modify the game formatting symbols (~z~ or ~w~). They must remain exactly at the start of each translated line.\n"
        "3. Output exactly the same number of lines as provided. Maintain the exact line-by-line order.\n"
        "4. Output ONLY the translated text lines. Do not add any introductory text, markdown formatting, or code blocks (like ```).\n\n"
        "Lines to translate:\n" + "\n".join(batch_texts)
    )
    
    for attempt in range(5):
        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            
            # Cleaning markdown remnants if leaked by AI
            response_text = response.text.strip().replace("```text", "").replace("```", "")
            translated_lines = [l.strip() for l in response_text.split('\n') if l.strip()]
            
            if len(translated_lines) == len(batch_texts):
                final_batch = []
                # Reconstruct key-prefix back to the translated dialogue string
                for key_prefix, trans_text in zip(batch_keys, translated_lines):
                    clean_trans = trans_text.strip('"').strip("'")
                    final_batch.append(f"{key_prefix}{clean_trans}")
                return final_batch
            else:
                print(f"\n⚠️ Batch {batch_num}: Lines count mismatch ({len(translated_lines)} vs {len(batch_texts)}). Retrying...", flush=True)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str or "Quota" in error_str or "exhausted" in error_str.lower():
                switch_key()
            else:
                time.sleep(4)
                
    # Fallback to original reconstruction if all attempts exhaust
    fallback_batch = []
    for key_prefix, orig_text in zip(batch_keys, batch_texts):
        fallback_batch.append(f"{key_prefix}{orig_text}")
    return fallback_batch

if os.path.exists(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        
    final_lines = list(all_lines)
    batch_keys = []
    batch_texts = []
    batch_indices = []
    
    for idx, line in enumerate(all_lines):
        if "~z~" in line or "~w~" in line:
            if not line.strip().startswith("//"):
                # Splitting line properly keeping the structural key prefix intact
                symbol = "~z~" if "~z~" in line else "~w~"
                parts = line.split(symbol, 1)
                if len(parts) > 1:
                    batch_keys.append(parts[0] + symbol) # Holds: "0x1F943B91 = ~z~"
                    batch_texts.append(parts[1].strip())  # Holds pure English text line
                    batch_indices.append(idx)

    total_batches = (len(batch_items := batch_texts) + batch_size - 1) // batch_size
    print(f"📋 Total Dialogues Found: {len(batch_items)} lines ({total_batches} batches). Starting on GitHub Cloud...", flush=True)
    
    for i in range(0, len(batch_items), batch_size):
        current_batch_num = (i // batch_size) + 1
        
        current_keys = batch_keys[i:i+batch_size]
        current_texts = batch_texts[i:i+batch_size]
        current_indices = batch_indices[i:i+batch_size]
        
        translated_batch = translate_batch_gemini(current_keys, current_texts, current_batch_num, total_batches)
        
        for b_idx, trans_line in zip(current_indices, translated_batch):
            final_lines[b_idx] = trans_line + "\n"
            
        print(f"➔ Processed Batch {current_batch_num} of {total_batches} successfully.", flush=True)
        time.sleep(4.0)

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.writelines(final_lines)
    print("\n🎉 SUCCESS: File writing complete.", flush=True)
else:
    print(f"❌ Error: '{input_file}' not found in repository root directory.", flush=True)
