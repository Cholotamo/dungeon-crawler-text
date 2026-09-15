# Locale Map: Aethelford
- **Feature ID:** `aethelford`
- **Classification:** Settlement
- **Scale Profile:** Large / Urban River City & Bastion. Urban Densification & Riverside Fortification.
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** The sovereign river-city of Aethelford stands as the heavily fortified heart of the Silver Channel, channeling vital supplies from the western crofts and Dun Kestrel's chalk quarries to the besieged frontier at Eaveshold while watching nervously over the necrotic taint creeping up from the southern oxbows.
- **Host Region:** Aethelford Crofts (Cleared_Land)
  - *Host Region Lore:* "Broad river-silt barley fields, flax plots, and rye crofts terraced along the fertile bends of the Silver Channel, feeding the bustling markets of Aethelford and supplying military rations to Eaveshold."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Greenwood Vault (Forest)
    - *Lore Context:* "The ancient hemlock canopy cleaved along its southern boundary by expanding timber-haulers and limestone roads, now shadowed by cold necrotic vapors drifting through the eastern timberlands."
  - **SOUTH & EAST BORDER:** The Silver Channel & The Drowned Clearings (River / Corrupted Water)
    - *Lore Context:* "A majestic river channel whose southern oxbows have been corrupted by the eruption of Mor-Ghul, turning into poisoned black waters choked with necrotic silt, where unhallowed corpse-candles flare in the night."
  - **WEST BORDERS:** Transition into host region (Aethelford Crofts — Cleared_Land).
    - *Lore Context:* "Broad, terraced barley fields and flax plots yielding high-volume harvests for the river-city and highland allies."
- **External Ingress & Connected Destinations:**
  - **NORTH Approach:** The Downs-Way (Road) -> Leads toward Dun Kestrel (Settlement)
    - *Road Lore:* "A heavily traveled, crushed-limestone track hacked through the Greenwood Vault, linking Dun Kestrel's white-chalk citadel directly to Aethelford's north gate."
    - *Destination Context:* "Dun Kestrel (Citadel): Elevated from a pastoral hill-fort into the sovereign stone citadel of the western highlands. Encircled by cyclopean chalk-ashlar ramparts, high beacon towers, and cavernous grain vaults, Dun Kestrel now commands the sheep-walks, quarries, and reclaimed polders of the downs as an equal rival to the River Throne."
  - **EAST Approach:** The Silver Span (Road) -> Leads toward The Sylvan Trace (Road)
    - *Road Lore:* "A monumental timber-and-stone viaduct anchored on sunken ashlar piers, bridging the Silver Channel to connect Aethelford's river market directly with the Sylvan Trace."
    - *Destination Context:* "A heavily fortified corduroy road of felled hemlock logs and crushed shale driven east through the Greenwood Vault to supply the barricaded watch at Eaveshold."

### World Relations & Material Flow
Aethelford channels processed timber, river salmon, and surplus grain along the Silver Span to sustain the frontline garrison at Eaveshold, while receiving white chalk-stone, wool, and heavy armaments from Dun Kestrel via the Downs-Way. As necrotic corruption spreads across the lower basin from Mor-Ghul, Aethelford acts as the premier logistical lifeline and fortified bastion for the entire central river valley.

### Architectural & Spatial Rationale
In response to the necrotic corruption erupting in the southern Drowned Clearings, Aethelford reinforced its riverfront quays with stone battlements, watch-posts, and iron-reinforced piers. The north gatehouse and river citadel were retrofitted with white chalk-ashlar masonry imported from Dun Kestrel to withstand potential sieges and secure uninterrupted grain shipments across the Silver Span. In Epoch 4, the site experienced architectural stagnancy: No recorded developments, environmental shifts, or infrastructure changes occurred for Aethelford in Epoch 4. In Epoch 5, the site experienced architectural stagnancy: No recorded developments, environmental shifts, or infrastructure changes occurred for Aethelford in Epoch 5.

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
  - Lore: Vast multi-story stone silos storing harvested barley, rye, and dried provisions from the western crofts to supply river trade and eastern posts.
- ID 'north_gate': **Downs-Way Chalk-Ashlar Gatehouse** ['/'] (gate)
  - Position: [X: 08, Y: 02]
  - Lore: A fortified gatehouse upgraded with white chalk-ashlar masonry from Dun Kestrel, guarding the northern ingress along the Downs-Way.
- ID 'river_citadel': **Aethelford Sovereign River-Citadel** ['C'] (keep)
  - Position: [X: 08, Y: 05]
  - Lore: A lordly ashlar-and-timber citadel housing the sovereign council chamber, armory, and high command overlooking the river crossing.
- ID 'river_wharf': **Sovereign River Quays & Docks** ['D'] (docks)
  - Position: [X: 07, Y: 10]
  - Lore: Paved stone quays and heavy log piers fitted with cranes, mooring posts, and defensive breastworks for river barges and timber rafts.
- ID 'sawmill': **Greenwood Sawmill & Timber Yard** ['S'] (smithy)
  - Position: [X: 05, Y: 06]
  - Lore: An expanded water-powered timber mill processing massive hemlock logs hauled from the forest for city building and export to Eaveshold.
- ID 'silver_span': **The Silver Span Viaduct** ['='] (bridge)
  - Footprint: 6 tiles ([X: 10..15, Y: 09..09])
  - Lore: A colossal viaduct resting on sunken stone piers and heavy oak pilings, spanning the Silver Channel to connect Aethelford with the Sylvan Trace.

### Districts Registry
- ID '0': **Frontier Buffer & Wilderness** (buffer)
  - Lore: The dense hemlock canopy of the Greenwood Vault to the north and the churning, necrotic-tainted currents of the Silver Channel to the south and east.
- ID '1': **Citadel & Sovereign Wards** (residential)
  - Lore: The fortified urban heart of Aethelford, boasting high stone masonry, paved limestone plazas, administrative halls, and dense merchant lodgings.
- ID '2': **Silver Channel Quays & Port** (harbor)
  - Lore: Expanded ashlar quays, river landings, and crane-rigged wharves where timber rafts, grain barges, and rivercraft dock.
- ID '3': **Downs-Way Trailhead** (square)
  - Lore: The north gate approach where crushed limestone from the Undulating Downs meets Aethelford's fortified gatehouse.
- ID '4': **Silver-Silt Crofts** (farmland)
  - Lore: Broad, terraced river-silt crofts, flax fields, and barley strips feeding the expanding urban populace and supplying military garrisons.
- ID '5': **The Silver Span Viaduct** (bridge)
  - Lore: A monumental timber-and-stone viaduct anchored on sunken ashlar piers, carrying road traffic across the Silver Channel toward the Sylvan Trace and Eaveshold.
