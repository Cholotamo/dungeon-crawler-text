# Locale Map: Kar-Drakh
- **Feature ID:** `kar_drakh`
- **Classification:** Dungeon
- **Scale Profile:** Compact Subterranean Complex
- **Registered Features:** 6

### Geographic & World Context
- **Overview Lore:** A colossal, cyclopean gatehouse hewn into the sheer cliff face of the Red Sandstone Canyon. As Ironcrest transforms into a sovereign mountain citadel, deep magnetite excavation tremors rumble through the outer mountain bedrock, though Kar-Drakh's sealed basalt doors and subterranean sanctums remain silent and unviolated.
- **Host Region:** Red Sandstone Canyon (Cliffs)
  - *Host Region Lore:* "A dizzying, mile-deep chasm where surging jade-green rapids thresh beneath sheer walls draped in hanging gardens of primordial ferns and liverworts."
- **Surrounding Perimeters:**
  - **SOUTH & EAST BORDER:** The Northern Ribs (Mountains)
    - *Lore Context:* "The desolate alpine screes and towering granite crags now thunder day and night with the deep tremors of heavy excavation, blast furnaces, and cascading slag-sluices, as the newly elevated citadel of Ironcrest delves labyrinthine adits into the ancient mountain roots to harvest vast deposits of black magnetite iron and dark roofing slate."
  - **NORTH & WEST BORDERS:** Transition into host region (Red Sandstone Canyon — Cliffs).
    - *Lore Context:* "A dizzying, mile-deep chasm where surging jade-green rapids thresh beneath sheer walls draped in hanging gardens of primordial ferns and liverworts."
- **External Ingress & Connected Destinations:**
  - **Perimeter Approach:** None -> Wilderness Traversal
    - *Destination Context:* "None. (Isolated wilderness site; entry is via local terrain traversal)."

### World Relations & Material Flow
Kar-Drakh remains an enigmatic, ancient sanctuary buried deep within the sandstone cliffs. The dramatic elevation of Ironcrest into a heavy iron-producing citadel intensifies mining along the shared mountain roots, bringing constant tremors and stone debris to the outer perimeters without breaching the sealed dungeon within.

### Architectural & Spatial Rationale
The internal layout and ancient features of Kar-Drakh remain undisturbed behind sealed rune-carved basalt doors. Along the southeastern perimeter, minor bedrock displacement and expanded scree slopes reflect the heavy excavation tremors and slag runoff from Ironcrest's deep adit delvings.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^^~~;;,&&^^^^###                            |    00: 0000000000000000
01: ^^~~;;,,&&^^####                            |    01: 0000000000000000
02: ^^&,,+..#+######                            |    02: 0011111000000000
03: ^^&,,G..#####..#                            |    03: 0011122000004400
04: #####.../......#                            |    04: 0000222222224400
05: #####+#####+####                            |    05: 0000020000000000
06: ###......#.....#                            |    06: 0003333330444440
07: ###...H..|..S..#                            |    07: 0003333330444440
08: ###......#.....#                            |    08: 0003333330444440
09: #####+######/###                            |    09: 0000030000000000
10: ###......#.....#                            |    10: 0005555556666660
11: ###......#..~..#                            |    11: 0005555556666660
12: ###..R...W.~~~.#                            |    12: 0005555556666660
13: ###......#..A.~#                            |    13: 0005555556666660
14: ##############::                            |    14: 0000000000000000
15: #############:::                            |    15: 0000000000000000
```

### Features Registry
- ID 'chasm_span': **Basalt Walkway Span** ['W'] (span)
  - Position: [X: 09, Y: 12]
  - Lore: A cyclopean stone bridge spanning the subterranean pool within the inner sanctum.
- ID 'cyclopean_gate': **Rune-Carved Basalt Gate** ['G'] (gatehouse)
  - Position: [X: 05, Y: 03]
  - Lore: Massive basalt doors carved with ancient glyphs, sealing the colossal entrance cut into the cliff face.
- ID 'hearth_brazier': **Basalt Pillar Brazier** ['H'] (hearth)
  - Position: [X: 06, Y: 07]
  - Lore: A monolithic basalt pillar topped with an eternal flame brazier, casting amber light across the Great Basalt Hall.
- ID 'runic_stele': **Rune-Carved Stele** ['R'] (monolith)
  - Position: [X: 05, Y: 12]
  - Lore: An unyielding black basalt stele inscribed with ancient runic script pre-dating mortal speech.
- ID 'sanctum_altar': **Altar of the Vanished** ['A'] (altar)
  - Position: [X: 12, Y: 13]
  - Lore: An ancient sandstone altar overlooking the subterranean plunge pool, where pre-mortal rites were conducted.
- ID 'sarcophagus_vault': **Cyclopean Sarcophagus** ['S'] (sarcophagus)
  - Position: [X: 12, Y: 07]
  - Lore: A massive stone sarcophagus in the Crypt of the Vanished, sealed with iron-bound basalt slabs.

### Districts Registry
- ID '0': **Frontier Buffer & Canyon Bedrock** (buffer)
  - Lore: Unzoned, dizzying canyon precipices draped in primordial ferns to the north and west, and dark mountain bedrock echoing with the thunder of Ironcrest's deep magnetite mines and cascading scree along the south and east.
- ID '1': **Canyon Ledge Approach** (antechamber)
  - Lore: A narrow, wind-scoured trail winding along the sheer red sandstone cliff edge toward the ancient gatehouse threshold.
- ID '2': **Cyclopean Gatehouse & Outer Antechamber** (antechamber)
  - Lore: A vaulted entry hall carved into the cliff face, flanked by monumental sandstone pillars and heavy threshold barriers.
- ID '3': **Great Basalt Hall** (hall)
  - Lore: A wide subterranean hall constructed from giant dark basalt blocks, featuring ancient fire braziers and stone partitions.
- ID '4': **Crypt of the Vanished** (crypt)
  - Lore: A solemn hypogeum where ancient guardians were laid to rest within stone niches before recorded history.
- ID '5': **Vault of Primordial Runes** (vault)
  - Lore: An inner chamber housing unyielding basalt steles inscribed with glowing, forgotten runes of power.
- ID '6': **Subterranean Chasm & Sanctum** (sanctum)
  - Lore: A cavernous abyss where a jade subterranean pool plunges into hidden subterranean channels, bridged by a basalt walkway leading to a forgotten altar.
