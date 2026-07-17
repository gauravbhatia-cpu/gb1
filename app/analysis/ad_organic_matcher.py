"""
Organic-vs-boosted matching.

The question this answers: "of everything this competitor posts organically,
which posts are they ALSO putting ad spend behind, and which are purely
organic with no paid support?"

Important honesty note: there is no official API that links a specific
organic post to a specific Ad Library entry for a page you don't manage.
(If you manage the page yourself, the Graph API's Page > promotable_posts
edge gives you this directly -- but that only works for your own account,
not competitors.) For competitor tracking, the best available signal is a
content match: does the ad's creative text closely resemble a caption the
competitor posted organically around the same time? That's what this module
does, and it reports a confidence score so you can see how strong the match
is rather than presenting a guess as certainty.

Matching approach: plain character-level similarity (e.g. difflib) turned
out to produce false positives on repetitive marketing copy -- two
completely different product pushes that both say "Flash sale: 20% off ...
today only!" score deceptively high on raw text overlap even though they
share no actual product mention. Instead this uses a document-frequency
weighted word overlap: words that recur across many of this competitor's
posts/ads (generic boilerplate like "shop", "new", "today", "collection")
get down-weighted, and words distinctive to a specific post (product names,
specific claims) get up-weighted -- similar in spirit to TF-IDF, without
needing an external NLP dependency.
"""
import logging
import math
import re
from collections import Counter
from typing import List, Optional, Dict, Any

from app import models

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.75          # deliberately strict: a real "boosted post" almost always
                                 # reuses the exact (or near-exact) organic copy as the ad
                                 # creative, so we'd rather under-flag than falsely claim paid
                                 # support behind content that's actually organic-only
MAX_DAYS_APART = 21              # an ad running >3 weeks from the post is unlikely to be it

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: Optional[str]) -> set:
    if not text:
        return set()
    return set(_WORD_RE.findall(text.lower()))


def _build_word_weights(texts: List[Optional[str]]) -> Dict[str, float]:
    """
    Document-frequency weighting: a word that shows up in most of this
    competitor's posts/ads (generic marketing filler) gets a low weight;
    a word that shows up in only one or two gets a high weight.
    """
    doc_freq = Counter()
    docs = [t for t in (_tokenize(x) for x in texts) if t]
    for word_set in docs:
        doc_freq.update(word_set)

    n_docs = max(len(docs), 1)
    return {word: math.log(n_docs / (1 + count)) + 1.0 for word, count in doc_freq.items()}


def _weighted_overlap(text_a: Optional[str], text_b: Optional[str], weights: Dict[str, float]) -> float:
    words_a, words_b = _tokenize(text_a), _tokenize(text_b)
    if not words_a or not words_b:
        return 0.0
    union = words_a | words_b
    if not union:
        return 0.0
    intersection_weight = sum(weights.get(w, 1.0) for w in (words_a & words_b))
    union_weight = sum(weights.get(w, 1.0) for w in union)
    return intersection_weight / union_weight if union_weight else 0.0


def match_posts_to_ads(posts: List[models.Post], ads: List[models.AdCreative]) -> Dict[str, Any]:
    """
    Mutates each Post's is_boosted / matched_ad_id / match_confidence in
    place based on best-match against the given ads. Caller is responsible
    for committing the session. Returns a summary dict.
    """
    boosted_count = 0
    organic_only_count = 0

    all_texts = [p.caption for p in posts] + [a.creative_text for a in ads]
    weights = _build_word_weights(all_texts)

    for post in posts:
        best_ad = None
        best_score = 0.0

        for ad in ads:
            if post.posted_at and ad.start_date:
                days_apart = abs((post.posted_at - ad.start_date).days)
                if days_apart > MAX_DAYS_APART:
                    continue  # too far apart in time to plausibly be the same push

            score = _weighted_overlap(post.caption, ad.creative_text, weights)
            if score > best_score:
                best_score = score
                best_ad = ad

        if best_ad is not None and best_score >= MATCH_THRESHOLD:
            post.is_boosted = True
            post.matched_ad_id = best_ad.id
            post.match_confidence = round(best_score, 3)
            boosted_count += 1
        else:
            post.is_boosted = False
            post.matched_ad_id = None
            post.match_confidence = None
            organic_only_count += 1

    return {
        "total_posts": len(posts),
        "boosted": boosted_count,
        "organic_only": organic_only_count,
        "threshold_used": MATCH_THRESHOLD,
    }


def organic_vs_boosted_summary(posts: List[models.Post]) -> Dict[str, Any]:
    """Read-only summary, for posts that have already been matched (or not)."""
    checked = [p for p in posts if p.is_boosted is not None]
    boosted = [p for p in checked if p.is_boosted]
    organic_only = [p for p in checked if not p.is_boosted]
    unchecked = len(posts) - len(checked)

    return {
        "boosted_count": len(boosted),
        "organic_only_count": len(organic_only),
        "unchecked_count": unchecked,
        "boosted_pct": round(len(boosted) / len(checked) * 100, 1) if checked else None,
    }
