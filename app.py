
from datetime import datetime
from flask import Flask, render_template, jsonify
import main_article 
import threading
import time

app = Flask(__name__)
news_data_fetched = {} # in-memory cache
last_refreshed  = datetime.now()

def background_fetch():
    global news_data_fetched, last_refreshed
    while True:
        try:
            print(f"fetching news at {datetime.now()}")
            news_data_fetched = main_article.main_fetch()
            last_refreshed = datetime.now()

        except Exception as e:
            print(f"Error fetching news: {e}")
        time.sleep(300)  # 5 minutes

@app.route('/')
def index():
    global news_data_fetched
    news_data = news_data_fetched
    for value in news_data.values():
        value["source_links"] = list(zip(value["sources"], value["urls"]))
    #print(news_data)
    return render_template('index.html', news=news_data, 
                           refreshed=datetime.strftime(last_refreshed, "%Y-%m-%d %H:%M:%S" ))

if __name__ == '__main__':
    threading.Thread(target=background_fetch, daemon=True).start()
    #print("Sleeping...")
    #time.sleep(400)
    #print("Done...")
    app.run(host='0.0.0.0', port=5000, debug=True)
