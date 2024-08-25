import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gspread
from oauth2client.service_account import ServiceAccountCredentials


@dataclass
class Actor:
    movie: str
    full_name: str
    rating: float
    movie_count: int = 1
    average_rating: float = 0.0

    def update_rating(self, new_rating):
        self.movie_count += 1
        self.rating += new_rating
        self.average_rating = self.rating / self.movie_count


def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("top-250-imdb-433615-52c40bf27abb.json", scope)

    client = gspread.authorize(creds)

    try:
        sheet = client.open("IMDb Top 250").sheet1
        print("Opened 'IMDb Top 250' spreadsheet")
    except gspread.SpreadsheetNotFound:
        sheet = client.create("IMDb Top 250").sheet1
        print("Created 'IMDb Top 250' spreadsheet")
    except Exception as e:
        logging.error(f"Error opening/creating Google Sheet: {e}")
        raise

    return sheet


def save_to_google_sheets(data):
    sheet = setup_google_sheets()

    headers = ["Movie", "Full Name", "Average Rating"]

    if not sheet.get_all_values():
        sheet.append_row(headers)

    rows = [[actor.movie, actor.full_name, round(actor.average_rating, 2)] for actor in data.values()]

    if rows:
        sheet.append_rows(rows)
        logging.info("Data saved to Google Sheets.")
    else:
        logging.warning("No data to save.")


def get_top_250_movies(driver: webdriver):
    driver.get("https://www.imdb.com/chart/top/?ref_=nv_mv_250")

    WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                "div.ipc-title.ipc-title--base.ipc-title--title."
                "ipc-title-link-no-icon.ipc-title--on-textPrimary."
                "sc-b189961a-9.bnSrml.cli-title"
            )
        )
    )

    movies = driver.find_elements(
        By.CSS_SELECTOR,
        "div.ipc-title.ipc-title--base.ipc-title--title."
        "ipc-title-link-no-icon.ipc-title--on-textPrimary."
        "sc-b189961a-9.bnSrml.cli-title"
    )

    ratings = driver.find_elements(
        By.CSS_SELECTOR,
        "div.sc-e2dbc1a3-0.jeHPdh.sc-b189961a-2.bglYHz.cli-ratings-container"
    )

    movie_data = []

    for movie, rating in zip(movies, ratings):
        title_element = movie.find_element(By.CSS_SELECTOR, "h3.ipc-title__text")
        rating_element = rating.find_element(By.CLASS_NAME, "ipc-rating-star--rating")
        title = title_element.text.strip()
        url = movie.find_element(By.TAG_NAME, "a").get_attribute("href")

        movie_data.append((title, url, float(rating_element.text.strip())))

    return movie_data


def get_cast(movie_name: str, movie_url: str, rating: float, driver: webdriver):
    parsed_url = urlparse(movie_url)

    new_path = parsed_url.path.rstrip("/") + "/fullcredits/"

    full_cast_url = urlunparse(parsed_url._replace(path=new_path))

    logging.info(f"Start scraping cast for movie: {full_cast_url}")

    driver.get(full_cast_url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "cast_list"))
    )

    cast_table = driver.find_element(By.CLASS_NAME, "cast_list")
    cast = []

    for row in cast_table.find_elements(By.TAG_NAME, "tr"):
        if row.find_elements(By.CLASS_NAME, "character"):
            try:
                element = row.find_element(
                    By.CLASS_NAME, "primary_photo"
                ).find_element(By.XPATH, "./following-sibling::td")
                full_name = element.text.strip()
                cast.append(Actor(movie=movie_name, full_name=full_name, rating=rating))
            except Exception as e:
                logging.warning(f"Error processing row: {e}")

        if "Rest of cast" in row.text:
            logging.info("Found 'Rest of cast', STOP.")
            break

    logging.info(f"Stop scraping movie - {full_cast_url}. Result: {len(cast)} actors!")

    return cast


def calculate_average_ratings(cast):
    actor_dict = defaultdict(lambda: Actor(movie="", full_name="", rating=0.0))

    for actor in cast:
        if actor.full_name in actor_dict:
            actor_dict[actor.full_name].update_rating(actor.rating)
        else:
            actor_dict[actor.full_name] = actor

    return actor_dict


def main():
    start_time = time.time()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("imdb_parser.log", mode="w"),
            logging.StreamHandler(),
        ],
    )

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        (
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    )

    driver = webdriver.Chrome(options=chrome_options)

    try:
        movies = get_top_250_movies(driver)
        cast = []

        for movie_title, movie_url, rating in movies:
            cast.extend(get_cast(movie_title, movie_url, rating, driver))

        actor_dict = calculate_average_ratings(cast)

        save_to_google_sheets(actor_dict)

        logging.info("Parsing completed. Data saved to Google Sheets.")
    finally:
        driver.quit()

    end_time = time.time()
    execution_time = end_time - start_time

    logging.info(f"Execution time: {round(execution_time / 60, 1)} min")


if __name__ == "__main__":
    main()