# Locale Map: Ironcrest
- **Feature ID:** `ironcrest`
- **Classification:** Settlement
- **Scale Profile:** Small / Compact (Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.)
- **Registered Features:** 6

### Geographic & World Context
- **Overview Lore:** A compact, fortified highland mining outpost established in the shadow of the Northern Ribs to mine magnetite iron and quarry dark slate.
- **Host Region:** The Undulating Downs (Hills)
  - *Host Region Lore:* "Once pastoral sheep-walks and lonely bluffs, the highlands have unified under the High Thane of Dun Kestrel into a fortified domain of white-chalk bastions, limestone quarries, terraced barley fields, and disciplined border companies."
- **Surrounding Perimeters:**
  - **ALL BORDERS:** Transition into host region (The Undulating Downs — Hills).
    - *Lore Context:* "Once pastoral sheep-walks and lonely bluffs, the highlands have unified under the High Thane of Dun Kestrel into a fortified domain of white-chalk bastions, limestone quarries, terraced barley fields, and disciplined border companies."
- **External Ingress & Connected Destinations:**
  - **SOUTH Approach:** The Iron-Trace (Road) -> Leads toward Dun Kestrel (Citadel)
    - *Road Lore:* "A steep, graded wagon-track of crushed limestone and basalt ballast linking the high citadel of Dun Kestrel with the northern iron mines of Ironcrest."
    - *Destination Context:* "Elevated from a pastoral hill-fort into the sovereign stone citadel of the western highlands. Encircled by cyclopean chalk-ashlar ramparts, high beacon towers, and cavernous grain vaults, Dun Kestrel now commands the sheep-walks, quarries, and reclaimed polders of the downs as an equal rival to the River Throne."

### World Relations & Material Flow
Ironcrest functions as the primary material engine for Dun Kestrel, supplying dark slate for citadel roofing and rich magnetite iron for arms, armor, and structural ironwork along the steep Iron-Trace wagon road.

### Architectural & Spatial Rationale
The outpost is tightly enclosed by chalk-ashlar and timber palisades built into the mountain base. Mining shafts and slate benches press directly against the northern rock face, while smelting kilns, barracks, and wagon yards surround a central courtyard connected directly to the southern gatehouse and the Iron-Trace road.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^^^^^^^^^^^^^^^^                            |    00: 0000000000000000
01: ^^^:::^^^^:::^^^                            |    01: 0000000000000000
02: ^^::...M....::^^                            |    02: 0000000200000000
03: ^:#####+######:^                            |    03: 0022222233333300
04: ^#.....+......#^                            |    04: 0222222233333330
05: ^#.+S++++++K..#^                            |    05: 0222222233333330
06: :#.....+......#:                            |    06: 0222222233333330
07: :#.....+......#:                            |    07: 0111111111111110
08: ,#.....+......#,                            |    08: 0111111111111110
09: ,#.+B++++++W..#,                            |    09: 0444444444444440
10: ,#.....+......#,                            |    10: 0444444444444440
11: ,:#####G######:,                            |    11: 0044444444444400
12: ::::::+++:::::::                            |    12: 0000000000000000
13: ,,,,,,:+:,,,,,,,                            |    13: 0000000000000000
14: ,,,,,,:+:,,,,,,,                            |    14: 0000000000000000
15: ,,,,,,:+:,,,,,,,                            |    15: 0000000000000000
```

### Features Registry
- ID 'garrison_barracks': **Border Company Quarters** ['B'] (barracks)
  - Position: [X: 04, Y: 09]
  - Lore: Reinforced chalk-ashlar barracks providing quarters and armaments for the disciplined guards stationed by the High Thane.
- ID 'iron_gatehouse': **The South Iron Gatehouse** ['G'] (gatehouse)
  - Position: [X: 07, Y: 11]
  - Lore: A thick chalk-and-timber barrier controlling access between the Iron-Trace wagon road and the interior mine yard.
- ID 'magnetite_mine_shaft': **Northern Ribs Mine Incline** ['M'] (mine_shaft)
  - Position: [X: 07, Y: 02]
  - Lore: A timber-shored shaft driving deep into the highland ridge to extract high-purity magnetite iron for Dun Kestrel.
- ID 'slate_quarry_saw': **Highland Slate Works** ['S'] (quarry)
  - Position: [X: 04, Y: 05]
  - Lore: Open cutting benches and wedge-frames where dark slate is split into roofing shingles and structural slabs for the citadel.
- ID 'smelting_hearth': **Assay Kiln & Tool Smithy** ['K'] (smithy)
  - Position: [X: 11, Y: 05]
  - Lore: Draft-boosted masonry furnaces used to test iron ore purity and repair heavy steel drills, picks, and wagon axles.
- ID 'wagon_depot': **Iron-Trace Wagon Yard** ['W'] (depot)
  - Position: [X: 11, Y: 09]
  - Lore: A heavy-timber staging barn where ballast wagons and draft oxen assemble before hauling iron and slate south.

### Districts Registry
- ID '0': **Frontier Buffer & Chalk Bluffs** (buffer)
  - Lore: Unzoned limestone bluffs and rolling downs surrounding the outpost, marked by wild sheep-walks and scree slopes.
- ID '1': **Redoubt Staging Courtyard** (square)
  - Lore: A graveled, timber-braced yard where heavy ore wagons are loaded, weighed, and prepared for transit along the Iron-Trace.
- ID '2': **Magnetite Incline & Slate Quarry** (crafts)
  - Lore: Shored shaft mouths and quarry terraces extracting dark slate slabs and rich magnetite veins from the roots of the Northern Ribs.
- ID '3': **Assay Kilns & Smelting Hearth** (crafts)
  - Lore: High-heat stone furnaces and blacksmith hearths where magnetite ore is assayed and iron quarrying tools are forged.
- ID '4': **Garrison Hold & Iron Gatehouse** (keep)
  - Lore: A fortified chalk-ashlar gatehouse and timber barracks housing the High Thane's border guards and mining overseers.
