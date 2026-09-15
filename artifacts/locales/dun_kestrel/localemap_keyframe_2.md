# Locale Map: Dun Kestrel
- **Feature ID:** `dun_kestrel`
- **Classification:** Settlement
- **Scale Profile:** Settlement turned into big city (Small / Compact -> Large / Urban). Urban Densification & Fortification.
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** Elevated from a pastoral hill-fort into the sovereign stone citadel of the western highlands, Dun Kestrel is encircled by cyclopean chalk-ashlar ramparts, high beacon towers, and cavernous grain vaults, commanding both the reclaimed polders and the ancient wool routes.
- **Host Region:** The Undulating Downs (Hills)
  - *Host Region Lore:* "Once pastoral sheep-walks and lonely bluffs, the highlands have unified under the High Thane of Dun Kestrel into a fortified domain of white-chalk bastions, limestone quarries, terraced barley fields, and disciplined border companies."
- **Surrounding Perimeters:**
  - **ALL BORDERS:** Transition into host region (The Undulating Downs — Hills).
    - *Lore Context:* "Once pastoral sheep-walks and lonely bluffs, the highlands have unified under the High Thane of Dun Kestrel into a fortified domain of white-chalk bastions, limestone quarries, terraced barley fields, and disciplined border companies."
- **External Ingress & Connected Destinations:**
  - **WEST Approach:** The Hollow-Trace (Road) -> Leads toward The Hollow Polders (Waterworks)
    - *Road Lore:* "New road established leading toward None. A graded chalk-gravel road descending the steep western spurs of Dun Kestrel to connect the mountain citadel with the hydraulic ditches and barley fields of the Hollow Polders."
    - *Destination Context:* "The Hollow Polders (Waterworks): A vast hydraulic grid of drainage trenches, sluices, and dykes where reclaimed peat-bogs produce abundant barley and grain for the highland garrisons."
  - **EAST Approach:** The Downs-Way (Road) -> Leads toward Aethelford (City)
    - *Road Lore:* "A heavily traveled beaten dirt and crushed-limestone track linking Dun Kestrel's east gate directly to the bustling river markets and ashlar quays of Aethelford."
    - *Destination Context:* "Aethelford (City): The sovereign river-city of the Silver Channel, boasting stone quays, granaries, and a fortified timber-and-stone citadel guarding the crossing into the eastern forest."

### World Relations & Material Flow
Dun Kestrel exports wool bales, dressed limestone blocks, and harvested barley from the Hollow Polders along the Downs-Way to Aethelford, while receiving forged steel weaponry, specialized timber, and luxury river goods from the sovereign city.

### Architectural & Spatial Rationale
To reflect its expansion from a compact hill-fort to a major urban citadel, Dun Kestrel's timber palisades were replaced with massive ashlar ramparts. A new western gate and graded road (The Hollow-Trace) were carved out to secure grain flows from the reclaimed Hollow Polders, while deep stone vaults were excavated to store surplus grain and quarried chalk.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^,^,,,^,,,,,,,,,                            |    00: 0000000000000000
01: ,,,,,^,,,,,,,,,,                            |    01: 0000000000000000
02: ,,,########,,,,,                            |    02: 0001111111100000
03: ,,,#.B.#.S.#,:|:                            |    03: 0001111111100330
04: ^,,#.+...+..#,:|                            |    04: 0001111111100330
05: ,,,#.V.#...#,:|:                            |    05: 0001111111100330
06: ++++W...+...+:::                            |    06: 5555111111100330
07: ++++#...+...E+++                            |    07: 5555111111144444
08: ^,,#.C.#.G.#::::                            |    08: 0002222222200330
09: ,,,#.+...+..#,:|                            |    09: 0002222222200330
10: ,,,########,,:|:                            |    10: 0002222222200330
11: ,,,,,,::::,,,,,,                            |    11: 0000003333000000
12: ^,,,,,::::,,,,^,                            |    12: 0000003333000000
13: ,,,,,,,::,,,,,,,                            |    13: 0000000000000000
14: ^,^,,,,,,,,,,,^,                            |    14: 0000000000000000
15: ,,,^,,,,,,,,,,^,                            |    15: 0000000000000000
```

### Features Registry
- ID 'clan_armory': **Highland Forge & Armory** ['S'] (smithy)
  - Position: [X: 09, Y: 03]
  - Lore: Expanded into a massive stone workshop producing iron-rimmed wheels, masonry tools, and steel armaments for the High Thane's guards.
- ID 'east_gatehouse': **Downs-Way East Gate** ['E'] (gatehouse)
  - Position: [X: 12, Y: 07]
  - Lore: The monumental stone entrance opening onto the Downs-Way, equipped with iron portcullises and guard barracks.
- ID 'grain_vaults': **Highland Grain & Polder Vaults** ['V'] (granary)
  - Position: [X: 05, Y: 05]
  - Lore: Deep stone subterranean vaults storing thousands of bushels of barley harvested from the newly reclaimed Hollow Polders.
- ID 'high_beacon': **High Chalk Beacon Tower** ['B'] (hearth)
  - Position: [X: 05, Y: 03]
  - Lore: A towering stone beacon kiln built over the ancient chalk hearth, its high flames signaling the highland clans across the Undulating Downs.
- ID 'limestone_quarry': **Chalk-Stone Supply Depot** ['G'] (vault)
  - Position: [X: 09, Y: 08]
  - Lore: Heavy stone storehouses and dressed ashlar yards holding cut limestone blocks for rampart expansion and export to Aethelford.
- ID 'thanes_citadel': **High Thane's Citadel** ['C'] (keep)
  - Position: [X: 05, Y: 08]
  - Lore: A grand ashlar-walled citadel crowning the highest bluff, serving as the throne of the unified highland clans.
- ID 'west_gatehouse': **Hollow-Trace Gatehouse** ['W'] (gatehouse)
  - Position: [X: 04, Y: 06]
  - Lore: A heavily fortified ashlar gatehouse guarding the steep western descent towards the Hollow Polders.

### Districts Registry
- ID '0': **Frontier Buffer & Wild Downs** (buffer)
  - Lore: Unzoned rolling hills of fescue, wild rye, and craggy limestone bluffs.
- ID '1': **High Citadel Commons & Armory Ward** (square)
  - Lore: The stone-paved upper yard housing the beacon kiln, high smithy, and subterranean grain vaults.
- ID '2': **High Thane's Keep & Vaults Ward** (keep)
  - Lore: The monumental ashlar southern wing housing the High Thane's citadel and dressed stone storehouses.
- ID '3': **Terraced Sheep-Runs & Polder Slopes** (farmland)
  - Lore: Enclosed hurdle terraces and hillside pastures overlooking the western polders and eastern roads.
- ID '4': **Downs-Way Approach** (crafts)
  - Lore: The eastern ashlar gate approach connecting Dun Kestrel to Aethelford.
- ID '5': **Hollow-Trace Approach** (crafts)
  - Lore: The graded western chalk track connecting the citadel gates to the hydraulic barley polders.
