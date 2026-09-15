# Locale Map: Ironcrest
- **Feature ID:** `ironcrest`
- **Classification:** Settlement
- **Scale Profile:** Settlement turned into big city (Small / Compact -> Large / Urban). Urban Densification & Fortification.
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** Elevated from a frontier mining redoubt into a sovereign mountain fortress-citadel. Crowned with cyclopean slate ramparts, soaring blast furnaces, and deep labyrinthine adits delved into the roots of the Northern Ribs, Ironcrest now stands as the supreme industrial and martial bastion of the highland clans, supplying cold-forged magnetite steel to the entire realm.
- **Host Region:** The Undulating Downs (Hills)
  - *Host Region Lore:* "Anchored between the twin sovereign citadels of Dun Kestrel and Ironcrest, the high rolling chalklands have transformed into a fortified highland realm of martial discipline, deep limestone quarries, terraced barley slopes, and rumbling iron-wains traversing the paved trace."
- **Surrounding Perimeters:**
  - **NORTH:** Transition into host region (The Northern Ribs — Alpine Crags).
    - *Lore Context:* "The desolate alpine screes and towering granite crags thunder day and night with deep tremors of heavy excavation, blast furnaces, and cascading slag-sluices as Ironcrest delves into the ancient mountain roots."
  - **SOUTH / EAST / WEST:** Transition into host region (The Undulating Downs — Hills).
    - *Lore Context:* "Anchored between the twin sovereign citadels of Dun Kestrel and Ironcrest, the high rolling chalklands have transformed into a fortified highland realm of martial discipline, deep limestone quarries, terraced barley slopes, and rumbling iron-wains traversing the paved trace."
- **External Ingress & Connected Destinations:**
  - **SOUTH Approach:** The Iron-Trace (Paved Highway) -> Leads toward Dun Kestrel (Sovereign Citadel)
    - *Road Lore:* "A paved, heavy-ballasted highway of fitted slate and limestone, worn by constant convoys of heavy iron-wains hauling magnetite ingots and refined steel south to Dun Kestrel."
    - *Destination Context:* "The sovereign stone citadel of the western highlands, defended by cyclopean chalk-ashlar ramparts and high beacon towers, bound to Ironcrest as its grand iron-foundry and armor-forge."

### World Relations & Material Flow
Ironcrest operates as the supreme industrial engine and martial northern anchor of the highland realm, supplying high-purity magnetite steel, armor plate, and structural slate to Dun Kestrel while commanding the mountain passes against northern threats.

### Architectural & Spatial Rationale
To support its evolution from a simple redoubt into a sovereign mountain fortress-citadel, the perimeter palisades were replaced with cyclopean slate and limestone ramparts. Twin iron-reinforced gatehouses secure the southern approach, while blast furnace batteries, heavy wain depots, and garrison keeps were expanded around paved inner thoroughfares. Labyrinthine adits and deep shafts now pierce directly into the mountain roots.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^^^^^^^^^^^^^^^^                            |    00: 0000000000000000
01: ^^^^^^^M^^^^^^^^                            |    01: 0000000200000000
02: ^^#####+######^^                            |    02: 0022222233333300
03: ^#++++++|+++++#^                            |    03: 0222222233333330
04: ^#+....+.....+#^                            |    04: 0222222233333330
05: ^#+S...+...K.+#^                            |    05: 0222222233333330
06: ^#+....+.....+#^                            |    06: 0222222233333330
07: ^#+++++C+####+#^                            |    07: 0111111111111110
08: ^#+....+.....+#^                            |    08: 0111111111111110
09: ^#+B...+...W.+#^                            |    09: 0444444444444440
10: ^#+....+.....+#^                            |    10: 0444444444444440
11: ^:#####G######:^                            |    11: 0044444444444400
12: ::::::+++:::::::                            |    12: 0000000000000000
13: ,,,,,,:+:,,,,,,,                            |    13: 0000000000000000
14: ,,,,,,:+:,,,,,,,                            |    14: 0000000000000000
15: ,,,,,,:+:,,,,,,,                            |    15: 0000000000000000
```

### Features Registry
- ID 'garrison_barracks': **Highland Guard Barracks & Armory** ['B'] (barracks)
  - Position: [X: 03, Y: 09]
  - Lore: A multi-story slate-roofed barracks and armory garrisoning disciplined border guards and combat engineers of the High Thane.
- ID 'high_citadel_keep': **Clan Thane's Iron Keep** ['C'] (keep)
  - Position: [X: 07, Y: 07]
  - Lore: The central stone keep and administrative seat of Ironcrest, commanding the mine works and housing the master smiths and clan commanders.
- ID 'iron_gatehouse': **The Grand Slate Gatehouse** ['G'] (gatehouse)
  - Position: [X: 07, Y: 11]
  - Lore: A cyclopean slate-and-iron gatehouse fitted with portcullis grates, commanding the southern entrance along the Iron-Trace highway.
- ID 'magnetite_mine_shaft': **Northern Ribs Great Adit & Incline** ['M'] (mine_shaft)
  - Position: [X: 07, Y: 01]
  - Lore: A massive timber-braced and slate-arched adit driving deep into the core of the Northern Ribs to extract high-purity magnetite ore and dark slate.
- ID 'slate_quarry_saw': **Highland Slate Terrace Works** ['S'] (quarry)
  - Position: [X: 03, Y: 05]
  - Lore: Expansive stepped cutting terraces and wedge-cranes splitting thick slabs of dark slate for fortress roofing and rampart facing.
- ID 'smelting_hearth': **Soaring Blast Furnaces & Foundry** ['K'] (smithy)
  - Position: [X: 11, Y: 05]
  - Lore: Draft-boosted charcoal blast furnaces and foundry hearths operating day and night to smelt magnetite ore into refined steel ingots.
- ID 'wagon_depot': **Iron-Wain Staging Yard & Depot** ['W'] (depot)
  - Position: [X: 11, Y: 09]
  - Lore: A fortified staging yard and repair depot where heavy iron-wains and draft oxen are prepared for the journey along the Iron-Trace.

### Districts Registry
- ID '0': **Frontier Buffer & Mountain Roots** (buffer)
  - Lore: Unzoned mountain rock faces, alpine scree, and rolling downs surrounding the fortress-citadel.
- ID '1': **Central Citadel & Upper Square** (square)
  - Lore: Paved inner courtyards and central keep grounds connecting the mine adits to the smelting foundries.
- ID '2': **Adit Incline & Slate Quarries** (crafts)
  - Lore: Stepped quarry terraces and heavy timbered mine mouths extracting magnetite ore and dark slate slabs.
- ID '3': **Blast Furnace & Foundry District** (crafts)
  - Lore: Roaring blast furnaces, charcoal stores, and casting hearths forging magnetite steel ingots.
- ID '4': **Southern Citadel Bastion & Wain Yard** (keep)
  - Lore: Fortified lower wards housing border guard barracks, iron-wain staging barns, and the south gatehouse.
