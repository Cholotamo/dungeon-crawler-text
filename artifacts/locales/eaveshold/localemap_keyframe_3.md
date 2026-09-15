# Locale Map: Eaveshold
- **Feature ID:** `eaveshold`
- **Classification:** Settlement
- **Scale Profile:** Settlement turned into big city (Small / Compact -> Large / Urban). Urban Densification & Fortification.
- **Registered Features:** 8

### Geographic & World Context
- **Overview Lore:** Firmly established as the eastern anchor of the Greenwood Vault, Eaveshold's slate-roofed citadel and granite ashlar ramparts form an impregnable fortress. Supplied with high-grade magnetite steel from Ironcrest and timber from the southern fellings, the stronghold commands the eastern marches and enforces strict containment against Mor-Ghul.
- **Host Region:** The Greenwood Vault (Forest)
  - *Host Region Lore:* "The ancient hemlock canopy remains dense and primeval, but its shadowed solitude is now bookended by mortal steel—anchored in the northeast by the battlements of Eaveshold and in the deep south by the water-gates of Confluence Watch, whose lumbermen fell giant river-trunks to supply the shipwrights of the lower basin."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Northern Ribs (Mountains)
    - *Lore Context:* "The desolate alpine screes and towering granite crags now thunder day and night with the deep tremors of heavy excavation, blast furnaces, and cascading slag-sluices, as the newly elevated citadel of Ironcrest delves labyrinthine adits into the ancient mountain roots to harvest vast deposits of black magnetite iron and dark roofing slate."
  - **SOUTH BORDER:** The Ward-Fosse (Canal Moat & Blighted Mire)
    - *Lore Context:* "New neighboring biome appeared: A deep, rapid defensive diversion channel carved east from the Silver Channel along the southern perimeter of Eaveshold, creating an impassable barrier of rushing mountain water that repels necrotic spirits and isolates the Blighted Mire."
  - **EAST BORDER:** The Marcher Garths (Cropland)
    - *Lore Context:* "New neighboring biome appeared: Irrigated barley and rye fields carved from the eastern hemlock woods, fed by diversion ditches from the Ward-Fosse to nourish the garrison citadel of Eaveshold."
  - **WEST BORDER:** The Sylvan Trace & Greenwood Vault
    - *Lore Context:* "A heavily fortified highway running west toward the Silver Span, flanked by cleared timber reserves and stone watch-posts."
- **External Ingress & Connected Destinations:**
  - **WEST Approach:** The Sylvan Trace (Paved Highway) -> Leads toward The Silver Span (Bridge)
    - *Road Lore:* "A broad stone-flagged highway paved over the old corduroy road, transporting heavy shipments of iron, grain, and stone directly to the citadel's west gatehouse."
    - *Destination Context:* "A monumental timber-and-stone viaduct resting on sunken ashlar piers, spanning the deep waters of the Silver Channel to link Aethelford with the untamed eastern forest."
  - **SOUTH Approach:** The Ward-Fosse Span (Drawbridge) -> Leads toward The Necropolis of Mor-Ghul (Ruin)
    - *Road Lore:* "A heavily guarded stone-arch span and drawbridge crossing the raging waters of the Ward-Fosse, giving access to the southern wardens' watchposts at the edge of the Mire."
    - *Destination Context:* "The shattered crypts of an ancient undead sovereign, now held back by the consecrated running-water barrier of the Ward-Fosse."

### World Relations & Material Flow
Eaveshold serves as the northeastern anchor of the Greenwood alliance, receiving magnetite iron and dark roofing slate from Ironcrest via the Northern Ribs while sending grain and timber south to Confluence Watch and west to Aethelford.

### Architectural & Spatial Rationale
As Ironcrest expanded its production of dark roofing slate and high-potency magnetite iron, Eaveshold integrated slate cladding across its upper roofs and expanded its high armories. The stone ramparts and Ward-Fosse canal remain the ultimate defense, with paved thoroughfares supporting heavy iron-wains from the northern passes.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^^^^^^^^^^^^^^^^                            |    00: 0000000000000000
01: ^^^^:^:^^^:^^^^^                            |    01: 0000000000000000
02: ,,:,&,,,::::,,::                            |    02: 0000000055555555
03: ,,##########&:::                            |    03: 0044444444445555
04: ,,&#WW....K.#:::                            |    04: 0043333322245555
05: ,,&#H.++++K.#:::                            |    05: 0043333322245555
06: ,,&#..+..+..#:::                            |    06: 0043331111145555
07: +++G++TT+++/#:::                            |    07: 1111111111145555
08: ,,&#..+..BB.#:::                            |    08: 0043331122245555
09: ,,&#..+++SS.#:::                            |    09: 0043332222245555
10: ,,&####/#####:::                            |    10: 0044444444445555
11: ~~~~~~MMM~~~~~~~                            |    11: 0044444444440000
12: ;;;;;;;;M;;;;;;;                            |    12: 0044444444440000
13: ,,&&&&,+;;;,&&&&                            |    13: 0000000000000000
14: &&&&&&&&;;&&&&&&                            |    14: 0000000000000000
15: &&&&&&&&&&&&&&&&                            |    15: 0000000000000000
```

### Features Registry
- ID 'flooded_moat_trench': **The Ward-Fosse Canal & Stone Span** ['M'] (keep)
  - Footprint: 4 tiles ([X: 06..08, Y: 11..12])
  - Lore: A roaring canal diverted from the Silver Channel, creating an impassable running-water moat crossed by a defensible stone bridge.
- ID 'logging_smithy': **Citadel Arsenal & High Smithy** ['K'] (smithy)
  - Footprint: 2 tiles ([X: 10..10, Y: 04..05])
  - Lore: A massive slate-roofed forge complex processing steady shipments of magnetite steel from Ironcrest into heavy plate armor, ballista bolts, and reinforced portcullises.
- ID 'marcher_granary': **Marcher Garths Granary** ['B'] (granary)
  - Footprint: 2 tiles ([X: 09..10, Y: 08..08])
  - Lore: A heavily fortified slate-roofed stone granary storing harvests from the Marcher Garths to provision both the local garrison and river fleets bound for Confluence Watch.
- ID 'mire_sentinel_tower': **Grand Ballista Bastion & Beacon Tower** ['W'] (watchtower)
  - Footprint: 2 tiles ([X: 04..05, Y: 04..04])
  - Lore: An elevated slate-capped granite artillery tower equipped with long-range repeating ballistas and a consecrated beacon fire that pierces necrotic fogs along the Ward-Fosse.
- ID 'pioneer_hearth': **High Captain's Hearth & Hall** ['H'] (hearth)
  - Position: [X: 04, Y: 05]
  - Lore: A vaulted stone hearth-hall where commanders plan border defense strategies and maintain an ever-burning warding flame.
- ID 'sylvan_gate': **Ironclad West Gatehouse** ['G'] (gate)
  - Position: [X: 03, Y: 07]
  - Lore: A formidable twin-towered stone gatehouse outfitted with heavy iron portcullises, guarding the entrance from the Sylvan Trace.
- ID 'sylvan_saw_pit': **Masonry Yard & Defense Workshop** ['S'] (crafts)
  - Footprint: 2 tiles ([X: 09..10, Y: 09..09])
  - Lore: A high-capacity masonry and timber yard dressing granite blocks from the Northern Ribs and shaping hemlock beams for fortification upkeep.
- ID 'sylvan_trace_staging': **Grand Citadel Square** ['T'] (market)
  - Footprint: 2 tiles ([X: 06..07, Y: 07..07])
  - Lore: The central paved square where troops muster, supply caravans assemble, and courier riders arrive from Aethelford.

### Districts Registry
- ID '0': **Frontier Buffer & Necrotic Borderlands** (buffer)
  - Lore: Unzoned mountain scree and southern mire borders, held at bay by the rushing Ward-Fosse canal.
- ID '1': **The Grand Processional Thoroughfare** (square)
  - Lore: The main stone-flagged avenue and central parade ground, busy with marching patrols, heavy wagons, and courier messengers.
- ID '2': **Citadel Armory & Masonry Works** (crafts)
  - Lore: High-capacity forge complexes, ballista workshops, and masonry yards dedicated to maintaining the citadel's defenses.
- ID '3': **Garrison Citadel & High Captain's Keep** (residential)
  - Lore: Multi-story stone barracks, commander's quarters, and high hearth-halls housing the elite marcher wardens and knights.
- ID '4': **Cyclopean Ramparts & Ward-Fosse Canal** (keep)
  - Lore: Massive granite curtain walls, stone gatehouses, ballista bastions, and the deep running-water moat canal.
- ID '5': **The Marcher Garths** (farmland)
  - Lore: Irrigated barley and rye crofts carved from the eastern timberland, supplying grain directly to the citadel granaries.
