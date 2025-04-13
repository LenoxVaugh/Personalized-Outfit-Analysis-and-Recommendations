import openai
from dotenv import load_dotenv
import json
import os

# Load environment variables
load_dotenv("demo.env")

# Sửa tên biến cho đúng
def init_openai():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return client, True
    except ImportError:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        return openai, False

client, is_new_sdk = init_openai()

prompt = """Bạn là chuyên gia tư vấn thời trang. Hãy trả lời mọi câu hỏi bằng tiếng Việt. 
Đưa ra lời khuyên chi tiết và thực tế về cách phối đồ. Giọng điệu thân thiện và chuyên nghiệp.
Trả lời luôn ở định dạng JSON có cấu trúc như sau:
{
    "message": "<lời khuyên bằng tiếng Việt>",
    "items": ["item1", "item2", ...]
}
Trong đó items là từ khóa các sản phẩm để tìm kiếm trên các trang mua sắm."""

def get_response_with_chat(prompt):
    try:
        if is_new_sdk:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        else:
            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message['content']
    except Exception as e:
        print(f"Error in get_response_with_chat: {str(e)}")
        return "Sorry, there was an error processing your request."
