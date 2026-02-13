#!/usr/bin/env python3
"""Single-file CPG marketing content generator.

Run:
  pip install streamlit
  streamlit run cpg_app.py
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import streamlit as st


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


ROOT = Path(__file__).resolve().parent
load_env_file(ROOT / ".env")
load_env_file(ROOT / "cpg-app" / ".env")


PRODUCT_DATABASE = [
    {
        "id": "p1",
        "name": "PureGlow Vitamin C Serum",
        "category": "Skincare",
        "brand": "PureGlow Naturals",
        "features": ["30% Vitamin C", "Hyaluronic Acid", "Ferulic Acid", "Vegan", "Cruelty-free"],
        "benefits": ["Brightens skin tone", "Reduces dark spots", "Boosts collagen production", "Deep hydration"],
        "usage": "Apply 3-4 drops to clean face morning and evening. Follow with moisturizer and SPF.",
        "targetAudience": "Women 25-45, skincare enthusiasts, clean beauty advocates",
        "pricePoint": "$34.99",
        "usp": "Clinical-grade Vitamin C in a clean, sustainable formula",
    },
    {
        "id": "p2",
        "name": "FreshBite Protein Crunch Bars",
        "category": "Food & Beverage",
        "brand": "FreshBite Co.",
        "features": ["20g protein", "Gluten-free", "No artificial sweeteners", "Non-GMO", "5g fiber"],
        "benefits": ["Sustained energy", "Muscle recovery support", "Guilt-free snacking", "Keeps you full longer"],
        "usage": "Enjoy as a post-workout snack or mid-day energy boost. Best served chilled.",
        "targetAudience": "Fitness enthusiasts 18-40, health-conscious consumers, busy professionals",
        "pricePoint": "$2.99/bar",
        "usp": "Real food ingredients with macro-friendly nutrition",
    },
    {
        "id": "p3",
        "name": "EcoClean All-Purpose Spray",
        "category": "Household",
        "brand": "EcoClean Home",
        "features": ["Plant-based formula", "Biodegradable", "No harsh chemicals", "Recyclable packaging", "EPA Safer Choice certified"],
        "benefits": ["Cuts grease effectively", "Safe around kids and pets", "Fresh lavender scent", "Streak-free clean"],
        "usage": "Spray directly on surfaces. Wipe with cloth. No rinsing needed.",
        "targetAudience": "Eco-conscious families, parents with young children, sustainability advocates",
        "pricePoint": "$6.49",
        "usp": "Powerful cleaning without compromising your family's health or the planet",
    },
    {
        "id": "p4",
        "name": "ZenBrew Adaptogenic Coffee",
        "category": "Food & Beverage",
        "brand": "ZenBrew",
        "features": ["Organic Arabica", "Lion's Mane mushroom", "Ashwagandha", "L-Theanine", "Medium roast"],
        "benefits": ["Calm focus without jitters", "Enhanced cognitive function", "Stress reduction", "Smooth, rich flavor"],
        "usage": "Brew 2 tbsp per 6oz water. French press or drip recommended. Enjoy hot or iced.",
        "targetAudience": "Wellness-focused professionals 25-50, biohackers, mindful consumers",
        "pricePoint": "$24.99/bag",
        "usp": "Where ancient adaptogens meet artisan coffee",
    },
    {
        "id": "p5",
        "name": "LuxeLocks Keratin Repair Mask",
        "category": "Haircare",
        "brand": "LuxeLocks Paris",
        "features": ["Keratin complex", "Argan oil", "Silk proteins", "Color-safe", "Sulfate-free"],
        "benefits": ["Repairs damage in one use", "72-hour frizz control", "Salon-quality results at home", "Restores shine and elasticity"],
        "usage": "Apply generously to damp hair. Leave for 5-10 minutes. Rinse thoroughly. Use weekly.",
        "targetAudience": "Women 20-50 with color-treated or damaged hair, salon quality seekers",
        "pricePoint": "$18.99",
        "usp": "Parisian salon science in every jar",
    },
    {
        "id": "p6",
        "name": "TinyTots Organic Baby Wipes",
        "category": "Baby Care",
        "brand": "TinyTots",
        "features": ["99% water", "Organic cotton", "Hypoallergenic", "Fragrance-free", "Compostable"],
        "benefits": ["Gentle on sensitive skin", "No irritation or rashes", "Eco-friendly disposal", "Pediatrician recommended"],
        "usage": "Gently wipe and dispose. Safe for face, hands, and diaper area.",
        "targetAudience": "New parents, eco-conscious families, parents of babies with sensitive skin",
        "pricePoint": "$8.99/80ct",
        "usp": "Pure enough for the most precious skin on earth",
    },
]


BRAND_STYLE_GUIDES = {
    "PureGlow Naturals": {
        "tone": "Sophisticated, science-backed yet approachable, empowering",
        "voiceTraits": ["Clean", "Confident", "Educational", "Aspirational"],
        "doWords": ["radiance", "transform", "clinical-grade", "pure", "glow", "reveal"],
        "dontWords": ["cheap", "miracle", "cure", "guaranteed results", "anti-aging"],
        "tagline": "Science Meets Nature",
    },
    "FreshBite Co.": {
        "tone": "Energetic, fun, motivational, straightforward",
        "voiceTraits": ["Bold", "Active", "Real", "Community-driven"],
        "doWords": ["fuel", "crush it", "real food", "power", "clean", "strong"],
        "dontWords": ["diet", "low-cal", "skinny", "cheat meal", "guilt"],
        "tagline": "Fuel Your Fire",
    },
    "EcoClean Home": {
        "tone": "Warm, trustworthy, eco-conscious, family-friendly",
        "voiceTraits": ["Caring", "Transparent", "Sustainable", "Reliable"],
        "doWords": ["protect", "pure", "planet-friendly", "safe", "naturally", "home"],
        "dontWords": ["toxic", "chemical-free (misleading)", "100% safe", "kills all"],
        "tagline": "Clean Home, Clean Planet",
    },
    "ZenBrew": {
        "tone": "Mindful, premium, intellectual, calm confidence",
        "voiceTraits": ["Wise", "Serene", "Elevated", "Intentional"],
        "doWords": ["ritual", "clarity", "flow state", "craft", "mindful", "elevate"],
        "dontWords": ["wired", "buzzed", "caffeine hit", "basic", "average"],
        "tagline": "Clarity in Every Cup",
    },
    "LuxeLocks Paris": {
        "tone": "Luxurious, French-inspired elegance, expert authority",
        "voiceTraits": ["Glamorous", "Expert", "Indulgent", "Confident"],
        "doWords": ["luxe", "transform", "salon-grade", "nourish", "silk", "radiant"],
        "dontWords": ["cheap", "basic", "quick fix", "drugstore", "no-fuss"],
        "tagline": "L'Art du Cheveu",
    },
    "TinyTots": {
        "tone": "Tender, reassuring, pure, parent-to-parent",
        "voiceTraits": ["Gentle", "Trustworthy", "Pure", "Loving"],
        "doWords": ["gentle", "pure", "precious", "nurture", "safe", "soft"],
        "dontWords": ["tough", "strong", "powerful", "aggressive", "extreme"],
        "tagline": "Pure Love, Pure Care",
    },
}


def build_rules() -> dict[str, list[dict[str, Any]]]:
    raw_rules = {
        "Skincare": [
            ("No disease treatment claims", "critical", r"\b(cure|treat|heal|remedy)\b"),
            ("No guaranteed results claims", "critical", r"\b(guaranteed|100%|always works|permanent)\b"),
            ("Must include 'results may vary' for efficacy claims", "warning", r"\b(clinically proven|dermatologist tested)\b"),
            ("No comparative superiority without evidence", "warning", r"\b(best|#1|number one|superior to)\b"),
            ("FDA disclaimer required for structure/function claims", "info", r"\b(supports|promotes|helps maintain)\b"),
        ],
        "Food & Beverage": [
            ("No disease prevention claims", "critical", r"\b(prevents?|cures?|treats?|fights? disease)\b"),
            ("No misleading health claims", "critical", r"\b(superfood|miracle|magic)\b"),
            ("Allergen info should be accessible", "warning", r"\b(contains|may contain|allergen)\b"),
            ("Nutritional claims must be substantiated", "warning", r"\b(high protein|low sugar|zero calorie|no sugar)\b"),
            ("Organic claims require certification", "info", r"\b(organic|certified organic)\b"),
        ],
        "Household": [
            ("No absolute safety claims", "critical", r"\b(100% safe|completely safe|totally harmless)\b"),
            ("No 'chemical-free' claims (misleading)", "warning", r"\b(chemical[ -]free|no chemicals)\b"),
            ("EPA certification must be accurate", "critical", r"\b(EPA certified|EPA approved)\b"),
            ("Efficacy claims need qualification", "warning", r"\b(kills 99|eliminates all|destroys)\b"),
        ],
        "Haircare": [
            ("No permanent change claims without evidence", "critical", r"\b(permanent|forever|irreversible)\b"),
            ("No medical claims", "critical", r"\b(treats? hair loss|cures? dandruff|medical)\b"),
            ("Time-based claims need substantiation", "warning", r"\b(instant|immediate|overnight)\b"),
        ],
        "Baby Care": [
            ("No absolute safety claims", "critical", r"\b(100% safe|completely safe|zero risk)\b"),
            ("Medical endorsement must be verified", "critical", r"\b(doctor recommended|clinically proven|medically approved)\b"),
            ("Age appropriateness must be specified", "warning", r"\b(all ages|any age|newborn)\b"),
            ("Ingredient transparency required", "info", r"\b(natural|organic|pure)\b"),
        ],
    }
    out: dict[str, list[dict[str, Any]]] = {}
    for category, rows in raw_rules.items():
        out[category] = [
            {"rule": rule, "severity": severity, "regex": re.compile(pattern, re.IGNORECASE)}
            for (rule, severity, pattern) in rows
        ]
    return out


COMPLIANCE_RULES = build_rules()

CHANNELS = [
    {"id": "instagram", "name": "Instagram Post", "maxLength": 2200, "format": "Visual-first caption with hashtags"},
    {"id": "facebook", "name": "Facebook Ad", "maxLength": 1000, "format": "Engaging ad copy with CTA"},
    {"id": "email", "name": "Email Campaign", "maxLength": 3000, "format": "Subject line + body with sections"},
    {"id": "twitter", "name": "X/Twitter Post", "maxLength": 280, "format": "Concise, punchy with hashtags"},
    {"id": "product_page", "name": "Product Page", "maxLength": 5000, "format": "SEO-optimized product description"},
    {"id": "print_ad", "name": "Print Ad", "maxLength": 500, "format": "Headline + body + tagline"},
    {"id": "tvc_script", "name": "TV/Video Script", "maxLength": 3000, "format": "30-second script with visuals"},
    {"id": "sms", "name": "SMS/WhatsApp", "maxLength": 160, "format": "Short promotional message"},
]

CAMPAIGN_TONES = ["Professional", "Playful", "Urgent", "Inspirational", "Educational", "Luxurious", "Eco-Conscious", "Bold & Edgy"]


def check_compliance(text: str, category: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for rule in COMPLIANCE_RULES.get(category, []):
        matches = rule["regex"].findall(text)
        if matches:
            unique_matches = sorted(set(matches if isinstance(matches, list) else [matches]))
            issues.append({"rule": rule["rule"], "severity": rule["severity"], "matches": unique_matches})
    return issues


def get_compliance_score(issues: list[dict[str, Any]]) -> str:
    severities = {i["severity"] for i in issues}
    if "critical" in severities:
        return "Needs Review"
    if "warning" in severities:
        return "Caution"
    if "info" in severities:
        return "Minor Notes"
    return "Compliant"


def strip_json_fence(text: str) -> str:
    return re.sub(r"```json|```", "", text).strip()


def openai_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it in .env or your shell environment.")

    req = urllib.request.Request(
        url="https://api.openai.com/v1/chat/completions",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
            message = parsed.get("error", {}).get("message", body)
        except json.JSONDecodeError:
            message = body
        raise RuntimeError(f"OpenAI request failed ({e.code}): {message}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error while calling OpenAI: {e.reason}") from e


def generate_for_channel(
    product: dict[str, Any],
    channel: dict[str, Any],
    tone: str,
    season: str,
    num_variants: int,
    custom_prompt: str,
    model: str,
) -> list[dict[str, Any]]:
    brand = BRAND_STYLE_GUIDES[product["brand"]]
    category_rules = COMPLIANCE_RULES.get(product["category"], [])
    rules_text = "\n".join([f"- {r['severity'].upper()}: {r['rule']}" for r in category_rules])

    system_prompt = f"""You are an expert CPG marketing copywriter. You produce high-converting, brand-compliant marketing content.

BRAND VOICE GUIDE for "{product['brand']}":
- Tone: {brand['tone']}
- Voice Traits: {", ".join(brand['voiceTraits'])}
- Preferred Words: {", ".join(brand['doWords'])}
- Avoid These Words: {", ".join(brand['dontWords'])}
- Brand Tagline: {brand['tagline']}

COMPLIANCE RULES for {product['category']}:
{rules_text}

You MUST respond ONLY with valid JSON. No markdown and no code fences.
Schema:
{{
  "variants": [
    {{
      "label": "Variant A label",
      "headline": "attention-grabbing headline",
      "body": "the main marketing copy",
      "cta": "call to action",
      "hashtags": ["tag1", "tag2"],
      "complianceNotes": "any compliance considerations"
    }}
  ]
}}"""

    user_prompt = f"""Create {num_variants} distinct marketing content variants for:

PRODUCT: {product['name']}
CATEGORY: {product['category']}
FEATURES: {", ".join(product['features'])}
BENEFITS: {", ".join(product['benefits'])}
USAGE: {product['usage']}
TARGET AUDIENCE: {product['targetAudience']}
PRICE: {product['pricePoint']}
USP: {product['usp']}

CHANNEL: {channel['name']}
FORMAT: {channel['format']}
MAX LENGTH: {channel['maxLength']} characters
CAMPAIGN TONE: {tone}
SEASON/OCCASION: {season}
{f"ADDITIONAL DIRECTION: {custom_prompt}" if custom_prompt else ""}

Each variant should use a different creative angle and be useful for A/B testing."""

    payload = {
        "model": model,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    data = openai_chat_completion(payload)
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join([item.get("text", "") for item in content if isinstance(item, dict)])
    parsed = json.loads(strip_json_fence(content))
    variants = parsed.get("variants", [])
    if not isinstance(variants, list):
        raise RuntimeError("Model response did not include a valid 'variants' array.")
    return variants


def build_txt_export(product: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = [
        "CPG MARKETING CONTENT EXPORT",
        f"Generated At: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Product: {product['name']} ({product['brand']})",
        f"Category: {product['category']}",
        "",
    ]
    for row in results:
        lines.append(f"Channel: {row['channel_name']}")
        lines.append("-" * 60)
        for i, v in enumerate(row["variants"], start=1):
            lines.append(f"Variant {i}: {v.get('label', '')}")
            lines.append(f"Headline: {v.get('headline', '')}")
            lines.append(f"Body: {v.get('body', '')}")
            lines.append(f"CTA: {v.get('cta', '')}")
            lines.append(f"Hashtags: {', '.join(v.get('hashtags', []))}")
            lines.append(f"Compliance Notes: {v.get('complianceNotes', '')}")
            lines.append("")
        lines.append("")
    return "\n".join(lines)


def build_csv_export(results: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["channel", "label", "headline", "body", "cta", "hashtags", "complianceNotes", "complianceScore"],
    )
    writer.writeheader()
    for row in results:
        for v in row["variants"]:
            writer.writerow(
                {
                    "channel": row["channel_name"],
                    "label": v.get("label", ""),
                    "headline": v.get("headline", ""),
                    "body": v.get("body", ""),
                    "cta": v.get("cta", ""),
                    "hashtags": ", ".join(v.get("hashtags", [])),
                    "complianceNotes": v.get("complianceNotes", ""),
                    "complianceScore": v.get("_compliance_score", ""),
                }
            )
    return buf.getvalue()


def main() -> None:
    st.set_page_config(page_title="CPG Content Generator", layout="wide")
    st.title("CPG Content Generator")
    st.caption("Single-file Python app with OpenAI generation and compliance checks")

    if "results" not in st.session_state:
        st.session_state.results = []

    product_options = {f"{p['name']} ({p['brand']})": p for p in PRODUCT_DATABASE}
    channel_options = {c["name"]: c for c in CHANNELS}

    with st.sidebar:
        st.header("Campaign Setup")
        selected_product_label = st.selectbox("Product", list(product_options.keys()))
        selected_channel_labels = st.multiselect(
            "Channels",
            list(channel_options.keys()),
            default=["Instagram Post"],
        )
        campaign_tone = st.selectbox("Campaign Tone", CAMPAIGN_TONES, index=0)
        target_season = st.text_input("Season / Occasion", value="General")
        num_variants = st.slider("Variants per channel", min_value=1, max_value=5, value=2)
        model = st.text_input("OpenAI model", value="gpt-4o-mini")
        custom_prompt = st.text_area("Additional direction", value="")
        generate_clicked = st.button("Generate Content", type="primary")

    selected_product = product_options[selected_product_label]

    if generate_clicked:
        if not selected_channel_labels:
            st.error("Select at least one channel.")
        else:
            results: list[dict[str, Any]] = []
            progress = st.progress(0)
            status = st.empty()
            selected_channels = [channel_options[name] for name in selected_channel_labels]
            try:
                for i, channel in enumerate(selected_channels, start=1):
                    status.write(f"Generating {channel['name']} ({i}/{len(selected_channels)}) ...")
                    variants = generate_for_channel(
                        product=selected_product,
                        channel=channel,
                        tone=campaign_tone,
                        season=target_season,
                        num_variants=num_variants,
                        custom_prompt=custom_prompt,
                        model=model,
                    )
                    enriched: list[dict[str, Any]] = []
                    for v in variants:
                        text = f"{v.get('headline', '')} {v.get('body', '')} {v.get('cta', '')}"
                        issues = check_compliance(text, selected_product["category"])
                        v["_compliance_issues"] = issues
                        v["_compliance_score"] = get_compliance_score(issues)
                        enriched.append(v)
                    results.append({"channel_id": channel["id"], "channel_name": channel["name"], "variants": enriched})
                    progress.progress(i / len(selected_channels))
                st.session_state.results = results
                status.success("Generation complete.")
            except Exception as err:
                st.error(str(err))

    if st.session_state.results:
        st.subheader("Generated Content")
        results = st.session_state.results
        for row in results:
            st.markdown(f"### {row['channel_name']}")
            for idx, variant in enumerate(row["variants"], start=1):
                with st.expander(f"Variant {idx}: {variant.get('label', 'Untitled')}"):
                    st.write(f"**Headline:** {variant.get('headline', '')}")
                    st.write(f"**Body:** {variant.get('body', '')}")
                    st.write(f"**CTA:** {variant.get('cta', '')}")
                    st.write(f"**Hashtags:** {', '.join(variant.get('hashtags', []))}")
                    st.write(f"**Compliance Notes:** {variant.get('complianceNotes', '')}")
                    st.write(f"**Compliance Score:** {variant.get('_compliance_score', 'Compliant')}")
                    issues = variant.get("_compliance_issues", [])
                    if issues:
                        for issue in issues:
                            st.write(
                                f"- [{issue['severity'].upper()}] {issue['rule']} | matches: {', '.join(issue['matches'])}"
                            )
                    else:
                        st.write("- No compliance issues detected by regex checks.")

        txt_data = build_txt_export(selected_product, results)
        json_data = json.dumps(
            {
                "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
                "product": selected_product,
                "results": results,
            },
            indent=2,
        )
        csv_data = build_csv_export(results)

        st.subheader("Export")
        st.download_button("Download TXT", data=txt_data, file_name="cpg_content_export.txt", mime="text/plain")
        st.download_button("Download JSON", data=json_data, file_name="cpg_content_export.json", mime="application/json")
        st.download_button("Download CSV", data=csv_data, file_name="cpg_content_export.csv", mime="text/csv")

    with st.expander("Product Library"):
        for p in PRODUCT_DATABASE:
            st.markdown(f"**{p['name']}** ({p['brand']})")
            st.write(f"Category: {p['category']}")
            st.write(f"USP: {p['usp']}")
            st.write(f"Price: {p['pricePoint']}")
            st.write("---")


if __name__ == "__main__":
    main()
