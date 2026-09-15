# Locale Map: Eaveshold
- **Feature ID:** `eaveshold`
- **Classification:** Settlement
- **Scale Profile:** Small / Compact (Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.)
- **Registered Features:** 6

### Geographic & World Context
- **Overview Lore:** A fortified palisade outpost and pioneer logging haven established at the eastern edge of the cleared trace, keeping vigil against the unquiet horrors of the southern mire.
- **Host Region:** The Greenwood Vault (Forest)
  - *Host Region Lore:* "An ancient expanse of moss-cloaked hemlocks and colossal oaks, now cleaved by the Silver Span and the corduroy logs of the Sylvan Trace as woodcutters push their fortified frontier into the eastern gloom."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Northern Ribs (Mountains)
    - *Lore Context:* "A jagged wall of grey gneiss, dark basalt, and folded slate tearing the sky into cloud ribbons, crowned with eternal snowpacks and paleoglaciers."
  - **SOUTH & EAST & WEST BORDERS:** Transition into host region (The Greenwood Vault — Forest).
    - *Lore Context:* "An ancient expanse of moss-cloaked hemlocks and colossal oaks, now cleaved by the Silver Span and the corduroy logs of the Sylvan Trace as woodcutters push their fortified frontier into the eastern gloom."
- **External Ingress & Connected Destinations:**
  - **WEST Approach:** The Sylvan Trace (Road) -> Leads toward The Silver Span (Bridge)
    - *Road Lore:* "A corduroy road of felled hemlock logs and crushed shale running east from the Silver Span, driven through the dense timber to supply the frontier watch at Eaveshold."
    - *Destination Context:* "A monumental timber-and-stone viaduct resting on sunken ashlar piers, spanning the deep waters of the Silver Channel to link Aethelford with the untamed eastern forest."

### World Relations & Material Flow
Eaveshold relies on the Sylvan Trace to ship raw hemlock and colossal oak timbers west toward the Silver Span and Aethelford, receiving grain, smithing iron, and fresh pioneer recruits in return.

### Architectural & Spatial Rationale
The settlement is built within a dense log palisade flanked by the impassable Northern Ribs to the north, with the Sylvan Trace entering directly through the West Gate to facilitate smooth timber transport while isolating timber yards and watch posts near the perimeter.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^^^^^^^^^^^^^^^^                            |    00: 0000000000000000
01: ^^^^:^:^^^:^^^^^                            |    01: 0000000000000000
02: ,,:,&,,,::,&,,,,                            |    02: 0000000000000000
03: ,,&##########&,,                            |    03: 0044444444440000
04: ,,&#WW....K.#&,,                            |    04: 0043333322240000
05: ,,&#H.++++K.#&,,                            |    05: 0043333322240000
06: ,,&#..+..+..#&,,                            |    06: 0043331111140000
07: +++G++TT+++/#&,,                            |    07: 1111111111140000
08: ,,&#..+..SS.#&,,                            |    08: 0043331122240000
09: ,,&#..+++SS.#&,,                            |    09: 0043332222240000
10: ,,&##########&,,                            |    10: 0044444444440000
11: ,,;&,,,,;,;;,,,,                            |    11: 0000000000000000
12: ,,&&&&,,;;;,&&&&                            |    12: 0000000000000000
13: &&&&&&&&;;&&&&&&                            |    13: 0000000000000000
14: &&&&&&&&&&&&&&&&                            |    14: 0000000000000000
15: &&&&&&&&&&&&&&&&                            |    15: 0000000000000000
```

### Features Registry
- ID 'logging_smithy': **Logging Tool Smithy** ['K'] (smithy)
  - Footprint: 2 tiles ([X: 10..10, Y: 04..05])
  - Lore: A rugged forge refitting crosscut saws, iron wedge collars, and draft-horse shoes using charcoal burned at the forest edge.
- ID 'mire_sentinel_tower': **Mire Sentinel Tower** ['W'] (watchtower)
  - Footprint: 2 tiles ([X: 04..05, Y: 04..04])
  - Lore: An elevated watchpost built from thick oak baulks, keeping constant vigil over the murky southern mire to signal impending threats.
- ID 'pioneer_hearth': **Pioneer Hearth** ['H'] (hearth)
  - Position: [X: 04, Y: 05]
  - Lore: A stone-lined hearth where woodsmen dry wet gear, share rations, and brew hemlock-bark tonic after clearing timber.
- ID 'sylvan_gate': **Sylvan Gate** ['G'] (gate)
  - Position: [X: 03, Y: 07]
  - Lore: A heavy double-timber portal made of bound hemlock trunks, marking the eastern terminus of the Sylvan Trace road.
- ID 'sylvan_saw_pit': **Sylvan Saw Pit** ['S'] (smithy)
  - Footprint: 4 tiles ([X: 09..10, Y: 08..09])
  - Lore: A subterranean pit flanked by timber gantries where woodcutters saw colossal hemlock trunks into beams bound for the Silver Span.
- ID 'sylvan_trace_staging': **Sylvan Trace Staging Yard** ['T'] (market)
  - Footprint: 2 tiles ([X: 06..07, Y: 07..07])
  - Lore: The corduroy timber yard where heavy timber sleds are loaded with felled logs and swapped for grain wagons arriving from Aethelford.

### Districts Registry
- ID '0': **Frontier Buffer & Greenwood Vault** (buffer)
  - Lore: Unzoned forest wilderness of moss-cloaked hemlocks and ancient oaks, bounded north by the jagged gneiss of the Northern Ribs.
- ID '1': **The Trace Way** (square)
  - Lore: The main corduroy thoroughfare and staging yard inside the outpost, aligned directly with the western approach from the Silver Span.
- ID '2': **The Timber Works** (crafts)
  - Lore: Saw pits, charcoal mounds, and tool smithies where woodcutters square giant timber trunks and repair logging hardware.
- ID '3': **Pioneer Ward** (residential)
  - Lore: Dugout timber shelters and common quarters housing woodcutters, trackers, and watchmen stationed at the edge of the wilderness.
- ID '4': **Palisade Ramparts** (keep)
  - Lore: Heavy hemlock-log palisades and elevated walkways guarding the pioneer haven against unquiet horrors from the southern mire.
