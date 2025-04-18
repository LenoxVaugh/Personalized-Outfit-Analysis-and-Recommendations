from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv("demo.env")

# Get API key and create client (sửa tên biến cho đúng)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

Prompt = """
Translates a sentence into the specified target language.
return only the string of the intended translation.
no need for further information.
input string: {sentence}
target language: {target_language}
    """

def translate_with_chat_gpt(sentence, target_language):
    try:
        prompt = Prompt.format(sentence=sentence, target_language=target_language)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use default GPT model since we don't need fine-tuned
            messages=[
                {"role": "system", "content": "You are a helpful translation assistant specialized in fashion and clothing descriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        translated_sentence = response.choices[0].message.content.strip()
        return translated_sentence
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return sentence  # Fallback to original sentence if translation fails