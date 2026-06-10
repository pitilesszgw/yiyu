from flask import Flask, render_template, g, request, jsonify, Response, send_from_directory
import os
import sqlite3
import re
import requests

app = Flask(__name__)
# Disable template caching during development
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Add markdown rendering filter
import markdown
from threading import Thread
import schedule
import time
import sys
import os
sys.path.append(os.path.dirname(__file__))
from agent import generate_daily_articles
from douyin_parser import DouyinParseError, parse_douyin_video

app.jinja_env.filters['markdown'] = lambda text: markdown.markdown(text, extensions=['extra', 'nl2br'])

# Database helper
DB_PATH = os.path.join(os.path.dirname(__file__), 'yiyu.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 0 seconds.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response



@app.route('/tool_copywriting')
def tools_copywriting():
    return render_template('tools/copywriting.html')

@app.route('/tool_douyin_video')
def tools_douyin_video():
    return render_template('tools/douyin_video.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/x-icon')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/product-intro')
def product_intro():
    return render_template('product_intro.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('login.html', is_register=True)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/articles')
def articles():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM articles ORDER BY id DESC')
    db_articles = cur.fetchall()
    
    # Convert sqlite3.Row objects to dicts
    articles_list = [dict(row) for row in db_articles]
    
    return render_template('articles.html', articles=articles_list)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
    article = cur.fetchone()
    
    if article is None:
        return "Article not found", 404
        
    return render_template('article_detail.html', article=dict(article))

@app.route('/api/articles.json')
def api_articles():
    """提供给外部拉取 Agent 每日生成文章数据的只读接口"""
    from flask import jsonify
    db = get_db()
    cur = db.cursor()
    # 默认返回较完整的历史列表，避免静态导出后只剩最新几篇。
    limit = request.args.get('limit', default=50, type=int) or 50
    limit = max(1, min(limit, 200))
    cur.execute(
        'SELECT id, category_id, title, title_en, summary, summary_en, content, content_en, date, views, seo_keywords FROM articles ORDER BY id DESC LIMIT ?',
        (limit,)
    )
    db_articles = cur.fetchall()
    
    articles_list = [dict(row) for row in db_articles]
    
    return jsonify({
        "status": "success",
        "count": len(articles_list),
        "data": articles_list
    })

@app.route('/api/tools/douyin-video/parse', methods=['POST'])
def api_douyin_video_parse():
    payload = request.get_json(silent=True) or {}
    video_url = payload.get('url', '')

    try:
        data = parse_douyin_video(video_url)
    except DouyinParseError as exc:
        return jsonify({
            "success": False,
            "message": str(exc)
        }), 400
    except Exception as exc:
        return jsonify({
            "success": False,
            "message": f"解析失败：{exc}"
        }), 500

    return jsonify({
        "success": True,
        "data": data
    })

@app.route('/api/tools/douyin-video/download', methods=['POST'])
def api_douyin_video_download():
    payload = request.get_json(silent=True) or {}
    play_url = (payload.get('playUrl') or '').strip()
    title = payload.get('title') or 'douyin-video'

    if not play_url.startswith(('http://', 'https://')):
        return jsonify({
            "success": False,
            "message": "缺少可下载的视频地址。"
        }), 400

    safe_title = re.sub(r'[\\/:*?"<>|\r\n]+', '_', title).strip('_')[:80] or 'douyin-video'

    try:
        upstream = requests.get(
            play_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.douyin.com/",
            },
            stream=True,
            timeout=30,
        )
        upstream.raise_for_status()
    except requests.RequestException as exc:
        return jsonify({
            "success": False,
            "message": f"下载视频失败：{exc}"
        }), 502

    def generate():
        for chunk in upstream.iter_content(chunk_size=1024 * 256):
            if chunk:
                yield chunk

    response = Response(generate(), mimetype=upstream.headers.get('content-type') or 'video/mp4')
    response.headers['Content-Disposition'] = f'attachment; filename="{safe_title}.mp4"'
    response.headers['Cache-Control'] = 'no-store'
    content_length = upstream.headers.get('content-length')
    if content_length:
        response.headers['Content-Length'] = content_length
    return response

def scheduled_job():
    print("Running scheduled daily article generation...")
    generate_daily_articles()
    
    print("Articles generated. Triggering static site build...")
    try:
        from build_dist import freezer
        freezer.app.config['FREEZER_DEFAULT_MIMETYPE'] = 'text/html'
        freezer.app.config['FREEZER_REMOVE_EXTRA_FILES'] = False
        print(f"Building static site to: {freezer.app.config['FREEZER_DESTINATION']}")
        freezer.freeze()
        print("Build complete! Static site updated.")
    except Exception as e:
        print(f"Error during static site build: {e}")

def run_scheduler():
    """Background thread to run scheduled tasks"""
    # Run the agent and then build the static site every day at 00:00 (Midnight)
    schedule.every().day.at("00:00").do(scheduled_job)
    
    # You can also run it every few minutes for testing if needed
    # schedule.every(10).minutes.do(scheduled_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    # Start the scheduler thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("Starting server...")
    try:
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        print(f"Error: {e}")
