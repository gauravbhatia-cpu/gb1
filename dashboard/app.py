"""
Dashboard UI. Run with:  streamlit run dashboard/app.py

Reads straight from the database (same models the API/scheduler write
to) so it reflects whatever has been ingested, whether that's real API
pulls or the seeded demo data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.database import SessionLocal, init_db
from app import models
from app.analysis import posting_time, engagement, ad_organic_matcher

st.set_page_config(page_title="Competitor Social Intel", layout="wide")
init_db()


@st.cache_resource
def get_session():
    return SessionLocal()


db = get_session()

st.title("📊 Competitor Social Intelligence")

competitors = db.query(models.Competitor).all()

if not competitors:
    st.warning(
        "No competitors yet. Run `python -m scripts.seed_demo_data` for a demo, "
        "or POST to /competitors on the API to add a real one."
    )
    st.stop()

comp_names = {c.name: c.id for c in competitors}
selected_names = st.sidebar.multiselect(
    "Competitors", options=list(comp_names.keys()), default=list(comp_names.keys())[:2]
)
if not selected_names:
    st.info("Select at least one competitor from the sidebar.")
    st.stop()

selected_ids = [comp_names[n] for n in selected_names]

tab_overview, tab_content, tab_mentions, tab_ads, tab_search = st.tabs(
    ["Overview", "Content & Timing", "Mentions", "Ad Creatives", "Brand Search Interest"]
)

# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
with tab_overview:
    cols = st.columns(len(selected_ids))
    for col, comp_id in zip(cols, selected_ids):
        comp = next(c for c in competitors if c.id == comp_id)
        posts = db.query(models.Post).filter_by(competitor_id=comp_id).all()
        post_dicts = [{
            "posted_at": p.posted_at, "likes": p.likes, "comments": p.comments,
            "shares": p.shares, "views": p.views, "content_type": p.content_type,
        } for p in posts]

        cadence = posting_time.posting_frequency_summary(post_dicts)
        avg_eng = engagement.average_engagement(post_dicts)
        mention_count = db.query(models.Mention).filter_by(competitor_id=comp_id).count()
        ad_count = db.query(models.AdCreative).filter_by(competitor_id=comp_id, is_active=True).count()
        boost_summary = ad_organic_matcher.organic_vs_boosted_summary(posts)

        with col:
            st.subheader(comp.name)
            st.metric("Posts/week", cadence["posts_per_week"])
            st.metric("Avg engagement rate", f"{avg_eng}%" if avg_eng else "n/a")
            st.metric("Mentions tracked", mention_count)
            st.metric("Active ads", ad_count)
            if boost_summary["boosted_pct"] is not None:
                st.metric("Boosted posts", f"{boost_summary['boosted_pct']}%",
                          help="Organic posts with a matching active/recent ad (best-effort content match)")
            st.caption(f"Top content type: {cadence.get('top_content_type') or 'n/a'}")

# --------------------------------------------------------------------------- #
# Content & Timing
# --------------------------------------------------------------------------- #
with tab_content:
    for comp_id in selected_ids:
        comp = next(c for c in competitors if c.id == comp_id)
        st.markdown(f"### {comp.name}")

        posts = db.query(models.Post).filter_by(competitor_id=comp_id).all()
        if not posts:
            st.info("No posts ingested yet for this competitor.")
            continue

        post_dicts = [{
            "posted_at": p.posted_at, "likes": p.likes, "comments": p.comments, "shares": p.shares,
        } for p in posts if p.posted_at]

        heatmap_data = posting_time.build_posting_heatmap(post_dicts)
        matrix = heatmap_data["engagement_matrix"]

        left, right = st.columns([2, 1])
        with left:
            fig = go.Figure(data=go.Heatmap(
                z=matrix, x=heatmap_data["hour_labels"], y=heatmap_data["day_labels"],
                colorscale="Viridis",
            ))
            fig.update_layout(title="Total engagement by day/hour posted", height=350,
                               xaxis_title="Hour of day", yaxis_title="Day of week")
            st.plotly_chart(fig, use_container_width=True)

        with right:
            type_counts = {}
            for p in posts:
                type_counts[p.content_type or "unknown"] = type_counts.get(p.content_type or "unknown", 0) + 1
            fig2 = px.pie(names=list(type_counts.keys()), values=list(type_counts.values()),
                          title="Content type mix")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**Best posting slots (by avg engagement):**")
        best = pd.DataFrame(heatmap_data["best_slots"])
        if not best.empty:
            st.dataframe(best, hide_index=True, use_container_width=True)

        st.markdown("**Recent posts:**")
        filter_choice = st.radio(
            "Show", ["All", "Organic only (no ad running)", "Boosted (matched to an ad)"],
            horizontal=True, key=f"filter_{comp_id}",
        )
        if filter_choice.startswith("Organic"):
            filtered = [p for p in posts if not p.is_boosted]
        elif filter_choice.startswith("Boosted"):
            filtered = [p for p in posts if p.is_boosted]
        else:
            filtered = posts

        recent = sorted(filtered, key=lambda p: p.posted_at or pd.Timestamp.min, reverse=True)[:10]
        recent_df = pd.DataFrame([{
            "posted_at": p.posted_at, "platform": p.platform, "type": p.content_type,
            "status": "🟢 Boosted" if p.is_boosted else ("⚪ Organic only" if p.is_boosted is False else "— not checked"),
            "match_confidence": p.match_confidence,
            "caption": (p.caption or "")[:70], "likes": p.likes, "comments": p.comments, "shares": p.shares,
        } for p in recent])
        st.dataframe(recent_df, hide_index=True, use_container_width=True)
        st.caption(
            "\"Boosted\" is a best-effort text match against this competitor's Ad Library creatives "
            "(no official platform link exists for pages you don't manage) -- run "
            "`POST /competitors/{id}/analyze/match-ads` after each sync to refresh these flags."
        )
        st.divider()

# --------------------------------------------------------------------------- #
# Mentions
# --------------------------------------------------------------------------- #
with tab_mentions:
    for comp_id in selected_ids:
        comp = next(c for c in competitors if c.id == comp_id)
        st.markdown(f"### {comp.name}")

        mentions = db.query(models.Mention).filter_by(competitor_id=comp_id).order_by(models.Mention.published_at.desc()).all()
        if not mentions:
            st.info("No mentions ingested yet. Try POST /competitors/{id}/sync/mentions?query=... on the API.")
            continue

        sentiment_counts = {}
        for m in mentions:
            label = m.sentiment_label or "unlabeled"
            sentiment_counts[label] = sentiment_counts.get(label, 0) + 1

        left, right = st.columns([1, 2])
        with left:
            fig = px.pie(names=list(sentiment_counts.keys()), values=list(sentiment_counts.values()),
                         title="Sentiment breakdown",
                         color=list(sentiment_counts.keys()),
                         color_discrete_map={"positive": "#2ecc71", "neutral": "#95a5a6", "negative": "#e74c3c"})
            st.plotly_chart(fig, use_container_width=True)

        with right:
            m_df = pd.DataFrame([{
                "published_at": m.published_at, "platform": m.platform, "author": m.author,
                "sentiment": m.sentiment_label, "text": (m.text or "")[:120], "url": m.url,
            } for m in mentions[:25]])
            st.dataframe(m_df, hide_index=True, use_container_width=True)
        st.divider()

# --------------------------------------------------------------------------- #
# Ad Creatives
# --------------------------------------------------------------------------- #
with tab_ads:
    for comp_id in selected_ids:
        comp = next(c for c in competitors if c.id == comp_id)
        st.markdown(f"### {comp.name}")

        ads = db.query(models.AdCreative).filter_by(competitor_id=comp_id).all()
        if not ads:
            st.info("No ad data ingested yet. Try POST /competitors/{id}/sync/meta-ads?search_term=... on the API.")
            continue

        ads_df = pd.DataFrame([{
            "active": a.is_active, "start_date": a.start_date, "end_date": a.end_date,
            "creative_text": (a.creative_text or "")[:150], "snapshot_url": a.snapshot_url,
        } for a in ads])
        st.dataframe(ads_df, hide_index=True, use_container_width=True)
        st.divider()

# --------------------------------------------------------------------------- #
# Brand Search Interest
# --------------------------------------------------------------------------- #
with tab_search:
    frames = []
    for comp_id in selected_ids:
        comp = next(c for c in competitors if c.id == comp_id)
        snaps = db.query(models.BrandSearchSnapshot).filter_by(competitor_id=comp_id).order_by(models.BrandSearchSnapshot.date).all()
        if snaps:
            frames.append(pd.DataFrame([{"date": s.date, "interest_score": s.interest_score, "competitor": comp.name} for s in snaps]))

    if frames:
        combined = pd.concat(frames)
        fig = px.line(combined, x="date", y="interest_score", color="competitor",
                      title="Relative search interest over time (Google Trends-style, 0-100)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(
            "No search-interest data yet. This comes from Google Trends via pytrends "
            "(unofficial, but public/no-login data) -- wire it up in app/analysis/brand_search_trends.py."
        )
