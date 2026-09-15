# Locale Map: The Necropolis of Mor-Ghul
- **Feature ID:** `mire_tomb_mor_ghul`
- **Classification:** Dungeon
- **Scale Profile:** Expanded Subterranean Necropolis & Ruptured Crypt Complex
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** Unsealed by ruptured wards, the half-submerged necropolis has awakened into an active necrotic locus, spewers of cold death-fog and drowned wights across black-silt oxbows.
- **Host Region:** The Drowned Clearings (Lake)
  - *Host Region Lore:* "A petrified desolation of necrotic ash and calcified roots, where the shattered wards of Mor-Ghul bleed ancient malevolence into the withered fens, choking the waterways with poisoned silt and unhallowed spirits."
- **Surrounding Perimeters:**
  - **SOUTH & WEST BORDER:** The Greenwood Vault (Forest)
    - *Lore Context:* "The primeval peace of the eastern timberlands is smothered by lingering fear as cold necrotic vapors drift through the ancient hemlock canopy, testing the iron resolve of the wardens at Eaveshold."
  - **NORTH & EAST BORDERS:** The Drowned Clearings (Lake)
    - *Lore Context:* "A forsaken expanse of stagnant oxbows where the water runs black with necromantic ash, unhallowed corpse-candles burn in perpetual fog, and restless spirits wail beneath weeping willows draped in calcified rot."
  - **LOCAL_SURROUNDINGS (4 tiles):** The Drowned Clearings
    - *Lore Context:* "New neighboring biome appeared: A forsaken expanse of stagnant oxbows where the water runs black with necromantic ash, unhallowed corpse-candles burn in perpetual fog, and restless spirits wail beneath weeping willows draped in calcified rot."
- **External Ingress & Connected Destinations:**
  - **Perimeter Approach:** None -> Wilderness Traversal
    - *Destination Context:* "Traversed only by desperate tomb-raiders or grim wardens from Eaveshold braving the necrotic vapors."

### World Relations & Material Flow
The rupture of Mor-Ghul's wards has sent shockwaves through the basin, forcing Eaveshold to transform into a heavily fortified frontier bastion against roving drowned legions. Timber cutting along the Sylvan Trace has ground to a halt as necrotic miasma poisons the hemlock groves.

### Architectural & Spatial Rationale
The ancient stone entryways have been blasted open by subterranean necrotic surges, shattering the cyclopean gate structure and corrupting the surrounding flora into ash and calcified scree. Decay has rotted the wooden boardwalk spans, while the inner chambers flare with violent death-fire.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ~~~~~~~~~~;;;&&&                            |    00: 0000000000000000
01: ~~~~~~~;;;;;&&&&                            |    01: 0000000000000000
02: ~~~~~;;######;;;                            |    02: 0000004444440000
03: ~~~;;;##B...####                            |    03: 0000004444440555
04: ~~;;;##......#A#                            |    04: 0000004444440555
05: ~~;;;##../##...#                            |    05: 0000004444440555
06: ~;;;+WWW+##/...#                            |    06: 0002222222225555
07: ~;;;+;;;+/.....#                            |    07: 0002222223333330
08: &;;;+;;;+#F.S..#                            |    08: 0002222223333330
09: &&:++WWW+#.....#                            |    09: 1112222223333330
10: &&::&;;;:.G./###                            |    10: 1111222223333330
11: &:..:&;;T......#                            |    11: 1111111111111110
12: &:..:&&&+......#                            |    12: 1111111111111110
13: &:..:&&&+......#                            |    13: 1111111111111110
14: &&&&&&&&+:......                            |    14: 1111111111111110
15: &&&&&&&&+:......                            |    15: 1111111111111110
```

### Features Registry
- ID 'cyclopean_breach': **The Shattered Cyclopean Gate** ['G'] (ingress)
  - Position: [X: 10, Y: 10]
  - Lore: Massive ashlar gateposts blasted apart by necrotic surges, opening a gaping breach into the inner crypt vaults.
- ID 'outer_threshold': **Shattered Threshold Arch** ['T'] (threshold)
  - Position: [X: 08, Y: 11]
  - Lore: A cracked stone archway dripping with calcified ash and lingering necrotic mist, marking the boundary to the unsealed tombs.
- ID 'oxbow_boardwalk': **Rotting Ash Boardwalk** ['W'] (bridge)
  - Footprint: 6 tiles ([X: 05..07, Y: 06..09])
  - Lore: Charred and decaying timber spans half-sunk into black, ash-choked shallows.
- ID 'sarcophagus': **Ruptured Sarcophagus of Mor-Ghul** ['S'] (sarcophagus)
  - Position: [X: 12, Y: 08]
  - Lore: The cyclopean stone lid has been cast aside, revealing the dark void from which Lord Mor-Ghul commands his risen legions.
- ID 'spirit_altar': **Altar of the Wight-Lord** ['A'] (altar)
  - Position: [X: 14, Y: 04]
  - Lore: A towering monolithic slab pulsing with cold necrotic aura, surrounded by bone-dust and dark offerings.
- ID 'votive_basin': **Overflowing Necrotic Basin** ['B'] (basin)
  - Position: [X: 08, Y: 03]
  - Lore: A stone basin overflowing with black necrotic silt and swirling corpse-candles.
- ID 'witch_brazier': **Flaring Death-Fire Brazier** ['F'] (brazier)
  - Position: [X: 10, Y: 08]
  - Lore: An ancient iron brazier roaring with violent green-white death-fire that casts long, twisted shadows.

### Districts Registry
- ID '0': **Frontier Buffer & Drowned Margins** (buffer)
  - Lore: Poisoned black oxbow waters of the Drowned Clearings and withered timberlands of the Greenwood Vault choked with calcified rot.
- ID '1': **Ash-Choked Approach** (antechamber)
  - Lore: A withered trail of calcified roots and necrotic ash winding toward the shattered gates of the necropolis.
- ID '2': **Ruined Wight-Courtyard** (hall)
  - Lore: A half-submerged plaza of black silt and rotting boardwalks where drowned legionaries gather under death-fog.
- ID '3': **Vaults of the Wight-Lord** (crypt)
  - Lore: Shattered cyclopean stone chambers where unsealed sarcophagi radiate intense, bone-chilling cold.
- ID '4': **Unsealed Necrotic Catacombs** (catacomb)
  - Lore: Flooded lower passages overflowing with black ash-silt, unhallowed corpse-candles, and ancient votive offerings.
- ID '5': **Sanctum of Mor-Ghul** (sanctum)
  - Lore: The high obsidian chamber where the primeval spirit altar burns with unholy death-fire above the waterline.
