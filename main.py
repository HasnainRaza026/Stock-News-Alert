import time
import logging
import os
import requests
from twilio.rest import Client
from dotenv import find_dotenv, load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

STOCK_API_URL = "https://www.alphavantage.co/query"
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Ensure all environment variables are loaded
STOCK_API_KEY = os.getenv("STOCK_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
FROM_NO = os.getenv("FROM_NO")
TO_NO = os.getenv("TO_NO")


def validate_env_vars():
    env_vars = [STOCK_API_KEY, NEWS_API_KEY,
                ACCOUNT_SID, AUTH_TOKEN, FROM_NO, TO_NO]
    if not all(env_vars):
        logger.error("One or more environment variables are missing.")
        return False
    return True


def send_sms_alert(news, sign, percentage):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    for i in range(min(3, len(news))):
        msg = f"Tesla stocks {sign} by {percentage}%\n{news[i][0]}\n{news[i][1]}."
        try:
            message = client.messages.create(
                body=msg,
                from_=FROM_NO,
                to=TO_NO
            )
            logger.info(f"Message sent with status: {message.status}")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
        time.sleep(5)


def get_related_news(date):
    news_parameter = {
        "q": "tesla",
        "from": date,
        "language": "en",
        "apiKey": NEWS_API_KEY
    }
    news = []
    try:
        news_data = requests.get(url=NEWS_API_URL, params=news_parameter)
        news_data.raise_for_status()
        data = news_data.json()
        for i in data["articles"]:
            if ("Tesla" in i["title"] or "Elon Musk" in i["title"]) and "[Removed]" not in i["title"]:
                news.append((i["title"], i["description"]))
        return news
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while fetching news: {e}")
        return []


def get_stock_data():
    stock_parameter = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "TSLA",
        "apikey": STOCK_API_KEY
    }
    try:
        stock_data = requests.get(url=STOCK_API_URL, params=stock_parameter)
        stock_data.raise_for_status()
        data = stock_data.json()
        time_series = data["Time Series (Daily)"]
        dates = list(time_series.keys())
        latest_close = float(time_series[dates[0]]["4. close"])
        previous_close = float(time_series[dates[1]]["4. close"])
        return latest_close, previous_close, dates[0]
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while fetching stock data: {e}")
        return None, None, None


def calculate_percentage(latest_close, previous_close):
    if latest_close is None or previous_close is None:
        return "same", 0.0
    difference = latest_close - previous_close
    percentage = abs(
        round((difference / ((latest_close + previous_close) / 2)) * 100, 2))
    if difference == 0:
        return "same", percentage
    elif difference < 0:
        return "decrease", percentage
    else:
        return "increase", percentage


def main():
    if not validate_env_vars():
        return

    latest_close, previous_close, date = get_stock_data()
    if latest_close is None or previous_close is None:
        logger.error("Stock data could not be fetched. Exiting program.")
        return

    sign, percentage = calculate_percentage(latest_close, previous_close)

    if percentage >= 5:
        news = get_related_news(date)
        if news:
            send_sms_alert(news, sign, percentage)
        else:
            logger.info("No relevant news found.")


if __name__ == '__main__':
    main()
