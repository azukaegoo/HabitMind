import os
import json
import random
import logging
import requests
from collections import Counter, defaultdict
from itertools import combinations

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Helper function for insights
# ═══════════════════════════════════════════

def load_json_file(filename):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", filename)

    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_mood_range(avg_mood):
    if avg_mood >= 7:
        return "high_mood"
    elif avg_mood >= 4:
        return "medium_mood"
    return "low_mood"


def get_base_reflection(habit_name, category, avg_mood):
    templates = load_json_file("reflection_templates.json")
    mood_range = get_mood_range(avg_mood)

    specific_habits = templates.get("specific_habits", {})
    categories = templates.get("categories", {})

    if habit_name in specific_habits:
        options = specific_habits[habit_name].get(mood_range, [])
    else:
        options = categories.get(category, {}).get(mood_range, [])

    if options:
        return random.choice(options)

    return "Keep tracking your habits to discover patterns in your mood over time."


def apply_reflection_tone(base_reflection, tone):
    tone_templates = load_json_file("tone_templates.json")

    if not tone:
        tone = "balanced"

    tone_data = tone_templates.get(tone, tone_templates.get("balanced"))

    prefix = random.choice(tone_data.get("prefixes", [""]))
    suffix = random.choice(tone_data.get("suffixes", [""]))

    return f"{prefix} {base_reflection} {suffix}".strip()

def generate_reflection(top_habits, avg_mood, tone=None):
    if not top_habits:
        return {
            "text": "Keep tracking your habits to discover patterns in your mood over time.",
            "habit": None,
            "emoji": "✨"
        }

    main_habit = top_habits[0]

    habit_names = [habit["name"] for habit in top_habits]
    categories = list({habit["category"] for habit in top_habits})

    base_reflection = get_base_reflection(
        habit_name=main_habit["name"],
        category=main_habit["category"],
        avg_mood=avg_mood
    )

    if len(top_habits) >= 2:
        habit_text = ", ".join(habit_names[:-1]) + f", and {habit_names[-1]}"

        if len(categories) >= 2:
            combined_intro = (
                f"Looking at your recent habit pattern, {habit_text} stood out across "
                f"different wellbeing areas. "
            )
        else:
            combined_intro = (
                f"Looking at your recent habit pattern, {habit_text} appeared consistently "
                f"in your routine. "
            )

        base_reflection = combined_intro + base_reflection
    else:
        base_reflection = (
            f"Based on your recent routine, {main_habit['emoji']} "
            f"{main_habit['name']} stood out. {base_reflection}"
        )

    final_reflection = apply_reflection_tone(
        base_reflection=base_reflection,
        tone=tone
    )

    return {
        "text": final_reflection,
        "habit": main_habit["name"],
        "emoji": main_habit["emoji"]
    }


def get_recommendation_intents(habit_name):
    intents_data = load_json_file("recommendation_intents.json")
    return intents_data.get(habit_name, ["park", "cafe"])


def get_fallback_recommendations(category):
    fallback_data = load_json_file("recommendation_fallback.json")

    items = fallback_data.get(
        category,
        fallback_data.get("General", [])
    )

    for item in items:
        item["is_fallback"] = True
        item["url"] = None
        item["lat"] = None
        item["lon"] = None

    return items


def get_osm_query_parts(intents):
    mapping = {
        "gym": 'node["leisure"="fitness_centre"]',
        "park": 'node["leisure"="park"]',
        "trail": 'node["highway"="path"]',
        "yoga": 'node["sport"="yoga"]',
        "wellness": 'node["leisure"="fitness_centre"]',
        "quiet_space": 'node["amenity"="library"]',
        "library": 'node["amenity"="library"]',
        "cafe": 'node["amenity"="cafe"]',
        "market": 'node["amenity"="marketplace"]',
        "healthy_food": 'node["shop"="greengrocer"]',
        "museum": 'node["tourism"="museum"]',
        "garden": 'node["leisure"="garden"]',
        "community": 'node["amenity"="community_centre"]'
    }

    return [mapping[i] for i in intents if i in mapping]


def get_place_type_from_osm(tags):
    if tags.get("leisure") == "park":
        return "park"

    if tags.get("leisure") == "garden":
        return "garden"

    if tags.get("leisure") == "fitness_centre":
        return "gym"

    if tags.get("amenity") == "library":
        return "library"

    if tags.get("amenity") == "cafe":
        return "cafe"

    if tags.get("amenity") == "marketplace" or tags.get("shop") == "greengrocer":
        return "market"

    if tags.get("tourism") == "museum":
        return "museum"

    if tags.get("amenity") == "community_centre":
        return "community"

    if tags.get("highway") == "path":
        return "trail"

    return "nearby"


def format_osm_result(item):
    tags = item.get("tags", {})
    name = tags.get("name", "Nearby place")

    lat = item.get("lat") or item.get("center", {}).get("lat")
    lon = item.get("lon") or item.get("center", {}).get("lon")

    url = None
    if lat and lon:
        url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

    place_type = get_place_type_from_osm(tags)
    place_templates = load_json_file("recommendation_place_types.json")
    template = place_templates.get(place_type, place_templates["nearby"])

    return {
        "emoji": template["emoji"],
        "title": name,
        "subtitle": template["subtitle"],
        "tag": template["tag"],
        "url": url,
        "lat": lat,
        "lon": lon
    }


def get_openstreetmap_recommendations(latitude, longitude, intents):
    query_parts = get_osm_query_parts(intents)

    if not query_parts:
        return []

    radius = 3000
    query_lines = []

    for part in query_parts:
        query_lines.append(
            f'{part}(around:{radius},{latitude},{longitude});'
        )

    query_body = "\n".join(query_lines)

    query = f"""
[out:json][timeout:15];
(
{query_body}
);
out tags center 10;
"""

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={
                "User-Agent": "HabitMind/1.0"
            },
            timeout=15
        )

        print("DEBUG OSM status:", response.status_code, flush=True)
        print("DEBUG OSM response:", response.text[:300], flush=True)

        response.raise_for_status()

        elements = response.json().get("elements", [])
        recommendations = []

        seen_names = set()

        for item in elements:
            rec = format_osm_result(item)

            name_key = rec["title"].strip().lower()

            if rec["title"] != "Nearby place" and name_key not in seen_names:
                recommendations.append(rec)
                seen_names.add(name_key)

            if len(recommendations) >= 3:
                break

        return recommendations

    except Exception as e:
        logger.exception("OpenStreetMap API error: %s", e)
        return []

def get_ticketmaster_keyword(intents):
    if "event" in intents:
        return "event"
    if "museum" in intents:
        return "exhibition"
    if "community" in intents:
        return "community"
    if "wellness" in intents or "yoga" in intents:
        return "wellness"

    return None


def get_ticketmaster_recommendations(latitude, longitude, intents):
    api_key = os.getenv("TICKETMASTER_API_KEY")

    if not api_key:
        return []

    keyword = get_ticketmaster_keyword(intents)

    if not keyword:
        return []

    params = {
        "apikey": api_key,
        "latlong": f"{latitude},{longitude}",
        "radius": 20,
        "unit": "km",
        "size": 3,
        "sort": "date,asc",
        "keyword": keyword
    }

    try:
        response = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params=params,
            timeout=6
        )
        response.raise_for_status()

        events = response.json().get("_embedded", {}).get("events", [])
        recommendations = []

        event_templates = load_json_file("recommendation_place_types.json")
        event_template = event_templates.get("event")

        for event in events[:3]:
            date = event.get("dates", {}).get("start", {}).get("localDate", "Upcoming event")
            event_url = event.get("url")

            recommendations.append({
                "emoji": event_template["emoji"],
                "title": event.get("name", "Local event"),
                "subtitle": f"{event_template['subtitle']} • {date}",
                "tag": event_template["tag"],
                "url": event_url,
                "lat": None,
                "lon": None
            })

        return recommendations

    except Exception as e:
        logger.exception("Ticketmaster API error: %s", e)
        return []


def get_location_recommendations(
    latitude,
    longitude,
    habit_name,
    category
):
    intents = get_recommendation_intents(habit_name)

    recommendations = []

    recommendations.extend(
        get_openstreetmap_recommendations(
            latitude,
            longitude,
            intents
        )
    )

    recommendations.extend(
        get_ticketmaster_recommendations(
            latitude,
            longitude,
            intents
        )
    )

    print("DEBUG get_location_recommendations", flush=True)
    print("DEBUG recommendations:", recommendations, flush=True)

    if recommendations:
        return recommendations[:3]

    print("DEBUG Using fallback recommendations", flush=True)

    return get_fallback_recommendations(category)

def build_top_habits(checkins, limit=3):
    habit_counter = Counter()
    habit_lookup = {}

    for checkin in checkins:
        for item in checkin.habits:
            if item.habit:
                habit_counter[item.habit.name] += 1
                habit_lookup[item.habit.name] = item.habit

    top_habits = []

    for habit_name, count in habit_counter.most_common(limit):
        habit = habit_lookup[habit_name]

        top_habits.append({
            "name": habit.name,
            "category": habit.category,
            "emoji": habit.icon or "✨",
            "count": count
        })

    return top_habits


def generate_noticed_patterns(checkins, top_habits, avg_mood):
    patterns = []

    if not checkins or not top_habits:
        return ["Your patterns will appear here after a few check-ins."]

    habit_day_count = Counter()
    habit_mood_scores = defaultdict(list)

    pair_count = Counter()
    pair_mood_scores = defaultdict(list)

    category_count = Counter()

    for checkin in checkins:
        habits = []

        for item in checkin.habits:
            if item.habit:
                habit = item.habit
                habits.append(habit)

                habit_day_count[habit.name] += 1
                habit_mood_scores[habit.name].append(checkin.mood_score)
                category_count[habit.category] += 1

        unique_habit_names = sorted({habit.name for habit in habits})

        for pair in combinations(unique_habit_names, 2):
            pair_count[pair] += 1
            pair_mood_scores[pair].append(checkin.mood_score)

    checkin_done = len(checkins)

    # 1. Strongest habit
    strongest = top_habits[0]

    patterns.append(
        f"<strong>{strongest['name']}</strong> appeared in "
        f"<strong>{strongest['count']}/{checkin_done}</strong> check-ins, "
        f"making it your most consistent habit this period."
    )

    # 2. Best habit pair
    if pair_count:
        best_pair = None
        best_pair_score = -1

        for pair, count in pair_count.items():
            if count < 2:
                continue

            avg_pair_mood = sum(pair_mood_scores[pair]) / len(pair_mood_scores[pair])

            if avg_pair_mood > best_pair_score:
                best_pair = pair
                best_pair_score = avg_pair_mood

        if best_pair:
            patterns.append(
                f"<strong>{best_pair[0]}</strong> and <strong>{best_pair[1]}</strong> "
                f"often appeared together and were associated with an average mood of "
                f"<strong>{round(best_pair_score, 1)}/10</strong>."
            )

    # 3. Best single habit mood association
    best_habit = None
    best_habit_score = -1

    for habit_name, moods in habit_mood_scores.items():
        if len(moods) < 2:
            continue

        habit_avg = sum(moods) / len(moods)

        if habit_avg > best_habit_score:
            best_habit = habit_name
            best_habit_score = habit_avg

    if best_habit:
        patterns.append(
            f"Days with <strong>{best_habit}</strong> had one of your higher mood averages "
            f"this period at <strong>{round(best_habit_score, 1)}/10</strong>."
        )

    # 4. Category balance
    if category_count:
        top_categories = [category for category, _ in category_count.most_common(3)]

        if len(top_categories) >= 2:
            patterns.append(
                f"Your habits covered multiple wellbeing areas, including "
                f"<strong>{', '.join(top_categories)}</strong>."
            )
        else:
            patterns.append(
                f"Most of your completed habits came from <strong>{top_categories[0]}</strong>, "
                f"showing this was your strongest focus area."
            )

    # 5. Average mood summary
    patterns.append(
        f"Your average mood for this insight period was <strong>{avg_mood}/10</strong>."
    )

    # 6. Data quality note
    if checkin_done < 7:
        patterns.append(
            f"You completed <strong>{checkin_done}/7</strong> check-ins. "
            f"More check-ins can make future patterns more accurate."
        )

    return patterns[:5]