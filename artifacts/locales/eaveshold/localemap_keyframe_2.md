# Locale Map: Eaveshold
- **Feature ID:** `eaveshold`
- **Classification:** Settlement
- **Scale Profile:** Settlement turned into big city (Small / Compact -> Large / Urban). Urban Densification & Fortification.
- **Registered Features:** 8

### Geographic & World Context
- **Overview Lore:** Elevated from a beleaguered frontier stockade into a sovereign marcher citadel. Shielded behind the rushing waters of the Ward-Fosse canal, Eaveshold's towering granite ramparts, ballista turrets, and consecrated beacon-fires stand as the unyielding shield of the Greenwood against the horrors of Mor-Ghul.
- **Host Region:** The Greenwood Vault (Forest)
  - *Host Region Lore:* "Though ancient shadows linger beneath the towering hemlocks, the dread of the creeping blight is held at bay by the rushing torrent of the Ward-Fosse, while mortal crofts and stone battlements at Eaveshold assert dominion over the eastern timberlands."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Northern Ribs (Mountains)
    - *Lore Context:* "The desolate granite precipices and alpine screes of the southern ribs now echo with the clang of pickaxes and the smoke of charcoal bloomery furnaces, as miners from Dun Kestrel delve deep into rich veins of magnetite iron."
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
Eaveshold stands as the dominant bastion of the Greenwood, supplied with magnetite iron from Ironcrest via the Northern Ribs, grain from its own Marcher Garths, and troop reinforcements from Aethelford across the Silver Span.

### Architectural & Spatial Rationale
With the diversion of the Silver Channel into the Ward-Fosse, Eaveshold expanded its timber palisades into massive granite ashlar ramparts. The fortress footprint was broadened to encompass an expanded armory, a high ballista turret, a granary to store harvests from the newly cleared Marcher Garths, and a consecrated beacon tower.

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
  - Lore: A expanded forge complex smelting magnetite iron into armor, ballista bolts, and siege weaponry.
- ID 'marcher_granary': **Marcher Garths Granary** ['B'] (granary)
  - Footprint: 2 tiles ([X: 09..10, Y: 08..08])
  - Lore: A fortified stone granary built to store grain yields harvested from the eastern Garths, ensuring self-sufficiency during sieges.
- ID 'mire_sentinel_tower': **Grand Ballista Bastion & Beacon Tower** ['W'] (watchtower)
  - Footprint: 2 tiles ([X: 04..05, Y: 04..04])
  - Lore: An elevated granite artillery tower equipped with long-range repeating ballistas and a consecrated beacon fire that pierces death-fogs.
- ID 'pioneer_hearth': **High Captain's Hearth & Hall** ['H'] (hearth)
  - Position: [X: 04, Y: 05]
  - Lore: A vaulted stone hearth-hall where commanders plan border defense strategies and maintain an ever-burning warding flame.
- ID 'sylvan_gate': **Ironclad West Gatehouse** ['G'] (gate)
  - Position: [X: 03, Y: 07]
  - Lore: A formidable twin-towered stone gatehouse outfitted with heavy iron portcullises, guarding the entrance from the Sylvan Trace.
- ID 'sylvan_saw_pit': **Masonry Yard & Defense Workshop** ['S'] (crafts)
  - Footprint: 2 tiles ([X: 09..10, Y: 09..09])
  - Lore: A busy stone-cutters' yard dressing granite blocks from the Northern Ribs and fabricating heavy timber hoardings.
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
