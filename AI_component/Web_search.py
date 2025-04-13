# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.edge.options import Options as EdgeOptions
# import time
# import sys
# import os
# # Configure Selenium for Edge
# # options = EdgeOptions()
# # options.add_argument("--headless")
# # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
# # driver = webdriver.Edge(options=options)

# # # Ẩn toàn bộ log cảnh báo hệ thống và selenium
# # os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# # os.environ["PYTHONWARNINGS"] = "ignore"
# # sys.stderr = open(os.devnull, 'w')  # Ẩn log lỗi hệ thống (như DevTools...)
# def search_lazada(query):
# # Cấu hình các tùy chọn cho Microsoft Edge
#     options = EdgeOptions()
#     options.use_chromium = True
#     options.add_argument("--headless")  # Chế độ headless
#     options.add_argument("--disable-gpu")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")

#     # Thiết lập user-agent để mô phỏng trình duyệt thật
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
#     driver = webdriver.Edge(options=options)
#     try:
#         # URL tìm kiếm trên Lazada (Lazada Việt Nam)
#         url = f"https://www.lazada.vn/catalog/?q={query}"
#         driver.get(url)
        
#         # Đợi trang tải nội dung (có thể cần điều chỉnh thời gian tùy theo tốc độ mạng)
#         time.sleep(5)
        
#         # Cuộn trang xuống dưới để tải thêm sản phẩm (nếu cần)
#         driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#         time.sleep(3)
        
#         # Lấy HTML trang hiện tại và parse bằng BeautifulSoup
#         soup = BeautifulSoup(driver.page_source, 'html.parser')
#         products = []
        
#         # Lazada thường hiển thị sản phẩm trong các thẻ <a> có liên kết đến sản phẩm
#         # Lọc ra những link có chứa "/products/"
#         for a_tag in soup.find_all('a', href=True):
#             link = a_tag['href']
#             if '/products/' not in link:
#                 continue
            
#             # Lấy tiêu đề sản phẩm từ thuộc tính 'title' hoặc từ thẻ <img alt="">
#             title = a_tag.get('title')
#             if not title:
#                 img_tag = a_tag.find('img', alt=True)
#                 if img_tag:
#                     title = img_tag.get('alt')
            
#             if not title:
#                 continue
            
#             # Nếu link không có giao thức, thêm "https:"
#             if not link.startswith('http'):
#                 link = "https:" + link
            
#             products.append({"title": title, "link": link})
        
#         return products
#     finally:
#         # Đảm bảo đóng trình duyệt sau khi hoàn thành
#         driver.quit()
# if __name__ == "__main__":
#     query = "áo thun"  # Ví dụ: tìm kiếm "áo thun"
#     products = search_lazada(query)
#     print("Found products:")
#     for product in products:
#         print(f"Title: {product['title']}")
#         print(f"Link: {product['link']}")
#         print("-" * 30)

from bs4 import BeautifulSoup
import time
import os
import pickle
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_cookies(driver, filename="cookies.pkl"):
    with open(filename, "wb") as cookie_file:
        pickle.dump(driver.get_cookies(), cookie_file)

def load_cookies(driver, filename="cookies.pkl"):
    if os.path.exists(filename):
        with open(filename, "rb") as cookie_file:
            cookies = pickle.load(cookie_file)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                print("❗ Cookie error:", e)

def search_lazada(query):
    options = EdgeOptions()
    options.use_chromium = True

    # Chạy hoàn toàn ẩn không cửa sổ
    options.add_argument("--headless=new")  # Đảm bảo dùng chế độ headless mới
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    # Không giữ cửa sổ sau khi chạy
    options.add_experimental_option("detach", False)

    # Tạo WebDriver
    driver = webdriver.Edge(options=options)

    try:
        driver.get("https://www.lazada.vn/")
        time.sleep(1)

        load_cookies(driver)
        driver.refresh()
        time.sleep(1)

        search_url = f"https://www.lazada.vn/catalog/?q={query.replace(' ', '+')}"
        driver.get(search_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qa-locator='product-item']"))
        )

        save_cookies(driver)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        items = soup.select("div[data-qa-locator='product-item']")
        results = []

        for item in items:
            a_tag = item.find("a", href=True)
            if a_tag:
                link = a_tag.get("href")
                if not link.startswith("http"):
                    link = "https:" + link
                title = a_tag.get("title") or a_tag.find("img").get("alt", "")
                if title:
                    results.append({
                        "title": title.strip(),
                        "link": link.strip()
                    })

        return results

    except Exception as e:
        print("❌ Lỗi:", e)
        return []

    finally:
        driver.quit()

# # Test
# if __name__ == "__main__":
#     search_terms = ["áo thun trắng", "áo khoác bomber nam"]
#     for search_term in search_terms:
#         print(f"🔍 Tìm kiếm: {search_term}")
#         results = search_lazada(search_term)
        
#         if results:
#             print("✅ Found products:")
#             for i, product in enumerate(results[:5], 1):
#                 print(f"{i}. {product['title']}")
#                 print(f"   🔗 {product['link']}\n")
#         else:
#             print("❌ Không tìm thấy sản phẩm.")
