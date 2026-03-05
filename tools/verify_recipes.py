#!/usr/bin/env python3
"""
Hanzi decomposition tool using hanzicraft.com.

Fetches the structural decomposition (Level 1 = "components1") for any Chinese
character, then uses that data to build and verify radical forge recipes.

Usage:
    python tools/verify_recipes.py              # Verify existing recipes + generate corrected Rust code
    python tools/verify_recipes.py --lookup 想   # Look up decomposition for a single character
    python tools/verify_recipes.py --generate    # Generate new recipe set from scratch
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from typing import Optional


def fetch_page_data(hanzi: str) -> Optional[dict]:
    """Fetch the embedded JSON data from hanzicraft.com for a character."""
    url = f"https://hanzicraft.com/character/{urllib.parse.quote(hanzi)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠ Failed to fetch {hanzi}: {e}", file=sys.stderr)
        return None

    match = re.search(r"var data = ({.*?});\s*</script>", html, re.DOTALL)
    if not match:
        # Try without </script> anchor
        match = re.search(r"var data = ({.*?});", html, re.DOTALL)
    if not match:
        print(f"  ⚠ No embedded JSON found for {hanzi}", file=sys.stderr)
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error for {hanzi}: {e}", file=sys.stderr)
        return None


def get_components(data: dict, hanzi: str) -> list[str]:
    """Extract Level 1 components from page data."""
    return (
        data.get("decompose", {})
        .get(hanzi, {})
        .get("components1", [])
    )


def deep_decompose(hanzi: str, max_depth: int = 4) -> list[str]:
    """Recursively decompose a character down to game radicals.
    
    Returns the list of leaf radicals (all in GAME_RADICALS) if fully
    decomposable, otherwise returns whatever we got (may contain
    non-game components).
    """
    if hanzi in GAME_RADICALS:
        return [hanzi]

    if max_depth <= 0:
        return [hanzi]

    data = cached_fetch(hanzi)
    if not data:
        return [hanzi]

    components = get_components(data, hanzi)
    if not components or components == [hanzi]:
        return [hanzi]

    result = []
    for comp in components:
        if comp in GAME_RADICALS:
            result.append(comp)
        else:
            sub = deep_decompose(comp, max_depth - 1)
            result.extend(sub)
    return result


def get_pinyin_meaning(data: dict, hanzi: str) -> tuple[str, str]:
    """Extract pinyin and short meaning from page data."""
    entries = data.get("dictionary", {}).get(hanzi, [])
    if not entries:
        return ("", "")
    entry = entries[0]
    pinyin = entry.get("pinyin", "")
    definition = entry.get("definition", "")
    short_def = definition.split("/")[0] if definition else ""
    return (pinyin, short_def)


# Cache to avoid re-fetching
_cache: dict[str, dict] = {}


def cached_fetch(hanzi: str) -> Optional[dict]:
    """Fetch with caching and rate limiting."""
    if hanzi in _cache:
        return _cache[hanzi]
    data = fetch_page_data(hanzi)
    if data:
        _cache[hanzi] = data
    time.sleep(0.3)  # Rate limit
    return data


# ─── Game Data ───────────────────────────────────────────────

GAME_RADICALS = [
    "火", "水", "木", "金", "土", "日", "月", "心", "口", "手",
    "目", "人", "大", "小", "山", "石", "雨", "风", "刀", "力",
    "田", "女", "子", "王", "竹", "米", "虫", "贝", "马", "鸟",
]

SPELL_EFFECTS = {
    "fire":   {"火", "日", "雨"},
    "heal":   {"水", "心", "木", "月", "米"},
    "shield": {"金", "石", "土", "山", "王"},
    "strike": {"刀", "力", "手", "大", "风"},
}


def classify_effect(components: list[str]) -> str:
    """Classify spell effect based on radical components."""
    scores = {k: 0 for k in SPELL_EFFECTS}
    for comp in components:
        for effect, radicals in SPELL_EFFECTS.items():
            if comp in radicals:
                scores[effect] += 1
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "strike"


def effect_to_rust(effect: str, power: int) -> str:
    """Convert effect + power to Rust SpellEffect enum variant."""
    return {
        "fire": f"SpellEffect::FireAoe({power})",
        "heal": f"SpellEffect::Heal({power})",
        "shield": "SpellEffect::Shield",
        "strike": f"SpellEffect::StrongHit({power})",
    }[effect]


# Candidate characters to check — common characters likely composed of our radicals
CANDIDATE_CHARACTERS = [
    # 2-component candidates
    "明", "好", "岩", "林", "炎", "泥", "沐", "仁", "灯", "打",
    "吗", "呗", "叶", "吹", "沁", "李", "杏", "村", "枝", "松",
    "柳", "梅", "桃", "坚", "地", "场", "块", "城", "塔", "尘",
    "砂", "码", "砖", "玉", "玩", "珠", "环", "班", "现", "理",
    "球", "琴", "男", "畔", "界", "略", "烧", "烤", "灾", "烛",
    "照", "煮", "蒸", "焦", "然", "煤", "刃", "切", "刊", "判",
    "别", "刮", "到", "功", "加", "助", "动", "劲", "勇",
    "虹", "蛇", "蜂", "蚁", "蝶", "蜘", "蛛",
    "驰", "驻", "骑", "鸡", "鸭", "鹅", "鸣", "鸦",
    "妈", "奶", "姐", "妹", "嫁", "娘", "粉", "粒", "粮", "精",
    "笔", "笑", "笛", "筷", "箱", "算",
    "汁", "江", "河", "池", "湿", "泪", "汗", "沙", "淡",
    "妙", "她", "妇", "如", "妖",
    "忘", "忙", "忍",
    "岛", "峰",
    # 3-component candidates
    "想", "雷", "淋", "洗", "海", "湖", "溪", "涌",
    "看", "着", "盯", "睡", "睛", "瞎",
    "忍", "思", "念", "怒", "恨", "愁",
]


def lookup_single(hanzi: str):
    """Look up and display decomposition for a single character."""
    data = fetch_page_data(hanzi)
    if not data:
        print(f"Could not fetch data for {hanzi}")
        return

    components = get_components(data, hanzi)
    pinyin, meaning = get_pinyin_meaning(data, hanzi)
    deep = deep_decompose(hanzi)

    print(f"\n{'='*50}")
    print(f"Character:    {hanzi}")
    print(f"Pinyin:       {pinyin}")
    print(f"Meaning:      {meaning}")
    print(f"Level 1:      {components}")
    print(f"Deep decomp:  {deep}")

    in_game = [c for c in deep if c in GAME_RADICALS]
    not_in = [c for c in deep if c not in GAME_RADICALS]
    print(f"In game:      {in_game}")
    if not_in:
        print(f"NOT in game:  {not_in}")

    usable = len(in_game) >= 2 and len(not_in) == 0
    print(f"Recipe?       {'✅ YES' if usable else '❌ NO'}")

    if usable:
        effect = classify_effect(deep)
        power = len(deep) + 1
        print(f"Effect:       {effect} (power {power})")
        print(f"Rust:         {effect_to_rust(effect, power)}")


def verify_existing():
    """Verify current radical.rs recipes against hanzicraft."""
    # Recipes currently in src/radical.rs
    current = [
        (["火", "火"], "炎", "yán", "flame/blaze"),
        (["火", "山"], "灾", "zāi", "disaster"),
        (["火", "木"], "烧", "shāo", "to burn"),
        (["心", "人"], "仁", "rén", "benevolence"),
        (["水", "心"], "沁", "qìn", "to seep/refresh"),
        (["日", "月"], "明", "míng", "bright/clear"),
        (["木", "子"], "李", "lǐ", "plum tree"),
        (["金", "土"], "坚", "jiān", "solid/firm"),
        (["石", "山"], "岩", "yán", "rock/cliff"),
        (["王", "金"], "玉", "yù", "jade"),
        (["刀", "力"], "刃", "rèn", "blade edge"),
        (["手", "力"], "拳", "quán", "fist"),
        (["大", "力"], "奋", "fèn", "exert effort"),
        (["金", "刀"], "剑", "jiàn", "sword"),
        (["风", "刀"], "刮", "guā", "to scrape/gust"),
        (["水", "木"], "沐", "mù", "to bathe"),
        (["雨", "田"], "雷", "léi", "thunder"),
        (["水", "土"], "泥", "ní", "mud"),
        (["女", "子"], "好", "hǎo", "good"),
        (["口", "大"], "呗", "bài", "to chant"),
        (["竹", "马"], "笃", "dǔ", "sincere/earnest"),
        (["米", "口"], "粮", "liáng", "grain/provisions"),
        (["目", "心"], "想", "xiǎng", "to think/miss"),
        (["虫", "火"], "烛", "zhú", "candle"),
        (["鸟", "山"], "岛", "dǎo", "island"),
    ]

    print("Verifying existing recipes against hanzicraft.com...\n")
    print(f"{'Char':<5} {'Recipe':<16} {'Actual':<24} {'OK?'}")
    print("-" * 55)

    correct = []
    incorrect = []

    for inputs, output, pinyin, meaning in current:
        deep = deep_decompose(output)

        inputs_s = sorted(inputs)
        comps_s = sorted(deep)
        match = (inputs_s == comps_s) and all(c in GAME_RADICALS for c in deep)

        status = "✅" if match else "❌"
        print(f"{output:<5} {'+'.join(inputs):<16} {','.join(deep) if deep else '???':<24} {status}")

        if match:
            correct.append((inputs, output, pinyin, meaning))
        else:
            incorrect.append((inputs, output, pinyin, meaning, deep))

    print(f"\n✅ {len(correct)}/{len(current)} correct")
    if incorrect:
        print(f"❌ {len(incorrect)}/{len(current)} incorrect:")
        for inputs, output, pinyin, meaning, actual in incorrect:
            print(f"   {output}: expected {inputs}, got {actual}")

    return correct, incorrect


def generate_recipes() -> list[dict]:
    """Generate verified recipes from candidate characters."""
    print("\nScanning candidate characters...\n")

    recipes = []
    seen_combos = set()

    for hanzi in CANDIDATE_CHARACTERS:
        deep = deep_decompose(hanzi)

        if not deep or len(deep) < 2 or len(deep) > 3:
            continue

        if not all(c in GAME_RADICALS for c in deep):
            continue

        combo_key = tuple(sorted(deep))
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)

        data = cached_fetch(hanzi)
        if not data:
            continue
        pinyin, meaning = get_pinyin_meaning(data, hanzi)
        if not pinyin or not meaning:
            continue

        effect = classify_effect(deep)
        power = len(deep) + 1

        recipes.append({
            "inputs": deep,
            "output": hanzi,
            "pinyin": pinyin,
            "meaning": meaning,
            "effect": effect,
            "power": power,
        })
        print(f"  ✅ {hanzi} ({pinyin}) = {' + '.join(deep)} → {effect}")

    print(f"\nFound {len(recipes)} valid recipes.")
    return recipes


def recipes_to_rust(recipes: list[dict]) -> str:
    """Convert recipe list to Rust const code."""
    lines = ["pub const RECIPES: &[Recipe] = &["]
    for r in recipes:
        inputs = ", ".join(f'"{i}"' for i in r["inputs"])
        effect = effect_to_rust(r["effect"], r["power"])
        meaning = r["meaning"].replace('"', '\\"')
        lines.append(
            f'    Recipe {{ inputs: &[{inputs}], output_hanzi: "{r["output"]}", '
            f'output_pinyin: "{r["pinyin"]}", output_meaning: "{meaning}", '
            f'effect: {effect} }},'
        )
    lines.append("];")
    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--lookup" and len(sys.argv) >= 3:
            lookup_single(sys.argv[2])
            return
        if sys.argv[1] == "--generate":
            recipes = generate_recipes()
            if recipes:
                code = recipes_to_rust(recipes)
                print("\n" + "=" * 60)
                print(code)
                with open("tools/generated_recipes.rs", "w", encoding="utf-8") as f:
                    f.write("// Auto-generated verified recipes from hanzicraft.com\n")
                    f.write("// Run: python tools/verify_recipes.py --generate\n\n")
                    f.write(code)
                print(f"\nSaved to tools/generated_recipes.rs")
            return

    # Default: verify then generate corrected set
    correct, incorrect = verify_existing()

    print("\n" + "=" * 60)
    print("Generating full verified recipe set...")
    print("=" * 60)

    new_recipes = generate_recipes()

    # Merge: correct existing + new verified (no duplicates)
    all_recipes = []
    seen = set()

    for inputs, output, pinyin, meaning in correct:
        effect = classify_effect(inputs)
        power = len(inputs) + 1
        all_recipes.append({
            "inputs": inputs, "output": output, "pinyin": pinyin,
            "meaning": meaning, "effect": effect, "power": power,
        })
        seen.add(output)

    for r in new_recipes:
        if r["output"] not in seen:
            all_recipes.append(r)
            seen.add(r["output"])

    code = recipes_to_rust(all_recipes)
    print("\n" + "=" * 60)
    print("Final Rust RECIPES code:")
    print("=" * 60)
    print(code)

    with open("tools/generated_recipes.rs", "w", encoding="utf-8") as f:
        f.write("// Auto-generated verified recipes from hanzicraft.com\n")
        f.write("// Run: python tools/verify_recipes.py --generate\n\n")
        f.write(code)
    print(f"\nSaved to tools/generated_recipes.rs")


if __name__ == "__main__":
    main()
