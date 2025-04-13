# # from AI_component.Search_item_prompt import extract_items
# # from AI_component.get_response_with_chat import get_response_with_chat
# # from AI_component.Blip_model import load_blip_model
# # from AI_component.Transaltion import translate_with_chat_gpt
# # from AI_component.Web_search import search_lazada
# # from PIL import Image

# # def get_image_caption(image_path):
# #     """ Load an image and generate a caption using the BLIP model and extract items. """
# #     image = Image.open(image_path)
# #     caption = load_blip_model(image)
# #     extracted_items = extract_items(caption)
    
# #     # for item in extracted_items:
# #     #     print(f"Searching for: {item}")
# #     #     results = search_lazada(item)
# #     #     for result in results[:4]:  # Limit to top 4 results
# #     #         print(f"Title: {result['title']}, Link: {result['link']}")
    
# #     return caption, extracted_items

# # def get_chat_response(sentence):
# #     """ Get a response from the chat model based on the extracted items. """
# #     message, items = get_response_with_chat(sentence)
# #     for item in items:
# #         print(f"Searching for: {item}")
# #         results = search_lazada(item)
# #         for result in results[:3]:  # Limit to top 4 results
# #             print(f"Title: {result['title']}, Link: {result['link']}")   
# #     return message, items

# # response, extracted_items = get_image_caption(r"E:\KY_9_DO_AN\data_ver2\Final outfit APP\0084e766-1f08-4b3d-a629-f78fe0cce72e.jpg")
# # print("Caption:", response)
# # response = translate_with_chat_gpt(response, "Vietnamese")
# # print("Translated Caption:", response)
# # print("Extracted Items:", extracted_items)

# # response, extracted_items = get_chat_response("I about to go to a wedding i already have a T-shirt can you suggest me a jean")
# # print("Chat Response:", response)
# # response = translate_with_chat_gpt(response, "Vietnamese")
# # print("Translated Chat Response:", response)
# # print("Extracted Items:", extracted_items)

# from AI_component.Search_item_prompt import extract_items
# from AI_component.get_response_with_chat import get_response_with_chat
# from AI_component.Blip_model import load_blip_model
# from AI_component.Transaltion import translate_with_chat_gpt
# from AI_component.Web_search import search_lazada
# import json
# from PIL import Image

# def search_for_items(items):
#     """Tìm kiếm trên Lazada cho mỗi item và in ra 3 kết quả."""
#     for item in items:
#         print(f"\n🔍 Searching for: {item}")
#         results = search_lazada(item)
#         if not results:
#             print("❌ No results found.")
#         else:
#             for result in results[:3]:
#                 print(f"✅ Title: {result['title']}\n🔗 Link: {result['link']}")
#         print("-" * 40)

# def get_image_caption(image_path):
#     """Load ảnh và tạo caption bằng mô hình BLIP, sau đó trích xuất các item và tìm kiếm."""
#     image = Image.open(image_path)
#     caption = load_blip_model(image)
#     extracted_items = extract_items(caption)
#     extracted_items = json.loads(extracted_items)
#     extracted_items = extracted_items["Item_list"]
#     translated_item = []
#     for item in extracted_items:
#         new_item = translate_with_chat_gpt(item, "Vietnamese")
#         translated_item.append(new_item)
#     print("📝 Caption:", caption)
#     print("🧠 Extracted Items:", extracted_items)  # In ra trực tiếp list

#     # Tìm kiếm sau khi in
#     search_for_items(translated_item)

#     return caption, translated_item


# def get_chat_response(sentence):
#     """Lấy phản hồi từ mô hình chat dựa trên truy vấn của người dùng và tìm kiếm item."""
#     message, items = get_response_with_chat(sentence)

#     print("💬 Chat Response:", message)
#     print("🧠 Extracted Items:", items)  # In ra trực tiếp list

#     search_for_items(items)

#     return message, items

# # ==== Ví dụ sử dụng ====
# response, extracted_items = get_image_caption(r"E:\KY_9_DO_AN\data_ver2\Final outfit APP\0084e766-1f08-4b3d-a629-f78fe0cce72e.jpg")
# translated_caption = translate_with_chat_gpt(response, "Vietnamese")
# print("🌐 Translated Caption:", translated_caption)

# response, chat_items = get_chat_response("I about to go to a wedding i already have a T-shirt can you suggest me a jean")
# translated_chat = translate_with_chat_gpt(response, "Vietnamese")
# print("🌐 Translated Chat Response:", translated_chat)



from AI_component.Search_item_prompt import extract_items
from AI_component.get_response_with_chat import get_response_with_chat
from AI_component.Blip_model import load_blip_model
from AI_component.Transaltion import translate_with_chat_gpt
from AI_component.Web_search import search_lazada
import json
from PIL import Image

def parse_translation(translation):
    """
    Nếu translation là dictionary và có key 'target', trả về giá trị đó.
    Nếu không, ép kiểu sang chuỗi.
    """
    if isinstance(translation, dict):
        return translation.get("target", str(translation))
    else:
        try:
            # Nếu translation là chuỗi JSON, thử load và lấy key 'target'
            parsed = json.loads(translation)
            return parsed.get("target", translation)
        except:
            return str(translation)

def search_for_items(items):
    """
    Tìm kiếm trên Lazada cho mỗi item và trả về chuỗi tổng hợp kết quả
    gồm: tên item, top 3 kết quả với Title và Link.
    """
    output_lines = []
    for item in items:
        output_lines.append(f"\n🔍 Đề xuất: {item}")
        results = search_lazada(item)
        if not results:
            output_lines.append("❌ No results found.")
        else:
            for result in results[:3]:
                output_lines.append(f"✅ Title: {result['title']}")
                output_lines.append(f"🔗 Link: {result['link']}")
        output_lines.append("-" * 40)
    return "\n".join(output_lines)

def get_image_caption(image_path: str, question: str):
    """
    Load ảnh và tạo caption bằng mô hình BLIP, sau đó trích xuất các item và tìm kiếm.
    """
    image = Image.open(image_path)
    caption = load_blip_model(image)
    response_dict = extract_items(caption=caption, query=question)
    response_dict = json.loads(response_dict)
    extracted_items = response_dict["Item_list"]
    response = response_dict["answer"]
    translated_items = []
    for item in extracted_items:
        translated_items.append(parse_translation(new_item))
    print("📝 Caption:", caption)
    return response, translated_items

def get_chat_response(sentence):
    """
    Lấy phản hồi từ mô hình chat dựa trên truy vấn của người dùng và tìm kiếm item.
    """
    message, items = get_response_with_chat(sentence)
    translated_items = []
    for item in items:
        translated_items.append(parse_translation(new_item))
    
    # Lấy kết quả tìm kiếm cho các item
    search_output = search_for_items(translated_items)
    return message, search_output

# ==== Ví dụ sử dụng ====
image_path = r"E:\KY_9_DO_AN\data_ver2\Final outfit APP\3b95ed76-00b1-416e-bb97-1098f53a114a.jpg"
question = "what would go great with this outfit ?"
response, extracted_items = get_image_caption(image_path, question=question)

# Lấy kết quả tìm kiếm cho caption (image) từ các item được trích xuất
image_search_output = search_for_items(extracted_items)
translated_caption = translate_with_chat_gpt(response, "Vietnamese")
# print("🌐 Translated Caption:", parse_translation(translated_caption))

# 2. Lấy phản hồi từ chat và tìm kiếm item
chat_response, chat_search_output = get_chat_response("I about to go to a wedding i already have a T-shirt can you suggest me a jean")
translated_chat = translate_with_chat_gpt(chat_response, "Vietnamese")
# print("🌐 Translated Chat Response:", parse_translation(translated_chat))

# Tổng hợp output cuối cùng (chỉ tổng hợp lại, không chạy lại các tìm kiếm)
final_output = (
    f"🌐 Chat: {parse_translation(translated_caption)}\n"
    f"{image_search_output}\n\n"
    f"🌐 Chat: {parse_translation(translated_chat)}\n"
    f"{chat_search_output}"
)

print("\n========== FINAL OUTPUT ==========")
print(final_output)

