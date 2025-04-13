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
    """Lưu cookies vào file."""
    with open(filename, "wb") as cookie_file:
        pickle.dump(driver.get_cookies(), cookie_file)

def load_cookies(driver, filename="cookies.pkl"):
    """Nạp cookies từ file (nếu có)."""
    if os.path.exists(filename):
        with open(filename, "rb") as cookie_file:
            cookies = pickle.load(cookie_file)
            for cookie in cookies:
                # Đảm bảo cookie có domain khớp với trang web hiện tại
                driver.add_cookie(cookie)

def search_lazada(query):
    options = EdgeOptions()
    options.use_chromium = True
    # Chạy ở chế độ không headless để có thể xử lý captcha,
    # nhưng khởi động ở chế độ minimized để không hiện cửa sổ lên màn hình chính.
    options.headless = False
    options.add_argument("--start-minimized")  # Khởi động dưới dạng minimize
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    # Loại bỏ tham số "start-maximized" nếu có
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    # Khởi tạo trình duyệt Microsoft Edge với các tùy chọn đã thiết lập
    driver = webdriver.Edge(options=options)
    # Đảm bảo cửa sổ được minimize
    driver.minimize_window()

    try:
        # 1) Mở trang chủ Lazada để thiết lập domain cookies
        driver.get("https://www.lazada.vn/")
        time.sleep(0.5)  # Đảm bảo trang đã tải xong

        # 2) Nạp cookies cũ (nếu có)
        load_cookies(driver)

        # 3) Refresh trang để áp dụng cookies
        driver.refresh()

        # 4) Điều hướng đến trang tìm kiếm với query
        query_url = f"https://www.lazada.vn/catalog/?q={query.replace(' ', '+')}"
        driver.get(query_url)

        # 5) Chờ cho đến khi trang sản phẩm xuất hiện
        #    Nếu xuất hiện captcha, bạn cần xử lý (cửa sổ vẫn đang minimized)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qa-locator='product-item']"))
        )

        # 6) Sau khi đã vào được trang (và có thể đã xác minh captcha nếu cần),
        #    lưu lại cookies mới nhất để lần sau không bị yêu cầu xác minh lại.
        save_cookies(driver)

        # 7) Cuộn trang để kích hoạt lazy-load nếu có
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

        # 8) Trích xuất dữ liệu từ trang
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        products = []

        for item in soup.select("div[data-qa-locator='product-item']"):
            a_tag = item.find("a", href=True)
            if a_tag:
                link = a_tag["href"]
                if not link.startswith("http"):
                    link = "https:" + link

                title = a_tag.get("title")
                if not title:
                    img_tag = a_tag.find("img", alt=True)
                    if img_tag:
                        title = img_tag.get("alt", "")

                if title:
                    products.append({
                        "title": title.strip(),
                        "link": link.strip()
                    })

        return products

    except Exception as e:
        print("❌ Có lỗi xảy ra:", e)
        return []

    finally:
        # Đóng trình duyệt
        driver.quit()