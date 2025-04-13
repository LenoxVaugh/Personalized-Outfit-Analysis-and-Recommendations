from openai import OpenAI
from dotenv import load_dotenv
import json
import os

# Load environment variables
load_dotenv("demo.env")

# Sửa tên biến cho đúng
api_key = os.getenv("OPENAI_API_KEY") 
client = OpenAI(api_key=api_key)

prompt = """Bạn là chuyên gia tư vấn thời trang. Hãy trả lời mọi câu hỏi bằng tiếng Việt. 
Đưa ra lời khuyên chi tiết và thực tế về cách phối đồ. Giọng điệu thân thiện và chuyên nghiệp.
Trả lời luôn ở định dạng JSON có cấu trúc như sau:
{
    "message": "<lời khuyên bằng tiếng Việt>",
    "items": ["item1", "item2", ...]
}
Trong đó items là từ khóa các sản phẩm để tìm kiếm trên các trang mua sắm."""

def get_response_with_chat(sentence):
    """Get response using standard GPT model."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Sử dụng model chuẩn thay vì fine-tuned
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": sentence}
            ],
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content.strip()
        
        try:
            response_json = json.loads(response_text)
            message = response_json.get("message", "")
            items = response_json.get("items", [])
            return message, items
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            return "Xin lỗi, có lỗi xảy ra khi xử lý phản hồi.", []
            
    except Exception as e:
        print(f"Error in get_response_with_chat: {str(e)}")
        return None, []