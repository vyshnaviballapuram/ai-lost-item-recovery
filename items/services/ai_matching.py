"""
AI Matching Service for AI-Based Campus Lost-Item Recovery System.

Compares Lost and Found reports using:
1. TF-IDF Textual Vectorization & Cosine Similarity (Scikit-Learn)
2. Category and Subcategory Hierarchy Compatibility
3. Distinctive Marks & Keyword Attribute Matching
4. Campus Location Proximity
5. Temporal Chronological Compatibility
"""

import logging
import re
from datetime import date
from django.conf import settings
from django.db import transaction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Campus landmark keywords for location correlation
CAMPUS_ZONES = [
    ('library', ['library', 'reading room', 'reference desk', 'study hall', 'stacks']),
    ('cafeteria', ['cafeteria', 'canteen', 'food court', 'cafe', 'mess', 'dining']),
    ('sports', ['sports complex', 'gym', 'gymnasium', 'stadium', 'ground', 'badminton', 'court']),
    ('engineering', ['engineering block', 'engg', 'computer lab', 'ece', 'mech', 'workshop']),
    ('science', ['science block', 'physics lab', 'chemistry lab', 'biotech']),
    ('admin', ['admin block', 'dean office', 'registrar', 'reception', 'auditorium']),
    ('hostel', ['hostel', 'dorm', 'residence hall', 'block a', 'block b', 'block c']),
    ('parking', ['parking lot', 'cycle stand', 'main gate', 'security post', 'bus stop']),
]

COMMON_BRANDS = [
    'apple', 'iphone', 'ipad', 'macbook', 'airpods', 'samsung', 'galaxy',
    'dell', 'hp', 'lenovo', 'asus', 'acer', 'sony', 'casio', 'titan',
    'fossil', 'nike', 'adidas', 'wildcraft', 'fastrack', 'boat', 'jbl',
    'oneplus', 'xiaomi', 'redmi', 'google', 'pixel', 'lenovo'
]

COMMON_COLORS = [
    'black', 'white', 'silver', 'grey', 'gray', 'blue', 'navy', 'red',
    'green', 'yellow', 'brown', 'gold', 'rose gold', 'pink', 'purple',
    'orange', 'space gray', 'metallic', 'transparent'
]


def _extract_tokens(text):
    """Normalize and extract lowercase alphabetic/numeric tokens."""
    if not text:
        return set()
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    return set(token for token in cleaned.split() if len(token) > 1)


def compute_text_similarity(lost_text, found_text):
    """
    Compute TF-IDF text similarity between combined titles and descriptions.
    Returns float score between 0.0 and 100.0.
    """
    lost_str = (lost_text or "").strip()
    found_str = (found_text or "").strip()

    if not lost_str or not found_str:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            token_pattern=r'(?u)\b[a-zA-Z0-9]{2,}\b',
            ngram_range=(1, 2)
        )
        tfidf_matrix = vectorizer.fit_transform([lost_str, found_str])
        cos_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        score = float(cos_sim * 100.0)

        # Check token intersection for bonus reinforcement on small texts
        lost_tokens = _extract_tokens(lost_str)
        found_tokens = _extract_tokens(found_str)
        if lost_tokens and found_tokens:
            jaccard = len(lost_tokens & found_tokens) / len(lost_tokens | found_tokens)
            score = max(score, jaccard * 100.0)

        return min(max(score, 0.0), 100.0)
    except Exception as e:
        logger.warning(f"TF-IDF text similarity calculation fallback: {e}")
        # Robust Jaccard fallback
        lost_tokens = _extract_tokens(lost_str)
        found_tokens = _extract_tokens(found_str)
        if not lost_tokens or not found_tokens:
            return 0.0
        overlap = len(lost_tokens & found_tokens)
        return min((overlap / max(len(lost_tokens), len(found_tokens))) * 100.0, 100.0)


def compute_category_similarity(lost_report, found_report):
    """
    Compute category and subcategory compatibility.
    Returns score (0.0 to 100.0) and justification reason.
    """
    reasons = []
    if lost_report.category_id == found_report.category_id:
        score = 80.0
        reasons.append(f"Category matched: Both items are '{lost_report.category.name}'")

        # Subcategory comparison
        lost_sub = (lost_report.subcategory or "").strip().lower()
        found_sub = (found_report.subcategory or "").strip().lower()
        if lost_sub and found_sub:
            if lost_sub == found_sub:
                score = 100.0
                reasons.append(f"Subcategory match: Both specify '{lost_report.subcategory}'")
            elif lost_sub in found_sub or found_sub in lost_sub:
                score = 95.0
                reasons.append(f"Subcategory overlap: '{lost_report.subcategory}' and '{found_report.subcategory}'")
            else:
                score = 70.0
        return score, reasons

    # Incompatible categories
    reasons.append(
        f"Category mismatch: '{lost_report.category.name}' vs '{found_report.category.name}'"
    )
    return 10.0, reasons


def compute_attribute_similarity(lost_report, found_report):
    """
    Evaluates brand, color, distinctive marks, and item attributes.
    Returns score (0.0 to 100.0) and justification reasons.
    """
    reasons = []
    lost_full = f"{lost_report.title} {lost_report.subcategory} {lost_report.description} {lost_report.distinctive_marks}".lower()
    found_full = f"{found_report.title} {found_report.subcategory} {found_report.description} {found_report.distinctive_marks}".lower()

    # Brand compatibility
    lost_brands = {b for b in COMMON_BRANDS if b in lost_full}
    found_brands = {b for b in COMMON_BRANDS if b in found_full}
    brand_score = 50.0  # neutral if unmentioned

    if lost_brands and found_brands:
        common_brands = lost_brands & found_brands
        if common_brands:
            brand_score = 100.0
            reasons.append(f"Brand match: Shared brand '{', '.join(common_brands).title()}'")
        else:
            brand_score = 10.0
            reasons.append(f"Brand conflict: '{', '.join(lost_brands)}' vs '{', '.join(found_brands)}'")
    elif lost_brands or found_brands:
        brand_score = 50.0

    # Color compatibility
    lost_colors = {c for c in COMMON_COLORS if c in lost_full}
    found_colors = {c for c in COMMON_COLORS if c in found_full}
    color_score = 50.0

    if lost_colors and found_colors:
        common_colors = lost_colors & found_colors
        if common_colors:
            color_score = 95.0
            reasons.append(f"Color match: Identical color identified '{', '.join(common_colors)}'")
        else:
            color_score = 25.0
            reasons.append(f"Color divergence: '{', '.join(lost_colors)}' vs '{', '.join(found_colors)}'")

    # Distinctive marks overlap
    marks_lost_tokens = _extract_tokens(lost_report.distinctive_marks)
    marks_found_tokens = _extract_tokens(found_report.distinctive_marks)
    marks_score = 50.0
    if marks_lost_tokens and marks_found_tokens:
        overlap = marks_lost_tokens & marks_found_tokens
        if overlap:
            marks_score = 90.0
            reasons.append(f"Distinctive marking overlap: Shared keywords {list(overlap)[:3]}")

    composite_attr = (brand_score * 0.45) + (color_score * 0.35) + (marks_score * 0.20)
    return min(max(composite_attr, 0.0), 100.0), reasons


def compute_location_similarity(lost_report, found_report):
    """
    Compute campus location compatibility and spatial proximity.
    Returns score (0.0 to 100.0) and justification reasons.
    """
    reasons = []
    lost_loc = f"{lost_report.location_name} {lost_report.location_details}".lower()
    found_loc = f"{found_report.location_name} {found_report.location_details}".lower()

    # Exact string match
    if lost_report.location_name.strip().lower() == found_report.location_name.strip().lower():
        reasons.append(f"Campus location match: Both reported at '{lost_report.location_name}'")
        return 100.0, reasons

    # Campus zone detection
    lost_zones = set()
    found_zones = set()

    for zone_name, keywords in CAMPUS_ZONES:
        if any(kw in lost_loc for kw in keywords):
            lost_zones.add(zone_name)
        if any(kw in found_loc for kw in keywords):
            found_zones.add(zone_name)

    shared_zones = lost_zones & found_zones
    if shared_zones:
        reasons.append(f"Zone proximity: Both locations in campus zone '{', '.join(shared_zones).title()}'")
        return 85.0, reasons

    # Token overlap in location strings
    lost_tokens = _extract_tokens(lost_loc)
    found_tokens = _extract_tokens(found_loc)
    overlap = lost_tokens & found_tokens
    if overlap:
        reasons.append(f"Location descriptor overlap: {list(overlap)[:2]}")
        return 65.0, reasons

    reasons.append(f"Different campus locations: '{lost_report.location_name}' and '{found_report.location_name}'")
    return 35.0, reasons


def compute_date_similarity(lost_report, found_report):
    """
    Compute temporal timeline coherence.
    A lost item should realistically be lost on or shortly before it was found.
    """
    reasons = []
    lost_d = lost_report.date_occurred
    found_d = found_report.date_occurred

    delta_days = (found_d - lost_d).days

    if delta_days == 0:
        reasons.append("Timeline alignment: Lost and found on the exact same date")
        return 100.0, reasons
    elif 1 <= delta_days <= 3:
        reasons.append(f"Consistent timeline: Item found {delta_days} day(s) after being reported lost")
        return 95.0, reasons
    elif 4 <= delta_days <= 14:
        reasons.append(f"Plausible timeline: Item found {delta_days} days after being lost")
        return 80.0, reasons
    elif 15 <= delta_days <= 45:
        reasons.append(f"Extended interval: Item found {delta_days} days after being lost")
        return 60.0, reasons
    elif delta_days > 45:
        reasons.append(f"Large time gap: Item found {delta_days} days later")
        return 35.0, reasons
    elif -2 <= delta_days < 0:
        # User might have estimated lost date within 1-2 days
        reasons.append("Minor date offset: Estimated lost date is 1-2 days after reported found date")
        return 65.0, reasons
    else:
        reasons.append(f"Timeline anomaly: Found date is {abs(delta_days)} days before lost date")
        return 20.0, reasons


def evaluate_report_pair(lost_report, found_report, weights=None):
    """
    Evaluate similarity between a LOST report and a FOUND report.
    Returns:
        dict with composite similarity score, subscores, and reasons list.
    """
    # CRITICAL INVARIANT: Cannot compare same reports or same types
    if lost_report.id == found_report.id:
        raise ValueError("Cannot compare a report with itself.")
    if lost_report.report_type != 'LOST' or found_report.report_type != 'FOUND':
        raise ValueError("AI recovery evaluation requires exactly one LOST report and one FOUND report.")

    if weights is None:
        weights = getattr(
            settings,
            'AI_MATCHING_WEIGHTS',
            {'text': 0.45, 'category': 0.20, 'attributes': 0.15, 'location': 0.10, 'date': 0.10}
        )

    # 1. Text Similarity (TF-IDF + Title & Description)
    lost_text = f"{lost_report.title} {lost_report.description}"
    found_text = f"{found_report.title} {found_report.description}"
    text_score = compute_text_similarity(lost_text, found_text)

    # 2. Category Similarity
    cat_score, cat_reasons = compute_category_similarity(lost_report, found_report)

    # 3. Attribute Similarity
    attr_score, attr_reasons = compute_attribute_similarity(lost_report, found_report)

    # 4. Location Similarity
    loc_score, loc_reasons = compute_location_similarity(lost_report, found_report)

    # 5. Date Similarity
    date_score, date_reasons = compute_date_similarity(lost_report, found_report)

    # Weighted composite score
    w_text = weights.get('text', 0.45)
    w_cat = weights.get('category', 0.20)
    w_attr = weights.get('attributes', 0.15)
    w_loc = weights.get('location', 0.10)
    w_date = weights.get('date', 0.10)

    composite = (
        (text_score * w_text) +
        (cat_score * w_cat) +
        (attr_score * w_attr) +
        (loc_score * w_loc) +
        (date_score * w_date)
    )
    composite = round(min(max(composite, 0.0), 100.0), 1)

    all_reasons = []
    if text_score >= 60:
        all_reasons.append(f"High description lexical similarity ({text_score:.1f}%)")
    elif text_score >= 35:
        all_reasons.append(f"Moderate description similarity ({text_score:.1f}%)")

    all_reasons.extend(cat_reasons)
    all_reasons.extend(attr_reasons)
    all_reasons.extend(loc_reasons)
    all_reasons.extend(date_reasons)

    return {
        'similarity_score': composite,
        'text_similarity': round(text_score, 1),
        'category_similarity': round(cat_score, 1),
        'attribute_similarity': round(attr_score, 1),
        'location_similarity': round(loc_score, 1),
        'date_similarity': round(date_score, 1),
        'matching_reasons': all_reasons,
    }


def run_ai_matching_for_report(target_report):
    """
    Run AI matching engine for a newly submitted or updated report.
    Compares against compatible counterpart reports and updates/creates ItemMatch records.
    Catches errors gracefully and marks report ai_processed status.
    """
    from items.models import ItemReport, ItemMatch
    from notifications.models import Notification

    created_matches = []
    try:
        threshold = getattr(settings, 'AI_MATCH_THRESHOLD', 50.0)

        if target_report.report_type == 'LOST':
            # Compare against FOUND reports (excluding REJECTED or ARCHIVED)
            candidates = ItemReport.objects.filter(
                report_type='FOUND'
            ).exclude(approval_status__in=['REJECTED', 'ARCHIVED'])
            
            for candidate in candidates:
                result = evaluate_report_pair(target_report, candidate)
                if result['similarity_score'] >= threshold:
                    with transaction.atomic():
                        match_obj, created = ItemMatch.objects.update_or_create(
                            lost_report=target_report,
                            found_report=candidate,
                            defaults={
                                'similarity_score': result['similarity_score'],
                                'text_similarity': result['text_similarity'],
                                'category_similarity': result['category_similarity'],
                                'attribute_similarity': result['attribute_similarity'],
                                'location_similarity': result['location_similarity'],
                                'date_similarity': result['date_similarity'],
                                'matching_reasons': result['matching_reasons'],
                                'is_active': True,
                            }
                        )
                        created_matches.append(match_obj)
        else:
            # Candidate is FOUND; compare against LOST reports
            candidates = ItemReport.objects.filter(
                report_type='LOST'
            ).exclude(approval_status__in=['REJECTED', 'ARCHIVED'])

            for candidate in candidates:
                result = evaluate_report_pair(candidate, target_report)
                if result['similarity_score'] >= threshold:
                    with transaction.atomic():
                        match_obj, created = ItemMatch.objects.update_or_create(
                            lost_report=candidate,
                            found_report=target_report,
                            defaults={
                                'similarity_score': result['similarity_score'],
                                'text_similarity': result['text_similarity'],
                                'category_similarity': result['category_similarity'],
                                'attribute_similarity': result['attribute_similarity'],
                                'location_similarity': result['location_similarity'],
                                'date_similarity': result['date_similarity'],
                                'matching_reasons': result['matching_reasons'],
                                'is_active': True,
                            }
                        )
                        created_matches.append(match_obj)

        target_report.ai_processed = True
        target_report.ai_processing_error = ""
        target_report.save(update_fields=['ai_processed', 'ai_processing_error'])

    except Exception as e:
        logger.exception(f"Error during AI matching for report {target_report.report_id}: {e}")
        target_report.ai_processed = False
        target_report.ai_processing_error = str(e)
        target_report.save(update_fields=['ai_processed', 'ai_processing_error'])

    return created_matches


def deactivate_matches_for_report(report):
    """
    When a report is rejected or archived, mark its active matches as inactive.
    """
    from items.models import ItemMatch
    ItemMatch.objects.filter(
        models_Q_or(lost_report=report, found_report=report)
    ).update(is_active=False)


def models_Q_or(**kwargs):
    from django.db.models import Q
    q = Q()
    for k, v in kwargs.items():
        q |= Q(**{k: v})
    return q
