#!/usr/bin/env python3
"""GitHub skill 仓库搜索与排名脚本。

用法:
  python3 github_search_rank.py --query "视频剪辑" [--top 10] [--min-stars 20] [--json out.json]

流程:
  1. 用 GitHub Search API 搜索仓库（多组关键词组合）
  2. 拉取每个候选的详情（star、最近提交、topics）
  3. 检测仓库是否含 SKILL.md（agent skill 的标志）
  4. 按 star热度 / 活跃度 / 相关性 / 文档完整度 加权打分
  5. 输出 Markdown 排名表（可直接贴给用户）

仅用标准库，无第三方依赖。未认证 60 次/小时限流，够用；
若设置了 GITHUB_TOKEN 环境变量则自动带上（5000 次/小时）。
"""

import argparse
import base64
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api_get(url, ok_404=False):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "skill-evolver")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404 and ok_404:
            return None
        if e.code == 403:
            print(f"[warn] GitHub API 限流（403）：{url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[warn] 请求失败 {url}: {e}", file=sys.stderr)
        return None


def search_repos(query, per_page=15, retries=1):
    """按 star 降序搜索仓库；未认证时连续搜索易触发次级限流，403 则等待重试。"""
    q = urllib.parse.quote(query)
    url = f"{API}/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"
    for attempt in range(retries + 1):
        data = api_get(url)
        if data is not None:
            return data.get("items", [])
        if attempt < retries:
            print("[warn] 等待 20 秒后重试该组搜索…", file=sys.stderr)
            time.sleep(20)
    return []


def has_skill_md(full_name):
    """检测仓库根目录是否有 SKILL.md（agent skill 标志）。"""
    data = api_get(f"{API}/repos/{full_name}/contents/SKILL.md", ok_404=True)
    return data is not None


def fetch_readme_head(full_name, chars=3000):
    data = api_get(f"{API}/repos/{full_name}/readme", ok_404=True)
    if not data:
        return ""
    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content[:chars]
    except Exception:
        return ""


def recency_score(pushed_at, now_ts):
    """最近提交越新分越高：30 天内 1.0，线性衰减到 2 年为 0。"""
    try:
        ts = time.mktime(time.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        days = max(0.0, (now_ts - ts) / 86400)
        return max(0.0, 1.0 - days / 730)
    except Exception:
        return 0.0


def relevance_score(repo, keywords):
    """关键词在 name/description/topics 中的命中度（0-1）。"""
    name = (repo.get("name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics") or []).lower()
    text = f"{name} {desc} {topics}"
    if not keywords:
        return 0.5
    hits = sum(1 for kw in keywords if kw.lower() in text)
    name_hit = any(kw.lower() in name for kw in keywords)
    score = hits / len(keywords)
    return min(1.0, score + (0.15 if name_hit else 0.0))


def score_all(candidates, keywords, min_stars):
    now = time.time()
    results = []
    for repo in candidates:
        stars = repo.get("stargazers_count", 0)
        if stars < min_stars:
            continue
        full_name = repo.get("full_name", "")
        star_s = min(1.0, math.log10(stars + 1) / 4.0)  # 10k star ≈ 1.0
        rec_s = recency_score(repo.get("pushed_at", ""), now)
        rel_s = relevance_score(repo, keywords)
        total = 0.25 * star_s + 0.25 * rec_s + 0.35 * rel_s  # skill_md 加分后补
        results.append({
            "full_name": full_name,
            "url": repo.get("html_url", ""),
            "stars": stars,
            "pushed_at": (repo.get("pushed_at") or "")[:10],
            "description": (repo.get("description") or "")[:120],
            "language": repo.get("language") or "-",
            "scores": {"star": round(star_s, 3), "recency": round(rec_s, 3),
                       "relevance": round(rel_s, 3), "skill_md": 0, "total": round(total, 3)},
        })
    return results


def check_and_boost(results):
    """逐个检测 SKILL.md；有则 +0.10 加分。只检查前 top 个，省限流。"""
    for r in results:
        r["scores"]["skill_md"] = 1 if has_skill_md(r["full_name"]) else 0
        r["scores"]["total"] = round(r["scores"]["total"] + 0.10 * r["scores"]["skill_md"], 3)
        time.sleep(0.3)
    return results


def render_table(results, keywords):
    lines = [
        f"## GitHub skill 候选排名（关键词: {', '.join(keywords)}）",
        "",
        "| # | 仓库 | Star | 最近提交 | SKILL.md | 总分 | 简介 |",
        "|---|------|------|----------|----------|------|------|",
    ]
    for i, r in enumerate(results, 1):
        skill_flag = "是" if r["scores"]["skill_md"] else "否"
        s = r["scores"]
        lines.append(
            f"| {i} | [{r['full_name']}]({r['url']}) | {r['stars']} | {r['pushed_at']} "
            f"| {skill_flag} | {s['total']} | {r['description']} |"
        )
    lines += [
        "",
        "评分构成：相关性 35% + star 热度 25% + 活跃度 25% + 含 SKILL.md 加分 10%",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="搜索关键词，如 'video editing skill'")
    ap.add_argument("--keywords", default="", help="逗号分隔的相关性判定关键词，缺省用 query 拆词")
    ap.add_argument("--top", type=int, default=10, help="返回前 N 个候选")
    ap.add_argument("--min-stars", type=int, default=20, help="最低 star 门槛")
    ap.add_argument("--json", default="", help="可选：结果另存 JSON 文件路径")
    args = ap.parse_args()

    kws = [k.strip() for k in args.keywords.split(",") if k.strip()] or args.query.split()

    # 多组查询词提高召回，去重合并
    queries = [args.query, f"{args.query} skill", f"{args.query} agent skill"]
    seen, candidates = set(), []
    for q in queries:
        for repo in search_repos(q):
            name = repo.get("full_name")
            if name and name not in seen:
                seen.add(name)
                candidates.append(repo)
        time.sleep(8.0)  # 未认证搜索限流 10 次/分钟，组间留足间隔

    if not candidates:
        print("未搜到任何候选仓库，请更换关键词。")
        sys.exit(1)

    results = score_all(candidates, kws, args.min_stars)
    if not results:
        print(f"所有候选都低于 --min-stars {args.min_stars}，可降低门槛重试。")
        sys.exit(1)

    # 按总分预排序，只对前 top 个做 SKILL.md 检测（省 API 配额）
    results.sort(key=lambda r: r["scores"]["total"], reverse=True)
    results = check_and_boost(results[: args.top])
    results.sort(key=lambda r: r["scores"]["total"], reverse=True)

    print(render_table(results, kws))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 已保存: {args.json}")


if __name__ == "__main__":
    main()
