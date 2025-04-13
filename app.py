from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import uuid
import datetime
import random
from PIL import Image
from dotenv import load_dotenv
import json
from difflib import SequenceMatcher
from supabase import create_client, Client
from datetime import datetime, timedelta
from database import get_db_connection

# Import các module AI từ AI_component
from AI_component.Search_item_prompt import extract_items
from AI_component.get_response_with_chat import get_response_with_chat
from AI_component.Blip_model import load_blip_model
from AI_component.Transaltion import translate_with_chat_gpt
from AI_component.Web_search import search_lazada

# Load environment variables with specific path
env_path = os.path.join(os.path.dirname(__file__), 'demo.env')
load_dotenv(env_path)

# Debug logging for environment variables
print("Debug Environment Variables:")
print(f"Current directory: {os.path.dirname(__file__)}")
print(f"ENV file path: {env_path}")
print(f"ENV file exists: {os.path.exists(env_path)}")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY length: {len(os.getenv('SUPABASE_KEY') or '')}")

# Supabase setup
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
        
    supabase = create_client(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )
    
    # Test connection with basic query
    print("Testing Supabase connection...")
    response = supabase.table('search_cache').select("*").limit(1).execute()
    print(f"Connection successful! Response data: {response.data}")
    
except Exception as e:
    print(f"Supabase Error: {str(e)}")
    print(f"Error type: {type(e)}")
    raise Exception(f"Failed to connect to Supabase: {str(e)}")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend API calls

# File storage configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Biến tạm thời để lưu các món đồ từ ảnh upload (không dùng DB vì không có đăng nhập)
temp_wardrobe = []

# Check valid file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# AI Utilities
def parse_translation(translation):
    """Parse translation response from OpenAI."""
    if isinstance(translation, dict):
        return translation.get("target", str(translation))
    else:
        try:
            parsed = json.loads(translation)
            return parsed.get("target", translation)
        except:
            return str(translation)

def extract_search_keywords(text):
    """Extract potential search keywords from text with improved accuracy"""
    # Mở rộng danh sách từ khóa chỉ mục tìm kiếm
    shopping_indicators = [
        'mua', 'tìm', 'shopping', 'buy', 'search', 'looking for', 
        'kiếm', 'đặt', 'order', 'get', 'có', 'bán'
    ]
    
    # Từ khóa cần loại bỏ để làm sạch kết quả
    remove_words = [
        'cho', 'tôi', 'mình', 'bạn', 'một', 'cái', 'chiếc', 
        'muốn', 'cần', 'giúp', 'xin', 'vui lòng'
    ]
    
    text = text.lower().strip()
    
    # Tìm kiếm từ khóa shopping trong câu
    for indicator in shopping_indicators:
        if (indicator in text):
            # Lấy phần text sau từ khóa
            index = text.find(indicator)
            search_text = text[index:].split('.')[0]
            
            # Loại bỏ các từ khóa shopping
            for ind in shopping_indicators:
                search_text = search_text.replace(ind, '')
                
            # Loại bỏ các từ không cần thiết
            for word in remove_words:
                search_text = search_text.replace(word, '')
            
            cleaned_text = search_text.strip()
            if cleaned_text:  # Chỉ trả về nếu còn nội dung sau khi làm sạch
                print(f"Extracted search keyword: {cleaned_text}")
                return cleaned_text
    return None

# Add debug logging for environment variables
print("Environment variables:")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')}")

CACHE_TABLE = 'search_cache'

class CacheManager:
    def __init__(self):
        self.table_name = 'search_cache'
    
    def get_cached_results(self, query):
        conn = get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT results FROM search_cache 
                    WHERE query = %s AND created_at > %s""",
                    (query.lower(), datetime.utcnow() - timedelta(hours=24))
                )
                result = cur.fetchone()
                if result and result[0]:
                    # Ensure we return a parsed JSON object
                    if isinstance(result[0], str):
                        return json.loads(result[0])
                    return result[0]
                return None
        finally:
            conn.close()

    def get_similar_results(self, query, similarity_threshold=0.8):
        conn = get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT query, results FROM search_cache 
                    WHERE created_at > %s""",
                    (datetime.utcnow() - timedelta(hours=24),)
                )
                results = cur.fetchall()
                
                if not results:
                    return None

                best_match = None
                highest_similarity = 0
                
                for db_query, db_results in results:
                    similarity = SequenceMatcher(None, query.lower(), db_query.lower()).ratio()
                    if similarity > similarity_threshold and similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = json.loads(db_results)
                
                return best_match
        finally:
            conn.close()

    def cache_results(self, query, results):
        """Cache search results in database"""
        conn = get_db_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                # Ensure results is a JSON string
                if isinstance(results, (list, dict)):
                    results = json.dumps(results)
                elif not isinstance(results, str):
                    results = json.dumps(str(results))
                
                cur.execute(
                    "DELETE FROM search_cache WHERE query = %s",
                    (query.lower(),)
                )
                cur.execute(
                    """INSERT INTO search_cache (query, results) 
                    VALUES (%s, %s)""",
                    (query.lower(), results)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error caching results: {str(e)}")
            return False
        finally:
            conn.close()

# Initialize cache manager
cache_manager = CacheManager()

# Replace existing cache functions
def get_cached_results(query):
    """Get exact match cached results from database"""
    return cache_manager.get_cached_results(query)

def get_similar_cached_results(query, similarity_threshold=0.8):
    """Find cached results for similar search queries"""
    return cache_manager.get_similar_results(query, similarity_threshold)

def cache_search_results(query, results):
    """Cache search results in database"""
    return cache_manager.cache_results(query, results)

def search_for_items(items, category=None):
    """Tìm kiếm thông tin sản phẩm với ưu tiên cache và lọc theo category"""
    search_results = []
    processed_keywords = set()
    
    # Define category keywords with both English and Vietnamese terms
    category_keywords = {
        'quần': ['quần', 'pants', 'jean', 'chinos', 'trousers', 'quần âu', 'quần tây', 'quần jeans'],
        'áo': ['áo', 'shirt', 'jacket', 't-shirt', 'hoodie', 'sweater', 'áo sơ mi', 'áo khoác'],
        'giày': ['giày', 'shoes', 'sneakers', 'boots', 'giày da', 'giày thể thao'],
        'túi': ['túi', 'bag', 'backpack', 'purse', 'túi xách', 'ba lô'],
        'phụ kiện': ['đồng hồ', 'watch', 'belt', 'necklace', 'bracelet', 'thắt lưng', 'vòng cổ']
    }
    
    # Pre-filter items based on category if specified
    if category and items:
        category_terms = category_keywords.get(category, [])
        filtered_items = [
            item for item in items 
            if any(term in item.lower() for term in category_terms)
        ]
        items = filtered_items if filtered_items else items

    for item in items:
        item = str(item) if not isinstance(item, str) else item
        
        if item.lower() in processed_keywords:
            continue
            
        item_results = {"query": item, "results": []}
        try:
            print(f"Processing search for: {item}")
            
            # Check cache first
            cached_results = get_cached_results(item)
            if (cached_results):
                # Format cached results
                try:
                    if isinstance(cached_results, str):
                        try:
                            formatted_results = json.loads(cached_results)
                            if not isinstance(formatted_results, list):
                                formatted_results = [{"title": str(formatted_results)}]
                        except json.JSONDecodeError:
                            formatted_results = [{"title": cached_results}]
                    elif isinstance(cached_results, list):
                        formatted_results = [
                            result if isinstance(result, dict) else {"title": str(result)}
                            for result in cached_results[:2]
                        ]
                    else:
                        formatted_results = [{"title": str(cached_results)}]
                except Exception as e:
                    print(f"Error formatting cached results: {str(e)}")
                    formatted_results = [{"title": str(cached_results)}]
                    
                item_results["results"] = formatted_results
                
            else:
                # Search online
                online_results = search_lazada(item)
                if online_results:
                    formatted_results = []
                    for result in online_results[:2]:
                        if isinstance(result, dict):
                            formatted_results.append(result)
                        else:
                            formatted_results.append({"title": str(result)})
                    
                    # Filter results by category if specified
                    if category:
                        category_terms = category_keywords.get(category, [])
                        formatted_results = [
                            result for result in formatted_results
                            if any(term in result["title"].lower() for term in category_terms)
                        ]
                    
                    item_results["results"] = formatted_results
                    
                    # Cache as JSON string
                    try:
                        json_string = json.dumps(formatted_results, ensure_ascii=False)
                        cache_search_results(item, json_string)
                    except Exception as e:
                        print(f"Error caching results: {str(e)}")
            
            # Only add results if they match the category filter
            if item_results["results"]:
                if category:
                    category_terms = category_keywords.get(category, [])
                    filtered_results = [
                        result for result in item_results["results"]
                        if any(term in result["title"].lower() for term in category_terms)
                    ]
                    if filtered_results:
                        item_results["results"] = filtered_results
                        processed_keywords.add(item.lower())
                        search_results.append(item_results)
                else:
                    processed_keywords.add(item.lower())
                    search_results.append(item_results)
                
        except Exception as e:
            print(f"Error searching for {item}: {str(e)}")
            continue
    
    return search_results[:3]

def get_image_caption(image_path: str, with_recommendation: bool = False):
    """Phân tích ảnh với BLIP và trả về thông tin quần áo."""
    try:
        image = Image.open(image_path)
        caption = load_blip_model(image)
        
        # Câu hỏi khác nhau dựa trên yêu cầu
        question = "What clothing items can you identify in this image?" if not with_recommendation else \
                    "What items can you identify in this image and what would go well with them?"
        
        response_dict = extract_items(caption=caption, query=question)
        response_dict = json.loads(response_dict)
        extracted_items = response_dict["Item_list"]
        response = response_dict["answer"]
        
        translated_items = [
            parse_translation(translate_with_chat_gpt(item, "Vietnamese")) 
            for item in extracted_items
        ]
        translated_response = parse_translation(
            translate_with_chat_gpt(response, "Vietnamese")
        )
        
        search_results = search_for_items(translated_items)
        return translated_response, translated_items, search_results, caption
    except Exception as e:
        print(f"Error in get_image_caption: {str(e)}")
        return f"Lỗi khi xử lý ảnh: {str(e)}", [], [], ""

def get_chat_response(sentence):
    """Tối ưu phản hồi chat để phù hợp với UI và đảm bảo phản hồi bằng tiếng Việt."""
    try:
        # Danh sách các từ chào hỏi đơn giản
        simple_greetings = ["hello", "hi", "chào", "xin chào", "hey", "alo"]
        
        # Danh sách từ khóa phong cách
        style_keywords = ["phong cách", "style", "thời trang", "fashion", "đi làm", "công sở", "office"]
        
        sentence_lower = sentence.lower().strip()
        
        # Chỉ trả lời chào khi người dùng chỉ gửi lời chào đơn giản
        if any(sentence_lower == greet for greet in simple_greetings):
            greeting_responses = [
                "Chào bạn! Mình là trợ lý thời trang thông minh. Bạn có thể gửi ảnh hoặc hỏi bất kỳ điều gì về thời trang nhé!",
                "Xin chào! Rất vui được gặp bạn. Bạn muốn tìm hiểu về phong cách nào?",
                "Hey! Mình ở đây để giúp bạn trông thật phong cách. Bạn cần tư vấn gì nào?"
            ]
            return random.choice(greeting_responses), [], []
            
        # Determine category based on context with more specific keywords
        category = None
        if any(word in sentence.lower() for word in ['quần', 'pants', 'jean', 'chinos', 'quần âu', 'quần tây']):
            category = 'quần'
            # Add specific search terms for pants
            search_terms = ['quần âu nam', 'quần tây nam', 'quần chinos nam']
        elif any(word in sentence.lower() for word in ['áo', 'shirt', 'jacket']):
            category = 'áo'
        elif any(word in sentence.lower() for word in ['giày', 'shoes']):
            category = 'giày'
            
        # Get response and items
        message, items = get_response_with_chat(sentence)
        if message is None:
            return "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại!", [], []
            
        # Translate message with context hints for style advice
        if any(char.isascii() for char in message):
            try:
                # Add context for style-related translations
                if any(keyword in sentence_lower for keyword in style_keywords):
                    translation_prompt = f"Translate this fashion style advice to natural Vietnamese: '{message}'"
                else:
                    translation_prompt = f"Translate to Vietnamese: {message}"
                    
                translated_message = translate_with_chat_gpt(translation_prompt, "Vietnamese")
                translated_message = parse_translation(translated_message)
                
                # Clean up common translation artifacts
                translated_message = translated_message.replace("bạn nên", "nên")
                translated_message = translated_message.replace("you should", "nên")
                translated_message = translated_message.replace("such as", "như")
            except Exception as e:
                print(f"Translation error: {str(e)}")
                translated_message = message
        else:
            translated_message = message
        
        # Get search keywords
        search_keyword = extract_search_keywords(sentence)
        if search_keyword:
            items.append(search_keyword)
        
        # Add specific search terms if category is pants
        if category == 'quần' and search_terms:
            items.extend(search_terms)
        
        # Translate items
        translated_items = []
        if items:
            translated_items = [
                str(parse_translation(translate_with_chat_gpt(str(item), "Vietnamese")))
                for item in items
            ]
            
            # Ensure we have pants-specific search terms
            if category == 'quần':
                translated_items.extend(['quần âu nam', 'quần tây nam', 'quần chinos nam'])
        
        # Search with category filter and force category if looking for pants
        search_results = search_for_items(translated_items, category=category) if translated_items else []
        
        # Ensure we have pants results
        if category == 'quần' and (not search_results or not any('quần' in str(result).lower() for result in search_results)):
            fallback_search = search_for_items(['quần âu nam', 'quần tây nam', 'quần chinos nam'], category='quần')
            if fallback_search:
                search_results = fallback_search
        
        return translated_message, translated_items, search_results
        
    except Exception as e:
        print(f"Error in get_chat_response: {str(e)}")
        return "Xin lỗi, có lỗi xảy ra. Bạn vui lòng thử lại nhé!", [], []

# Clothing Analyzer Class
class ClothingAnalyzer:
    def __init__(self):
        self.clothing_categories = ["shirt", "t-shirt", "jacket", "jeans", "dress", "shoes"]
        self.style_categories = ["casual", "formal", "business", "sporty"]
        self.color_categories = ["black", "white", "red", "blue", "green"]

    def analyze_image(self, image_path: str, question: str):
        """Phân tích ảnh và trả về thông tin trang phục cùng đề xuất."""
        response, translated_items, search_results, caption = get_image_caption(image_path, question)
        # Lưu các món đồ vào temp_wardrobe
        wardrobe_item = {
            "id": str(uuid.uuid4()),
            "image_path": image_path,
            "description": response,
            "clothing_type": translated_items or ["clothing item"],
            "created_at": datetime.datetime.now().isoformat()
        }
        temp_wardrobe.append(wardrobe_item)
        return {
            "success": True,
            "caption": caption,
            "translated_response": response,
            "translated_items": translated_items,
            "search_results": search_results
        }

    def recommend_outfits(self, wardrobe_items, occasion=None, weather=None, style_preference=None):
        """Đề xuất outfit từ danh sách món đồ tạm thời."""
        if not wardrobe_items:
            return []
        
        tops = [item for item in wardrobe_items if any(cat in item.get('clothing_type', []) for cat in ["shirt", "t-shirt"])]
        bottoms = [item for item in wardrobe_items if any(cat in item.get('clothing_type', []) for cat in ["jeans"])]
        outfits = []
        
        for top in tops[:3]:
            for bottom in bottoms[:3]:
                outfit = {
                    "id": str(uuid.uuid4()),
                    "name": f"Outfit với {top.get('description', 'top')} và {bottom.get('description', 'bottom')}",
                    "items": [top, bottom],
                    "match_score": 70,  # Giả lập score
                    "created_at": datetime.datetime.now().isoformat()
                }
                outfits.append(outfit)
        
        return outfits[:5]

# Initialize analyzer
clothing_analyzer = ClothingAnalyzer()

# API Routes
@app.route('/')
def home():
    try:
        return send_file('index.html')
    except FileNotFoundError:
        return jsonify({"message": "StyleAI API is running", "status": "active"}), 200

@app.route('/api/message', methods=['POST'])
def handle_message():
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Vui lòng gửi tin nhắn!'}), 400
    
    response, translated_items, search_results = get_chat_response(message)
    return jsonify({
        "success": True,
        "response": response,
        "items": translated_items,
        "search_results": search_results if search_results else []
    })

def get_simple_image_caption(image_path: str):
    """Chỉ trả về caption của ảnh mà không có recommend."""
    try:
        image = Image.open(image_path)
        caption = load_blip_model(image)
        translated_caption = parse_translation(translate_with_chat_gpt(caption, "Vietnamese"))
        return translated_caption
    except Exception as e:
        print(f"Error in get_simple_image_caption: {str(e)}")
        return "Lỗi khi xử lý ảnh"

@app.route('/api/upload', methods=['POST'])
def handle_upload():
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'response': 'Vui lòng chọn ảnh để upload!',
                'items': [],
                'search_results': []
            }), 400
        
        file = request.files['image']
        message = request.form.get('message', '').strip()
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'response': 'File không hợp lệ!',
                'items': [],
                'search_results': []
            }), 400

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        if not message:
            # Xử lý chỉ có ảnh
            caption = get_simple_image_caption(file_path)
            suggestion_questions = [
                "Tôi có thể giúp bạn với phong cách này không?",
                "Bạn muốn tìm items tương tự như trong ảnh chứ?",
                "Bạn cần tư vấn phối đồ với items trong ảnh không?",
                "Tôi có thể gợi ý một số items phù hợp với phong cách này."
            ]
            response = f"{random.choice(suggestion_questions)}\n\nTrong ảnh tôi nhận thấy: {caption}"
            
            return jsonify({
                "success": True,
                "response": response,
                "items": [],
                "search_results": [],
                "imageUrl": f"/uploads/{filename}"
            })
        else:
            # Xử lý có cả ảnh và text
            img_response, items, search_results, _ = get_image_caption(file_path, with_recommendation=True)
            msg_response, msg_items, msg_search_results = get_chat_response(message)
            
            # Ensure both responses are in Vietnamese
            if any(char.isascii() for char in img_response):
                img_response = translate_with_chat_gpt(img_response, "Vietnamese")
                img_response = parse_translation(img_response)
            
            if any(char.isascii() for char in msg_response):
                msg_response = translate_with_chat_gpt(msg_response, "Vietnamese")
                msg_response = parse_translation(msg_response)
            
            # Split and translate the first part if it exists
            pattern = "Here are some suggestions for you:"
            if pattern in img_response:
                parts = img_response.split(pattern)
                if len(parts) > 1:
                    first_part = translate_with_chat_gpt(parts[0].strip(), "Vietnamese")
                    first_part = parse_translation(first_part)
                    img_response = f"{first_part}\n\nGợi ý cho bạn: {parts[1].strip()}"
            
            # Combine responses
            response = f"{img_response}\n\n{msg_response}"
            
            # Combine search results
            if msg_search_results:
                search_results.extend(msg_search_results)

            return jsonify({
                "success": True,
                "response": response,
                "items": items,
                "search_results": search_results,
                "imageUrl": f"/uploads/{filename}"
            })
            
    except Exception as e:
        print(f"Error in handle_upload: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'Có lỗi xảy ra khi xử lý ảnh!',
            'items': [],
            'search_results': []
        }), 500

@app.route('/api/recommend', methods=['POST'])
def recommend_outfits():
    data = request.json
    occasion = data.get('occasion')
    weather = data.get('weather')
    style_preference = data.get('style_preference', [])
    
    if not temp_wardrobe:
        return jsonify({"success": False, "message": "Vui lòng upload ảnh trước để tôi gợi ý outfit!"}), 400
    
    outfits = clothing_analyzer.recommend_outfits(temp_wardrobe, occasion, weather, style_preference)
    
    if not outfits:
        return jsonify({"success": False, "message": "Không thể tạo gợi ý outfit từ ảnh đã upload!"}), 400
    
    return jsonify({"success": True, "outfits": outfits})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
    
@app.route('/api/message', methods=['POST'])
def handle_message():
    """Xử lý tin nhắn với phản hồi tối ưu cho UI."""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'response': 'Vui lòng nhập tin nhắn!',
                'items': [],
                'search_results': []
            }), 400
        
        response, translated_items, search_results = get_chat_response(message)
        
        return jsonify({
            "success": True,
            "response": response,
            "items": translated_items,
            "search_results": search_results if search_results else []
        })
        
    except Exception as e:
        print(f"Error in handle_message: {str(e)}")
        return jsonify({
            'success': False,
            'response': 'Có lỗi xảy ra. Vui lòng thử lại!',
            'items': [],
            'search_results': []
        }), 500