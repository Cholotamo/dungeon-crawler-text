# Locale Map: Aethelford
- **Feature ID:** `aethelford`
- **Classification:** Settlement
- **Scale Profile:** Settlement turned into big city (Small / Compact -> Large / Urban). Urban Densification & Fortification.
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** The sovereign river-city of the Silver Channel, boasting stone quays, granaries, and a fortified timber-and-stone citadel guarding the crossing into the eastern forest.
- **Host Region:** Aethelford Crofts (Cleared_Land)
  - *Host Region Lore:* "Broad river-silt barley fields, flax plots, and rye crofts terraced along the fertile bends of the Silver Channel, feeding the bustling markets of Aethelford."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Greenwood Vault (Forest)
    - *Lore Context:* "The ancient hemlock canopy cleaved along its southern boundary by expanding timber-haulers, stone quarries, and the fortified bastions of Aethelford."
  - **SOUTH & EAST BORDER:** The Silver Channel & The Drowned Clearings (River / Swamp)
    - *Lore Context:* "A majestic, half-league-wide river crossed by the monumental Silver Span viaduct; along the southern oxbows, green witch-fires flare across the mossy waters."
  - **WEST BORDERS:** Transition into host region (Aethelford Crofts — Cleared_Land).
    - *Lore Context:* "Broad river-silt barley fields, flax plots, and rye crofts terraced along the fertile bends of the Silver Channel, feeding the bustling markets of Aethelford."
- **External Ingress & Connected Destinations:**
  - **NORTH Approach:** The Downs-Way (Road) -> Leads toward Dun Kestrel (Settlement)
    - *Road Lore:* "A beaten dirt and crushed-limestone track hacked through the western fringes of the Greenwood Vault, linking Dun Kestrel to the river city of Aethelford."
    - *Destination Context:* "A hill-clan redoubt perched atop the chalk bluffs of the Undulating Downs, encircled by timber palisades and pastoral sheep-runs."
  - **EAST Approach:** The Silver Span (Road) -> Leads toward The Sylvan Trace (Road)
    - *Road Lore:* "New road established leading toward The Sylvan Trace (Road). A monumental timber-and-stone viaduct resting on sunken ashlar piers, spanning the deep waters of the Silver Channel to link Aethelford with the untamed eastern forest."
    - *Destination Context:* "Leads toward The Sylvan Trace (Road). A corduroy road of felled hemlock logs and crushed shale running east from the Silver Span, driven through the dense timber to supply the frontier watch at Eaveshold."

### World Relations & Material Flow
Aethelford channels processed timber, river salmon, and surplus barley along the Silver Span to the frontier garrison at Eaveshold, while receiving chalk, mutton, and wool from Dun Kestrel via the Downs-Way. As the sovereign capital of the central valleys, it regulates river trade and lumber transport across the entire Silver Channel.

### Architectural & Spatial Rationale
To protect its growing wealth and secure the new eastern river crossing, Aethelford upgraded its timber palisades to ashlar masonry walls and constructed a fortified river citadel at its heart. The new Silver Span viaduct bridges the river along the eastern flank, flanked by expanded stone granaries and quays to handle high-volume river barge traffic.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: &&&,,,,&+&,,,,&&                            |    00: 0000000030000000
01: &&&,,,,&+&,,,,&&                            |    01: 0000000030000000
02: &&&,,###/###,,&&                            |    02: 0000001111100000
03: :::,....+....,,&                            |    03: 4440111111110000
04: :::,....+....,,&                            |    04: 4440111111110000
05: :::..+++C+++..,~                            |    05: 4441111111111100
06: :::..S.+++G+..,~                            |    06: 4441111111111100
07: :::..+++.+++..;;                            |    07: 4441111111111100
08: ::::..++.+++..;;                            |    08: 4444111111111100
09: ::::..+++/======                            |    09: 4444111115555555
10: ,,,,..+D.++=~~~~                            |    10: 0000111222220000
11: ,,,,:::::::~~~~~                            |    11: 0000444440000000
12: ;;;;:::::::~~~~~                            |    12: 0000444440000000
13: ~~~~~~~~~~~~~~~~                            |    13: 0000000000000000
14: ~~~~~~~~~~~~~~~~                            |    14: 0000000000000000
15: ~~~~~~~~~~~~~~~~                            |    15: 0000000000000000
```

### Features Registry
- ID 'east_gate': **Silver Span Gatehouse** ['/'] (gate)
  - Position: [X: 09, Y: 09]
  - Lore: A fortified barbican and toll station guarding the western abutment of the Silver Span viaduct.
- ID 'granary': **High Ashlar Granary Vaults** ['G'] (granary)
  - Position: [X: 10, Y: 06]
  - Lore: Vast multi-story stone silos storing harvested barley, rye, and dried provisions from the western crofts.
- ID 'north_gate': **Downs-Way Stone Gatehouse** ['/'] (gate)
  - Position: [X: 08, Y: 02]
  - Lore: A fortified ashlar stone gatehouse and portcullis guarding the northern entry along the Downs-Way road from Dun Kestrel.
- ID 'river_citadel': **Aethelford River-Citadel** ['C'] (keep)
  - Position: [X: 08, Y: 05]
  - Lore: A lordly timber-and-stone citadel housing the sovereign council chamber, armory, and high hearth overlooking the river crossing.
- ID 'river_wharf': **Sovereign River Quays & Docks** ['D'] (docks)
  - Position: [X: 07, Y: 10]
  - Lore: Paved stone quays and heavy log piers fitted with cranes and mooring posts for river barges and timber rafts.
- ID 'sawmill': **Greenwood Sawmill & Timber Yard** ['S'] (smithy)
  - Position: [X: 05, Y: 06]
  - Lore: An expanded water-powered timber mill processing massive hemlock logs hauled from the forest for city building and export.
- ID 'silver_span': **The Silver Span Viaduct** ['='] (bridge)
  - Footprint: 6 tiles ([X: 10..15, Y: 09..09])
  - Lore: A colossal viaduct resting on sunken stone piers and heavy oak pilings, spanning the Silver Channel to connect Aethelford with the Sylvan Trace.

### Districts Registry
- ID '0': **Frontier Buffer & Wilderness** (buffer)
  - Lore: The dense hemlock canopy of the Greenwood Vault to the north and the churning currents of the Silver Channel to the south and east.
- ID '1': **Citadel & Sovereign Wards** (residential)
  - Lore: The fortified urban heart of Aethelford, boasting high stone masonry, paved limestone plazas, administrative halls, and dense merchant lodgings.
- ID '2': **Silver Channel Quays & Port** (harbor)
  - Lore: Expanded ashlar quays, river landings, and crane-rigged wharves where timber rafts, grain barges, and rivercraft dock.
- ID '3': **Downs-Way Trailhead** (square)
  - Lore: The north gate approach where crushed limestone from the Undulating Downs meets Aethelford's fortified gatehouse.
- ID '4': **Silver-Silt Crofts** (farmland)
  - Lore: Broad, terraced river-silt crofts, flax fields, and barley strips feeding the expanding urban populace.
- ID '5': **The Silver Span Viaduct** (bridge)
  - Lore: A monumental timber-and-stone viaduct anchored on sunken ashlar piers, carrying road traffic across the Silver Channel toward the Sylvan Trace.
