import os
import random
import subprocess
from datetime import date

import isodate
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

API_KEY = os.environ["YOUTUBE_API_KEY"]
DB_USER = os.environ.get("PG_USER", "postgres")
DB_PASSWORD = os.environ["PG_PASSWORD"]
DB_PORT = os.environ.get("PG_PORT", "5432")
DB_NAME = os.environ.get("PG_DB", "youtube_db")

try:
    DB_HOST = subprocess.check_output(
        "ip route show default | awk '{print $3}'", shell=True
    ).decode().strip()
except Exception:
    DB_HOST = "127.0.0.1"

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

MAX_QUOTA_LIMIT = 10000
REGIONS = [
    "AE", "AM", "AR", "AT", "AU", "AZ", "BA", "BD", "BE", "BG", "BH", "BO",
    "BR", "BY", "CA", "CH", "CL", "CO", "CR", "CY", "CZ", "DE", "DK", "DO",
    "DZ", "EC", "EE", "EG", "ES", "FI", "FR", "GB", "GE", "GH", "GR", "GT",
    "HK", "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IQ", "IS", "IT", "JM",
    "JO", "JP", "KE", "KH", "KR", "KW", "KZ", "LA", "LB", "LI", "LK", "LT",
    "LU", "LV", "LY", "MA", "MD", "ME", "MK", "MT", "MX", "MY", "NG", "NI",
    "NL", "NO", "NP", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PR",
    "PT", "PY", "QA", "RO", "RS", "RU", "SA", "SE", "SG", "SI", "SK", "SN",
    "SV", "TH", "TN", "TR", "TW", "TZ", "UA", "UG", "US", "UY", "VE", "VN",
    "YE", "ZA", "ZW",
]

quota_used = 0


class QuotaExceeded(Exception):
    pass


def api_call(request):
    global quota_used
    if quota_used >= MAX_QUOTA_LIMIT:
        raise QuotaExceeded()
    quota_used += 1
    try:
        return request.execute()
    except HttpError as e:
        if e.resp.status == 403 and "quota" in str(e).lower():
            raise QuotaExceeded()
        raise


def upsert(engine, table_name, df, conflict_cols, update_cols=None):
    if df is None or df.empty:
        return 0
    df = df.drop_duplicates(subset=conflict_cols, keep="last")
    df = df.astype(object).where(pd.notnull(df), None)
    table = Table(table_name, MetaData(), autoload_with=engine)
    records = df.to_dict("records")
    with engine.begin() as conn:
        for i in range(0, len(records), 1000):
            stmt = pg_insert(table).values(records[i:i + 1000])
            if update_cols:
                stmt = stmt.on_conflict_do_update(
                    index_elements=conflict_cols,
                    set_={c: stmt.excluded[c] for c in update_cols},
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
            conn.execute(stmt)
    return len(records)


def fetch_region(youtube, region, seen_video_ids):
    """Bir region üçün videoları və kateqoriyaları qaytarır. Kvota bitərsə, topladığını qaytarır."""
    items, categories, quota_hit = [], {}, False
    try:
        cat_res = api_call(youtube.videoCategories().list(part="snippet", regionCode=region))
        cat_ids = []
        for c in cat_res.get("items", []):
            categories[int(c["id"])] = c["snippet"]["title"]
            if c["snippet"].get("assignable"):
                cat_ids.append(c["id"])

        for cat_id in cat_ids:
            page_token = None
            while True:
                try:
                    res = api_call(youtube.videos().list(
                        part="snippet,contentDetails,statistics",
                        chart="mostPopular",
                        regionCode=region,
                        videoCategoryId=cat_id,
                        maxResults=50,
                        pageToken=page_token,
                    ))
                except HttpError:
                    break  # bu kateqoriya bu regionda dəstəklənmir
                for it in res.get("items", []):
                    if it["id"] not in seen_video_ids:
                        seen_video_ids.add(it["id"])
                        items.append(it)
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
    except QuotaExceeded:
        quota_hit = True
    except HttpError as e:
        print(f"[{region}] HttpError: {e}")
    return items, categories, quota_hit


def fetch_channels(youtube, channel_ids):
    rows, quota_hit = [], False
    ids = list(channel_ids)
    try:
        for i in range(0, len(ids), 50):
            res = api_call(youtube.channels().list(
                part="snippet,statistics", id=",".join(ids[i:i + 50])
            ))
            for it in res.get("items", []):
                rows.append({
                    "channel_id": it["id"],
                    "channel_title": it["snippet"]["title"],
                    "custom_url": it["snippet"].get("customUrl", ""),
                    "country": it["snippet"].get("country", "Unknown"),
                    "subscriber_count": int(it["statistics"].get("subscriberCount", 0)),
                    "total_views": int(it["statistics"].get("viewCount", 0)),
                })
    except QuotaExceeded:
        quota_hit = True
    except HttpError as e:
        print(f"Kanal sorğusu xətası: {e}")
    return rows, quota_hit


def build_frames(items, today_key):
    facts, videos = [], []
    for it in items:
        sn, st, cd = it["snippet"], it.get("statistics", {}), it.get("contentDetails", {})
        v = int(st.get("viewCount", 0))
        l = int(st.get("likeCount", 0))
        c = int(st.get("commentCount", 0))
        dur = int(isodate.parse_duration(cd.get("duration", "PT0S")).total_seconds())
        facts.append({
            "video_id": it["id"],
            "channel_id": sn["channelId"],
            "category_id": int(sn.get("categoryId", 0)),
            "date_key": today_key,
            "views": v,
            "likes": l,
            "comments": c,
            "engagement_rate": round((l + c) / v * 100, 2) if v > 0 else 0,
        })
        videos.append({
            "video_id": it["id"],
            "title": sn["title"],
            "published_at": pd.to_datetime(sn["publishedAt"]),
            "duration_sec": dur,
            "is_short": dur <= 60,
            "language": sn.get("defaultAudioLanguage", sn.get("defaultLanguage", "Unknown")),
        })
    return pd.DataFrame(facts), pd.DataFrame(videos)


def run_pipeline():
    global quota_used
    quota_used = 0

    youtube = build("youtube", "v3", developerKey=API_KEY, cache_discovery=False)
    engine = create_engine(DB_URL, pool_pre_ping=True)
    today_key = int(date.today().strftime("%Y%m%d"))

    regions = REGIONS[:]
    random.shuffle(regions)

    seen_video_ids, known_channels = set(), set()
    total_videos = 0

    for region in regions:
        items, categories, quota_hit = fetch_region(youtube, region, seen_video_ids)

        if items:
            df_fact, df_videos = build_frames(items, today_key)

            # Kateqoriyalar (əskik olanlar üçün placeholder)
            cat_rows = {int(k): v for k, v in categories.items()}
            for cid in df_fact["category_id"].unique():
                cat_rows.setdefault(int(cid), f"Unknown {cid}")
            df_cat = pd.DataFrame(
                [{"category_id": k, "category_name": v} for k, v in cat_rows.items()]
            )

            # Kanallar
            new_channels = set(df_fact["channel_id"]) - known_channels
            ch_rows, ch_quota_hit = fetch_channels(youtube, new_channels)
            quota_hit = quota_hit or ch_quota_hit
            fetched = {r["channel_id"] for r in ch_rows}
            for cid in new_channels - fetched:
                ch_rows.append({
                    "channel_id": cid, "channel_title": "Unknown", "custom_url": "",
                    "country": "Unknown", "subscriber_count": 0, "total_views": 0,
                })
            df_channels = pd.DataFrame(ch_rows)
            known_channels |= new_channels

            # Bazaya yaz (hər region bitdikcə)
            upsert(engine, "dim_categories", df_cat, ["category_id"])
            upsert(engine, "dim_channels", df_channels, ["channel_id"])
            upsert(engine, "dim_videos", df_videos, ["video_id"])
            upsert(
                engine, "fact_video_performance", df_fact,
                ["video_id", "date_key"],
                update_cols=["channel_id", "category_id", "views", "likes", "comments", "engagement_rate"],
            )
            total_videos += len(df_videos)
            print(f"[{region}] {len(df_videos)} video yazıldı | kvota: {quota_used}")

        if quota_hit:
            print("⚠️ Kvota bitdi. Toplanan data bazaya yazıldı, proses dayandırılır.")
            break

    print(f"🎉 ETL bitdi. Cəmi {total_videos} video yükləndi. İstifadə olunan kvota: {quota_used}")
