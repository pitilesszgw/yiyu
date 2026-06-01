import sqlite3
from pathlib import Path

from agent import generate_daily_articles
from build_dist import freezer, write_cloudflare_headers, write_deploy_version


DB_PATH = Path(__file__).with_name("yiyu.db")


def get_article_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    count = cur.fetchone()[0]
    conn.close()
    return count


def main() -> int:
    before_count = get_article_count()
    print(f"当前数据库文章数: {before_count}")

    success_count = generate_daily_articles()
    if success_count <= 0:
        raise RuntimeError("本次未生成任何文章，已中止自动发布流程。")

    after_generation_count = get_article_count()
    expected_min_count = before_count + success_count
    if after_generation_count < expected_min_count:
        raise RuntimeError(
            f"文章数量异常减少：生成前 {before_count}，生成后 {after_generation_count}，"
            f"预期至少为 {expected_min_count}。"
        )

    print("开始重新冻结 dist 静态站点...")
    freezer.freeze()
    write_cloudflare_headers()
    write_deploy_version()
    print("dist 静态站点已更新。")

    final_count = get_article_count()
    print(f"自动发布流程完成，当前数据库文章数: {final_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
