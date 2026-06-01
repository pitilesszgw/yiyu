import json
import os
from flask import Flask
from flask_frozen import Freezer
from app import app, get_db

# Set freezer config
app.config['FREEZER_DESTINATION'] = os.path.join(os.path.dirname(__file__), 'dist')
app.config['FREEZER_DEFAULT_MIMETYPE'] = 'text/html'
app.config['FREEZER_REMOVE_EXTRA_FILES'] = False

freezer = Freezer(app)


def write_cloudflare_headers():
    headers_path = os.path.join(app.config['FREEZER_DESTINATION'], '_headers')
    with open(headers_path, 'w', encoding='utf-8') as f:
        f.write(
            "/articles\n"
            "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0\n"
            "/article/*\n"
            "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0\n"
            "/api/articles.json\n"
            "  Cache-Control: no-store, no-cache, must-revalidate, max-age=0\n"
        )


def write_deploy_version():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT id, date, title, title_en FROM articles ORDER BY id DESC LIMIT 1')
        latest = cur.fetchone()

    payload = {
        "latestArticleId": latest["id"] if latest else None,
        "latestArticleDate": latest["date"] if latest else None,
        "latestArticleTitle": latest["title"] if latest else None,
        "latestArticleTitleEn": latest["title_en"] if latest else None,
    }
    if latest:
        payload["version"] = f"{latest['date']}-article-{latest['id']}"

    version_path = os.path.join(app.config['FREEZER_DESTINATION'], 'deploy-version.json')
    with open(version_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

@freezer.register_generator
def article_detail():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT id FROM articles')
        articles = cur.fetchall()
        for article in articles:
            yield {'article_id': article['id']}

if __name__ == '__main__':
    print(f"Building static site to: {app.config['FREEZER_DESTINATION']}")
    freezer.freeze()
    write_cloudflare_headers()
    write_deploy_version()
    print("Build complete!")
