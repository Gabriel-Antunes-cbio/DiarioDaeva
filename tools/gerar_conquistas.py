"""Gera daeva/data/conquistas_titulos.json: as conquistas do AION 2 que dão título.

Fonte: MetaBot.GG (https://metabot.gg/en/aion-2/achievements), que permite reaproveitar os dados
desde que cada um tenha um link de crédito para a página de origem (metabot.gg/en/ai).
O app mostra esse link em cada título. Transcrito em 19/10/2026.

Linhas: grupo | conquista | meta (do 1º nível, quando a conquista tem vários) | título | slug do título
"""
import json
from pathlib import Path

GROUPS = {
    "bosses": "Bosses de campo", "exploration": "Exploração", "shugo-festival": "Festival Shugo",
    "hunting": "Caça", "combat": "Combate", "social": "Legião, amigos e pets", "quests": "Missões",
    "enhancement": "Aprimoramento", "crafting": "Criação", "gear-collection": "Coleção de equipamentos",
    "kibelisks": "Kibelisks", "sealed-dungeons": "Dungeons seladas", "strongholds": "Fortalezas",
    "milestones": "Marcos de nível", "gathering": "Coleta", "consumables": "Consumíveis e armazém",
    "fire-temple": "Templo do Fogo", "draupnir-cave": "Caverna de Draupnir", "krao-cave": "Caverna de Krao",
    "urugugu": "Cânion Urugugu", "vakron": "Ilha Celeste de Vakron", "horn-den": "Covil do Chifre Feroz",
}

ROWS = """
bosses|Kernon of the West|Defeat Unique Field Monster Kernon of the West|Executioner of Kernon of the West|executioner-of-kernon-of-the-west
bosses|Neikel of the East|Defeat Unique Field Monster Neikel of the East|Executioner of Neikel of the East|executioner-of-neikel-of-the-east
bosses|Rotten Kutar|Defeat Unique Field Monster Rotten Kutar|Executioner of Rotten Kutar|executioner-of-rotten-kutar
bosses|Blooming Korin|Defeat Unique Field Monster Blooming Korin|Executioner of Blooming Korin|executioner-of-blooming-korin
bosses|Bodyguard Teegant|Defeat Unique Field Monster Bodyguard Teegant|Executioner of Bodyguard Teegant|executioner-of-bodyguard-teegant
bosses|Kusan the Mad Gladiator|Defeat Unique Field Monster Kusan the Mad Gladiator|Executioner of Kusan the Mad Gladiator|executioner-of-kusan-the-mad-gladiator
bosses|Ritualist Garshim|Defeat Unique Field Monster Ritualist Garshim|Executioner of Ritualist Garshim|executioner-of-ritualist-garshim
bosses|Bloodfang Pnyn|Defeat Unique Field Monster Bloodfang Pnyn|Executioner of Bloodfang Pnyn|executioner-of-bloodfang-pnyn
bosses|Furious Saursus|Defeat Unique Field Monster Furious Saursus|Executioner of Furious Saursus|executioner-of-furious-saursus
bosses|Scholar Aulla|Defeat Unique Field Monster Scholar Aulla|Executioner of Scholar Aulla|executioner-of-scholar-aulla
bosses|Chaser Taulo|Defeat Unique Field Monster Chaser Taulo|Executioner of Chaser Taulo|executioner-of-chaser-taulo
bosses|Forest Warrior Aullamu|Defeat Unique Field Monster Forest Warrior Aullamu|Executioner of Forest Warrior Aullamu|executioner-of-forest-warrior-aullamu
bosses|Heretic Layla|Defeat Unique Field Monster Heretic Layla|Executioner of Heretic Layla|executioner-of-heretic-layla
bosses|Black Tentacle Lawa|Defeat Unique Field Monster Black Tentacle Lawa|Executioner of Black Tentacle Lawa|executioner-of-black-tentacle-lawa
bosses|Centurion Demiros|Defeat Unique Field Monster Centurion Demiros|Executioner of Centurion Demiros|executioner-of-centurion-demiros
bosses|Divine Ansas|Defeat Unique Field Monster Divine Ansas|Executioner of Divine Ansas|executioner-of-divine-ansas
bosses|Harvest Manager Moshav|Defeat Unique Field Monster Harvest Manager Moshav|Executioner of Harvest Manager Moshav|executioner-of-harvest-manager-moshav
bosses|Sentinel K'nash|Defeat Unique Field Monster Sentinel K'nash|Executioner of Sentinel K'nash|executioner-of-sentinel-knash
bosses|Researcher Setram|Defeat Unique Field Monster Researcher Setram|Executioner of Researcher Setram|executioner-of-researcher-setram
bosses|Phantasm Kasia|Defeat Unique Field Monster Phantasm Kasia|Executioner of Phantasm Kasia|executioner-of-phantasm-kasia
bosses|Silent Dartan|Defeat Field Boss Silent Dartan|Executioner of Silent Dartan|executioner-of-silent-dartan
bosses|Soul Ruler Kashapa|Defeat Field Boss Soul Ruler Kashapa|Executioner of Soul Ruler Kashapa|executioner-of-soul-ruler-kashapa
bosses|High Commander Lagta|Defeat Field Boss High Commander Lagta|Executioner of High Commander Lagta|executioner-of-high-commander-lagta
bosses|[Eternal Isle] Eternal Gartua|Defeat Field Boss Eternal Gartua|Executioner of Eternal Gartua|executioner-of-eternal-gartua
bosses|Melted Danar|Defeat Unique Field Monster Melted Danar|Executioner of Melted Danar|executioner-of-melted-danar
bosses|Black Warrior Aed|Defeat Unique Field Monster Black Warrior Aed|Executioner of Black Warrior Aed|executioner-of-black-warrior-aed
bosses|Faithful Rajit|Defeat Unique Field Monster Faithful Rajit|Executioner of Faithful Rajit|executioner-of-faithful-rajit
bosses|Berserker Vargor|Defeat Unique Field Monster Berserker Vargor|Executioner of Berserker Vargor|executioner-of-berserker-vargor
bosses|Blood Warrior Lannar|Defeat Unique Field Monster Blood Warrior Lannar|Executioner of Blood Warrior Lannar|executioner-of-blood-warrior-lannar
bosses|Predator Garsan|Defeat Unique Field Monster Predator Garsan|Executioner of Predator Garsan|executioner-of-predator-garsan
bosses|Deceiver Trid|Defeat Unique Field Monster Deceiver Trid|Executioner of Deceiver Trid|executioner-of-deceiver-trid
bosses|Blue Wave Kelpina|Defeat Unique Field Monster Blue Wave Kelpina|Executioner of Blue Wave Kelpina|executioner-of-blue-wave-kelpina
bosses|Advisor Resana|Defeat Unique Field Monster Advisor Resana|Executioner of Advisor Resana|executioner-of-advisor-resana
bosses|High Overseer Nutah|Defeat Unique Field Monster High Overseer Nutah|Executioner of High Overseer Nutah|executioner-of-high-overseer-nutah
bosses|Special Operations Leader Linx|Defeat Unique Field Monster Special Operations Leader Linx|Executioner of Special Operations Leader Linx|executioner-of-special-operations-leader-linx
bosses|Desecrator Newbold|Defeat Unique Field Monster Desecrator Newbold|Executioner of Desecrator Newbold|executioner-of-desecrator-newbold
bosses|Specter Archon Axios|Defeat Unique Field Monster Specter Archon Axios|Executioner of Specter Archon Axios|executioner-of-specter-archon-axios
bosses|Addicted Hardirun|Defeat Unique Field Monster Addicted Hardirun|Executioner of Addicted Hardirun|executioner-of-addicted-hardirun
bosses|Executioner Barthien|Defeat Unique Field Monster Executioner Barthien|Executioner of Executioner Barthien|executioner-of-executioner-barthien
bosses|Drakan Battalion Weapon Guruta|Defeat Unique Field Monster Drakan Battalion Weapon Guruta|Executioner of Drakan Battalion Weapon Guruta|executioner-of-drakan-battalion-weapon-guruta
bosses|Veteran Shujakan|Defeat Unique Field Monster Veteran Shujakan|Executioner of Veteran Shujakan|executioner-of-veteran-shujakan
bosses|Visionary Karuka|Defeat Unique Field Monster Visionary Karuka|Executioner of Visionary Karuka|executioner-of-visionary-karuka
bosses|Dark Shadow Vishwada|Defeat Unique Field Monster Dark Shadow Vishwada|Executioner of Dark Shadow Vishwada|executioner-of-dark-shadow-vishwada
bosses|Sharp Shylak|Defeat Unique Field Monster Sharp Shylak|Executioner of Sharp Shylak|executioner-of-sharp-shylak
bosses|[Immortal Isle] Immortal Gartua|Defeat Field Boss Immortal Gartua|Executioner of Immortal Gartua|executioner-of-immortal-gartua
exploration|Bonds of the White Wings|Visit all villages in Verteron|Verteron Cartographer|verteron-cartographer
exploration|Bonds of the Black Wings|Visit all villages in Altgard|Altgard Cartographer|altgard-cartographer
exploration|Who Brought the Chest?|Open 3 Hidden Cubes|BLEEP BLOOP BLEEP BLOOP|bleep-bloop-bleep-bloop
exploration|Who Brought the Chest?|Open 3 Hidden Cubes|It's Okay to Be Imperfect|its-okay-to-be-imperfect
exploration|Soaring the Skies|Use Updraft 5 times|Shattered into Teeny, Tiny Pieces|shattered-into-teeny-tiny-pieces
exploration|Riding the Winds|Use Windstream 5 times|Gone with the Wind|gone-with-the-wind
exploration|Uncertain Path|Use Verteron's Spacetime Rift 3 times|Hello There|hello-there
exploration|Uncertain Path|Use Verteron's Spacetime Rift 3 times|Nice to Meet You|nice-to-meet-you
exploration|Dimension Defender|Participate in Dimensional Invasion 3 times|Welcome|welcome
exploration|Dimension Defender|Participate in Dimensional Invasion 3 times|Alien|alien
shugo-festival|Shugo Festival Regular|Participate in Shugo Festival 3 times|Shugo Festival Rookie|shugo-festival-rookie
shugo-festival|Shugo Festival Regular|Participate in Shugo Festival 3 times|Shugo Festival Expert|shugo-festival-expert
shugo-festival|Odyle Flight Frenzy|Participate in [Odyle Flight Frenzy] 1 time|Odyle Drops Keep Fallin' on My Head|odyle-drops-keep-fallin-on-my-head
shugo-festival|Up! Up! Up!|Participate in [Up! Up! Up!] 1 time|Up, Up, and Up Again!|up-up-and-up-again
shugo-festival|Mysterious Track|Participate in [Mysterious Track] 1 time|Mysterious Racer|mysterious-racer
shugo-festival|Defend Shugo Merchants|Participate in [Defend Shugo Merchants] 1 time|Standing on My Own Two Feet|standing-on-my-own-two-feet
shugo-festival|Jump Jump|Participate in [Jump Jump] 1 time|Ruuuuun!!|ruuuuun
shugo-festival|Hidden Lugi|Participate in [Hidden Lugi] 1 time|Catch Me If You Can|catch-me-if-you-can
shugo-festival|Not This Tile?|Participate in [Not This Tile?] 1 time|Tile Discerner|tile-discerner
shugo-festival|Wraith Evasion|Participate in [Wraith Evasion] 1 time|Lady of the Lake|lady-of-the-lake
shugo-festival|Goldrin's Treasure|Participate in [Goldrin's Treasure] 1 time|Arr! Where's Me Treasure?|arr-wheres-me-treasure
hunting|They Just Keep Coming!|Defeat 100 monsters|Ecosystem Eradicator|ecosystem-eradicator
hunting|Cogni Killer|Defeat 100 Cogni Monsters|Cogni Executioner|cogni-executioner
hunting|Driving Beasts Out|Defeat 100 Fera Monsters|Fera Executioner|fera-executioner
hunting|Insect Eradication|Defeat 100 Natura Monsters|Natura Executioner|natura-executioner
hunting|Destroy All Varian|Defeat 100 Varian Monsters|Varian Executioner|varian-executioner
hunting|War on Crime|Defeat 100 Special Monsters|Special Executioner|special-executioner
hunting|Doing You a Favor|Defeat 50 monsters in Altgard|Holding on by a Thread|holding-on-by-a-thread
hunting|Windstream to Eternity|Defeat 100 monsters on Eternal Isle|Eternal Isle Wanderer|eternal-isle-wanderer
hunting|Windstream to Immortality|Defeat 100 monsters on Immortal Isle|Immortal Isle Wanderer|immortal-isle-wanderer
combat|A Dance with Death|Get killed by a Boss Monster 5 times|Reckless Challenge|reckless-challenge
combat|Nothing Personal, Kid|Kill 5 players|Novice Asmodian Hunter|novice-asmodian-hunter
combat|Nothing Personal, Kid|Kill 5 players|Intermediate Asmodian Hunter|intermediate-asmodian-hunter
combat|Nothing Personal, Kid|Kill 5 players|Veteran Asmodian Hunter|veteran-asmodian-hunter
combat|Nothing Personal, Kid|Kill 5 players|Deathbringer|deathbringer
combat|Nothing Personal, Kid|Kill 5 players|Overtaking Black Wings|overtaking-black-wings
combat|Nothing Personal, Kid|Kill 5 players|Treading on Black Wings|treading-on-black-wings
combat|You'll Regret This|Be killed by a player 5 times|Just Getting Started|just-getting-started
combat|You'll Regret This|Be killed by a player 5 times|Evading the Grim Reaper|evading-the-grim-reaper
social|The More the Merrier|Join a Legion|There's No "I" in Team|theres-no-i-in-team
social|Back to Innocence|Make a friend|Co-op Society|co-op-society
social|My Reliable Friends|Collect 3 pets|Tamed|tamed
social|My Reliable Friends|Collect 3 pets|Ride All Creation|ride-all-creation
social|My Reliable Friends|Collect 3 pets|Bond with All Creation|bond-with-all-creation
social|My Reliable Friends|Collect 3 pets|Rule All Creation|rule-all-creation
social|A Clever Pet|Reach Cogni Insight Level 3|Cogni to the Bone|cogni-to-the-bone
social|An Imposing Pet|Reach Fera Insight Level 3|Fera to the Bone|fera-to-the-bone
social|A Fresh Pet|Reach Natura Insight Level 3|Natura to the Bone|natura-to-the-bone
social|A Strange Pet|Reach Varian Insight Level 3|Varian to the Bone|varian-to-the-bone
social|A Special Pet|Reach Special Insight Level 3|Special to the Bone|special-to-the-bone
social|Genus Genius|Reach All Genus Insights Level 10|Unbound by Genus|unbound-by-genus
social|I Have Exceptional Skill|Receive 1 Exceptional Skill Commendation|Has Exceptional Skill|has-exceptional-skill
social|I Have Exceptional Skill|Receive 1 Exceptional Skill Commendation|Divine Skill|divine-skill
social|I'm a Reliable Guardian|Receive 1 Reliable Guardian Commendation|Reliable Guardian|reliable-guardian
social|I'm a Reliable Guardian|Receive 1 Reliable Guardian Commendation|Unyielding Bulwark|unyielding-bulwark
social|I Provide Dedicated Support|Receive 1 Dedicated Support Commendation|Dedicated Supporter|dedicated-supporter
social|I Provide Dedicated Support|Receive 1 Dedicated Support Commendation|Whisper of Unity|whisper-of-unity
social|I Have Great Leadership|Receive 1 Great Leadership Commendation|Great Leader|great-leader
social|I Have Great Leadership|Receive 1 Great Leadership Commendation|Banner of the Vanguard|banner-of-the-vanguard
social|I'm a Helpful Mentor|Receive 1 Helpful Mentor Commendation|Helpful Mentor|helpful-mentor
social|I'm a Helpful Mentor|Receive 1 Helpful Mentor Commendation|Guiding Light|guiding-light
quests|Island of Death, Poeta|Complete Episode Quest 1|Island of Death, Poeta|island-of-death-poeta
quests|Island of Death, Poeta|Complete Episode Quest 1|Dreaming of Paradise|dreaming-of-paradise
quests|Island of Death, Poeta|Complete Episode Quest 1|Searching for High Priestess Reda|searching-for-high-priestess-reda
quests|Island of Death, Poeta|Complete Episode Quest 1|The Past Behind the Sealed Barrier|the-past-behind-the-sealed-barrier
quests|Island of Death, Poeta|Complete Episode Quest 1|Two-Faced|two-faced
quests|Island of Death, Poeta|Complete Episode Quest 1|Encountering Kaisinel's Core|encountering-kaisinels-core
quests|Stories of the People|Complete 1 Regional Quest in Verteron|Verteron Expert|verteron-expert
quests|Stories of the People|Complete 1 Regional Quest in Verteron|Verteron Troubleshooter|verteron-troubleshooter
quests|Five Veiled Fates|Complete Duty Quest: Mission 3 times|Protector of Atreia|protector-of-atreia
quests|Herald of Hope|Complete Duty Quest: Command 3 times|Messenger of Atreia|messenger-of-atreia
quests|Betrayer and Survivor|Complete Episode Quest 1|Betrayer and Survivor|betrayer-and-survivor
quests|Betrayer and Survivor|Complete Episode Quest 1|Stranger in a Strange Land|stranger-in-a-strange-land
quests|Betrayer and Survivor|Complete Episode Quest 1|You're in the Palm of Our Hands|youre-in-the-palm-of-our-hands
quests|Betrayer and Survivor|Complete Episode Quest 1|Ill-Fated Encounter|ill-fated-encounter
quests|Betrayer and Survivor|Complete Episode Quest 1|I Only Wanted You|i-only-wanted-you
quests|Betrayer and Survivor|Complete Episode Quest 1|Encountering Zikel's Core|encountering-zikels-core
enhancement|Common and Beyond|Enhance Common Gear to +5|Splendent Glow|splendent-glow
enhancement|Rare and Beyond I|Enhance Rare Gear to +5|Green Glow|green-glow
enhancement|Legendary Gambler's Challenge|Enhance Epic Gear to +5|Azure Glow|azure-glow
enhancement|Tailor-Made|Enhance Unique Gear to +5|Golden Glow|golden-glow
enhancement|Power of Steady Enhancement|Enhance gear 10 times|Pouring Water into a Sieve|pouring-water-into-a-sieve
enhancement|Fulfilled Soul|Achieve 100% Soul Binding on 1 piece of gear|Perfectionist|perfectionist
enhancement|Shaky Extraction|Extract +10 or higher gear 5 times|Extractor|extractor
crafting|Blacksmithing Specialist|Reach Crafting: Novice Blacksmithing Proficiency Level 50|Artisan Blacksmith|artisan-blacksmith
crafting|Blacksmithing Specialist|Reach Crafting: Novice Blacksmithing Proficiency Level 50|Blacksmithing Is Life|blacksmithing-is-life
crafting|Endless Hammering|Succeed in Crafting: Blacksmithing 5 times|Iron Arm|iron-arm
crafting|Armorsmithing Specialist|Reach Crafting: Novice Armorsmithing Proficiency Level 50|Artisan Armorsmith|artisan-armorsmith
crafting|Armorsmithing Specialist|Reach Crafting: Novice Armorsmithing Proficiency Level 50|Warriors' Idol|warriors-idol
crafting|Resilient Armor|Succeed in Crafting: Armorsmithing 5 times|Reliable Ally|reliable-ally
crafting|Handicrafting Specialist|Reach Crafting: Novice Handicrafting Proficiency Level 50|Artisan Handicrafter|artisan-handicrafter
crafting|Handicrafting Specialist|Reach Crafting: Novice Handicrafting Proficiency Level 50|You're My Gem|youre-my-gem
crafting|Detail Oriented|Succeed in Crafting: Handicrafting 5 times|Extreme Detailing|extreme-detailing
crafting|Alchemy Specialist|Reach Crafting: Novice Alchemy Proficiency Level 50|Artisan Alchemist|artisan-alchemist
crafting|Alchemy Specialist|Reach Crafting: Novice Alchemy Proficiency Level 50|Something from Nothing|something-from-nothing
crafting|Astonishing Alchemy|Succeed in Crafting: Alchemy 5 times|Seeker of Truths|seeker-of-truths
crafting|Cooking Specialist|Reach Crafting: Novice Cooking Proficiency Level 50|Artisan Chef|artisan-chef
crafting|Cooking Specialist|Reach Crafting: Novice Cooking Proficiency Level 50|★★★ Chef|chef
crafting|3 Minute Cook|Succeed in Crafting: Cooking 5 times|Flavors and Flair|flavors-and-flair
crafting|Soaked in Crafting|Craft Artisan Gear 5 times|Artisan Crafter|artisan-crafter
gear-collection|Fashionista|Collect 10 Skins|Fashionista|fashionista
gear-collection|Fashionista|Collect 10 Skins|Fashion Forward|fashion-forward
gear-collection|Fashionista|Collect 10 Skins|Empty Closet|empty-closet
gear-collection|Veteran Wing Collector|Collect 3 Wings|Shaking Off the World's Shackles|shaking-off-the-worlds-shackles
gear-collection|Veteran Wing Collector|Collect 3 Wings|Dominator of Dimensions|dominator-of-dimensions
gear-collection|Transformation Whizz|Collect 5 Titles|Going Around in Circles|going-around-in-circles
gear-collection|Transformation Whizz|Collect 5 Titles|Transformation Whizz|transformation-whizz
gear-collection|Shugo Collection|Collect 1 Unique Shugo Festival Artwork|Scenery Collector|scenery-collector
gear-collection|Shugo Collection|Collect 1 Unique Shugo Festival Artwork|Click|click
gear-collection|Conquering Boots Artwork|Collect 1 Unique Expedition Artwork|At Your Own Pace|at-your-own-pace
gear-collection|Conquering Boots Artwork|Collect 1 Unique Expedition Artwork|Steps on the Journey|steps-on-the-journey
gear-collection|Nightmare Statue|Collect 1 Unique Nightmare Statue|Ferocious Statue|ferocious-statue
gear-collection|Nightmare Statue|Collect 1 Unique Nightmare Statue|Twinkling Eyes|twinkling-eyes
gear-collection|Boss Loot|Collect 1 Unique Field Monster, Boss Artwork|Keen Eye|keen-eye
gear-collection|Boss Loot|Collect 1 Unique Field Monster, Boss Artwork|Genuine Masterpiece|genuine-masterpiece
kibelisks|Verteron Binding Master|Activate all Kibelisks in Verteron|Teleportation Specialist|teleportation-specialist
kibelisks|Altgard Binding Veteran|Activate all Kibelisks in Altgard|Teleportation Specialist|teleportation-specialist
sealed-dungeons|The Broken Seal of Verteron|Clear 3 Sealed Dungeons in Verteron|Verteron Seal Breaker|verteron-seal-breaker
sealed-dungeons|The Broken Seal of Altgard|Clear 3 Sealed Dungeons in Altgard|Altgard Seal Breaker|altgard-seal-breaker
strongholds|Verteron Stronghold Sweep|Clear 1 Stronghold in Verteron|Knock Knock Who's There|knock-knock-whos-there
strongholds|Altgard Stronghold Sweep|Clear 1 Stronghold in Altgard|Housekeeping Open Up|housekeeping-open-up
milestones|Only as Good as One's Gear|Reach Character Item Level 50|One Step at a Time|one-step-at-a-time
milestones|Only as Good as One's Gear|Reach Character Item Level 50|Designer Drip|designer-drip
gathering|Essence Extraction Specialist|Reach Novice Essence Extraction Proficiency Level 50|Professional Extractor|professional-extractor
gathering|Essence Extraction Specialist|Reach Novice Essence Extraction Proficiency Level 50|The World Is My Resource|the-world-is-my-resource
gathering|Skybound Treasure|Successfully gather 5 Odyle|Extracting in My Sleep|extracting-in-my-sleep
consumables|The Joy of Spending|Spend 100,000 Kina at Merchants|High Roller|high-roller
consumables|Black Cloud Merchants Regular|Purchase 5 items at Black Cloud Merchants|Big Spender|big-spender
consumables|Storage Keeper|Store items in the Storage 5 times|No Heavy Lifting!|no-heavy-lifting
fire-temple|Fire Temple Exploration Clear|Clear Fire Temple Exploration 1 time|Fire Temple Sightseer|fire-temple-sightseer
fire-temple|Fire Temple Conquest Clear|Clear Fire Temple Conquest on Normal 1 time|Fire Temple Tour Guide|fire-temple-tour-guide
fire-temple|Sauna|Lie down in the Fire Temple Conquest Boss Room|Kromede Will Remember That|kromede-will-remember-that
draupnir-cave|Draupnir Exploration Clear|Clear Draupnir Exploration 1 time|Draupnir Sightseer|draupnir-sightseer
draupnir-cave|Draupnir Conquest Clear|Clear Draupnir Conquest on Normal 1 time|Draupnir Tour Guide|draupnir-tour-guide
draupnir-cave|Enemy-Supplied Shortcut|Operate the Windstream Control Device in Draupnir 10 times|Pathfinder|pathfinder
krao-cave|Krao Cave Exploration Clear|Clear Krao Cave Exploration 1 time|Krao Cave Sightseer|krao-cave-sightseer
krao-cave|Krao Cave Conquest Clear|Clear Krao Cave Conquest on Normal 1 time|Krao Cave Tour Guide|krao-cave-tour-guide
krao-cave|Snipers First|Defeat 20 Sniping Crokas in Krao Cave|One Step Ahead|one-step-ahead
urugugu|Urugugu Canyon Exploration Clear|Clear Urugugu Canyon Exploration 1 time|Urugugu Canyon Sightseer|urugugu-canyon-sightseer
urugugu|Urugugu Canyon Conquest Clear|Clear Urugugu Canyon Conquest on Normal 1 time|Urugugu Canyon Tour Guide|urugugu-canyon-tour-guide
urugugu|Totem Destroyer|Destroy 20 Healing/Blazing Totems in Urugugu Canyon|Totem Destroyer|totem-destroyer
vakron|Vakron Sky Island Exploration Clear|Clear Vakron Sky Island Exploration 1 time|Vakron Sky Island Sightseer|vakron-sky-island-sightseer
vakron|Vakron Sky Island Conquest Clear|Clear Vakron Sky Island Conquest on Normal 1 time|Vakron Sky Island Tour Guide|vakron-sky-island-tour-guide
vakron|Trampled Dream|Defeat 20 Island Guardian Archers in Vakron Sky Island|Good-for-Nothing|good-for-nothing
horn-den|Ferocious Horn Den Exploration Clear|Clear Ferocious Horn Den Exploration 1 time|Ferocious Horn Den Sightseer|ferocious-horn-den-sightseer
horn-den|Ferocious Horn Den Conquest Clear|Clear Ferocious Horn Den Conquest on Normal 1 time|Ferocious Horn Den Tour Guide|ferocious-horn-den-tour-guide
horn-den|Faith in the Totem|Destroy 20 Mau/Fafnite Totems in Ferocious Horn Den|Hey! I'm Walkin' Here!|hey-im-walkin-here
"""


def main():
    out, multi = [], {}
    for line in ROWS.strip().splitlines():
        g, ach, goal, title, slug = [x.strip() for x in line.split("|")]
        assert g in GROUPS, g
        out.append({"id": f"{g}/{slug}/{len(out)}", "group": g, "achievement": ach, "goal": goal,
                    "title": title, "slug": slug})
        multi[(g, ach)] = multi.get((g, ach), 0) + 1
    for r in out:
        r["tiers"] = multi[(r["group"], r["achievement"])] > 1
    data = {
        "source": "MetaBot.GG",
        "source_url": "https://metabot.gg/en/aion-2/achievements",
        "collected": "2026-10-19",
        "groups": [{"id": k, "name": v, "url": f"https://metabot.gg/en/aion-2/achievements/{k}"} for k, v in GROUPS.items()],
        "items": out,
    }
    path = Path(__file__).resolve().parent.parent / "daeva" / "data" / "conquistas_titulos.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "conquistas com título ->", path)


if __name__ == "__main__":
    main()
