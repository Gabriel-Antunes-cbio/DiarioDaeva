from datetime import datetime, timezone

from daeva.profiles import (
    detail_urls, parse_a2i_skills, parse_a2i_title_counts, parse_link, parse_shugo, parse_shugo_gear,
)
from daeva.store import Store
from daeva.titles import Achievement, TitleInfo, load_achievements, parse_title_page, score

# Páginas de exemplo montadas a partir do texto real dos sites (19/10/2026)
TITLE_PAGE = """<html><body><h1>Executioner of Immortal Gartua <small>Challenge title</small></h1>
<dl><dt>Grade</dt><dd>Epic</dd><dt>Faction</dt><dd>Asmodian</dd><dt>Role</dt><dd>Offensive</dd>
<dt>Category</dt><dd>Challenge</dd></dl>
<h2>When equipped</h2><dl><dt>Block Penetration</dt><dd>+58</dd><dt>Penetration</dt><dd>+290</dd></dl>
<h2>Collection bonus (owned)</h2><dl><dt>Attack Bonus</dt><dd>+2</dd></dl>
<h2>How to get</h2><p>You earn it by completing the achievement “[Immortal Isle] Immortal Gartua”.</p>
</body></html>"""

SHUGO_GEAR = """<h2>Equipment</h2><table><thead><tr><th>Slot</th><th>Item</th><th>Grade</th></tr></thead><tbody>
<tr><td>Main Hand</td><td><a href="https://shugo.gg/items/110130050">Aulamus Greatsword +13</a></td><td>Unique</td></tr>
<tr><td>Off-hand</td><td><a href="https://shugo.gg/items/115030052">Vakron Guard +10</a></td><td>Unique</td></tr>
<tr><td>Legs</td><td><a href="/items/210230100">Gartua Greaves +10</a></td><td>Unique</td></tr>
</tbody></table><h2>Other members of bibas</h2>"""

A2I_SKILLS = """<h2>Active skills</h2>
<div><span>18</span><b>Overhead Slam</b><small>Learned at Lv 4</small></div>
<div><span>16</span><b>Rending Blow</b><small>Learned at Lv 1</small></div>
<h2>Passive skills</h2><div><span>10</span><b>Iron Skin</b><small>Learned at Lv 12</small></div>
<h2>Stigma skills</h2><p>13 skills, 4 equipped, 7 not learned</p>
<div><span>5</span><b>Wrathful Strike</b><small>Learned at Lv 20</small></div>"""

A2I_TITLES = """<div>Titles collected</div><div>Utility <b>66</b> / 99</div><div>Attack <b>68</b> / 103</div>
<div>Defense <b>66</b> / 95</div><div>Equipped</div><div>Through Hell and Back</div>"""


def test_title_page():
    t = parse_title_page(TITLE_PAGE)
    assert (t.grade, t.faction, t.role) == ("Epic", "Asmodian", "Offensive")
    assert t.equip == [("Block Penetration", "+58"), ("Penetration", "+290")]
    assert t.collection == [("Attack Bonus", "+2")]
    assert not t.fits("Elyos") and t.fits("Asmodian")


def test_shugo_gear_table():
    g = parse_shugo_gear(SHUGO_GEAR)
    assert g[0] == {"slot": "Main Hand", "item": "Aulamus Greatsword", "enchant": 13, "grade": "Unique"}
    assert len(g) == 3 and g[2]["item"] == "Gartua Greaves"


def test_a2i_skills_and_titles():
    s = parse_a2i_skills(A2I_SKILLS)
    assert s["active"] == [["Overhead Slam", 18], ["Rending Blow", 16]]
    assert s["passive"] == [["Iron Skin", 10]]
    assert s["stigma"] == [["Wrathful Strike", 5]]
    t = parse_a2i_title_counts(A2I_TITLES)
    assert t["total"] == [200, 297] and t["Attack"] == [68, 103]


def test_faction_from_shugo_and_detail_urls():
    page = ('<meta name="description" content="Kumaglad: AION 2 Level 45 Elyos Gladiator (1,723 GS) on Siel.">'
            '<p>Gear score 1,723 · Combat power 106,302</p>')
    assert parse_shugo(page).faction == "Elyos"
    u = detail_urls(parse_link("https://aion2index.com/c/la/siel/Kumaglad"))
    assert u["gear"] == "https://shugo.gg/character/global/la-siel/Kumaglad"
    assert u["skills"] == "https://aion2index.com/c/la/siel/Kumaglad/skills"


def test_achievement_data_and_goals():
    items, groups = load_achievements()
    assert len(items) == 192 and len(groups) == 22
    by_title = {a.title: a for a in items}
    assert by_title["Executioner of Eternal Gartua"].target_count is None  # derrotar 1 vez
    assert by_title["Ecosystem Eradicator"].target_count == 100
    assert by_title["Extractor"].target_count == 5           # "Extract +10 or higher gear 5 times"
    assert by_title["Golden Glow"].target_count is None      # "Enhance Unique Gear to +5"
    assert by_title["One Step at a Time"].target_count == 50  # Item Level 50
    assert by_title["Island of Death, Poeta"].target_count is None


def test_score_prefers_collection_bonus():
    atk = TitleInfo("Epic", "Elyos", "Offensive", [("Penetration", "+290")], [("Attack Bonus", "+2")])
    pvp = TitleInfo("Unique", "Both factions", "Offensive", [("PvP Damage Boost", "+4%")], [("PvP Accuracy", "+20")])
    deff = TitleInfo("Unique", "Elyos", "Defensive", [("Damage Tolerance", "+3%")], [("MP", "+20")])
    assert score(atk, "pve") == (1, 1)
    assert score(pvp, "pve") == (0, 0)
    assert score(pvp, "pvp") == (1, 1)
    assert score(deff, "def") == (0, 1)


def test_store_owned_and_target(tmp_path):
    s = Store(tmp_path / "d.json")
    s.set_owned("c1", "executioner-of-eternal-gartua", True)
    s.set_target("c1", "hunting/ecosystem-eradicator/45")
    s.set_progress("c1", 37)
    s.cache_title("x", {"grade": "Epic"}, datetime(2026, 10, 19, tzinfo=timezone.utc))
    s.save_title_cache()
    s2 = Store(tmp_path / "d.json")
    assert "executioner-of-eternal-gartua" in s2.owned("c1")
    assert s2.target("c1")["progress"] == 37
    assert s2.title_cache["x"]["grade"] == "Epic"
