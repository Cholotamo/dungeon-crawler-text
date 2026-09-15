# Locale Map: Eaveshold
- **Feature ID:** `eaveshold`
- **Classification:** Settlement
- **Scale Profile:** Small / Fortified Outpost (Barricaded forward bastion. Compact layout reinforced with flooded moat-ditches, iron-banded hemlock palisades, and elevated sentinel bastions to withstand necrotic miasma from the Blighted Mire.)
- **Registered Features:** 7

### Geographic & World Context
- **Overview Lore:** Transformed from a peaceful lumber camp into a desperate, heavily fortified forward bastion. Iron-banded oak palisades, moat-ditches, and watchful marsh-wardens maintain a harrowing vigil along the southern tree-line against the horrors drifting out of the Blighted Mire.
- **Host Region:** The Greenwood Vault (Forest)
  - *Host Region Lore:* "The ancient canopy of giant hemlocks and towering oaks is gripped by rising dread, as cold necrotic mists drift northward from the corrupted fens to claw at the sharpened palisades of Eaveshold."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Northern Ribs (Mountains)
    - *Lore Context:* "A jagged wall of grey gneiss, dark basalt, and folded slate tearing the sky into cloud ribbons, crowned with eternal snowpacks and paleoglaciers."
  - **SOUTH BORDER:** The Blighted Mire & Corrupted Fens
    - *Lore Context:* "A withered, ash-choked swamp oozing necrotic miasma from the unsealed crypts of Mor-Ghul, spewing restless spirits and drowned wights toward the southern tree-line."
  - **EAST & WEST BORDERS:** Transition into host region (The Greenwood Vault — Forest).
    - *Lore Context:* "An ancient expanse of hemlocks and oaks gripped by lingering necrotic vapors drifting north from the corrupted fens."
- **External Ingress & Connected Destinations:**
  - **WEST Approach:** The Sylvan Trace (Road) -> Leads toward The Silver Span (Bridge)
    - *Road Lore:* "A corduroy road of felled hemlock logs and crushed shale running east from the Silver Span, heavily patrolled by armed couriers supplying the bastion at Eaveshold."
    - *Destination Context:* "A monumental timber-and-stone viaduct resting on sunken ashlar piers, spanning the deep waters of the Silver Channel to link Aethelford with the untamed eastern forest."
  - **SOUTH Approach:** The Fen Sally Path (Path) -> Leads toward The Necropolis of Mor-Ghul (Ruin)
    - *Road Lore:* "A narrow corduroy causeway crossing the flooded moat-trench into the ash-choked southern buffer, used by marsh-wardens scouting the edge of the Blighted Mire."
    - *Destination Context:* "The shattered crypts of an ancient undead sovereign, projecting an aura of bone-chilling dread and spewing drowned wights northward."

### World Relations & Material Flow
Eaveshold now acts as a crucial defensive bulwark for the western heartlands, receiving iron, weapons, and seasoned troops via the Sylvan Trace from Aethelford while sending back intelligence on the movements of the undead horde emerging from Mor-Ghul.

### Architectural & Spatial Rationale
In response to the rupture of Mor-Ghul's crypts, Eaveshold was rapidly retrofitted into a barricaded bastion. A flooded moat-trench was dug along the southern perimeter, a southern sally port was cut through the fortified palisades, and internal saw pits were repurposed to fabricate spiked barricades.

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
10: ,,&####/#####&,,                            |    10: 0044444444440000
11: ;;;;;;MMM;;;;;;;                            |    11: 0044444444440000
12: ,,&&&&,+;;;,&&&&                            |    12: 0000000000000000
13: &&&&&&&&;;&&&&&&                            |    13: 0000000000000000
14: &&&&&&&&&&&&&&&&                            |    14: 0000000000000000
15: &&&&&&&&&&&&&&&&                            |    15: 0000000000000000
```

### Features Registry
- ID 'flooded_moat_trench': **Flooded Moat Trench & Causeway** ['M'] (keep)
  - Footprint: 3 tiles ([X: 06..08, Y: 11..11])
  - Lore: A broad ditch filled with stagnant marsh water surrounding the southern palisade, spanned by a narrow wooden causeway to deter necrotic wights.
- ID 'logging_smithy': **Bastion Forge & Smithy** ['K'] (smithy)
  - Footprint: 2 tiles ([X: 10..10, Y: 04..05])
  - Lore: A busy forge refitting woodcutters' axes into battle blades, hammering iron palisade straps, and forging iron gate-bars.
- ID 'mire_sentinel_tower': **Mire Sentinel Bastion** ['W'] (watchtower)
  - Footprint: 2 tiles ([X: 04..05, Y: 04..04])
  - Lore: An elevated oak-and-iron bastion outfitted with pitch cauldrons, heavy ballistas, and signal horns to alert the garrison of creeping death-fog.
- ID 'pioneer_hearth': **Warden's Vigil Hearth** ['H'] (hearth)
  - Position: [X: 04, Y: 05]
  - Lore: A stone-lined hearth where marsh wardens dry wet gear, brew hemlock-bark tonic, and maintain constant flame against necrotic chills.
- ID 'sylvan_gate': **Iron-Banded Sylvan Gate** ['G'] (gate)
  - Position: [X: 03, Y: 07]
  - Lore: Reinforced with heavy iron straps and oak baulks, this gate seals the western corduroy road against necrotic incursions.
- ID 'sylvan_saw_pit': **Defensive Saw Pit** ['S'] (smithy)
  - Footprint: 4 tiles ([X: 09..10, Y: 08..09])
  - Lore: Reconfigured from timber export to rapidly shape sharpened barricade stakes, moat revetments, and heavy palisade timbers.
- ID 'sylvan_trace_staging': **Garrison Staging Yard** ['T'] (market)
  - Footprint: 2 tiles ([X: 06..07, Y: 07..07])
  - Lore: The corduroy staging square where supply sleds from Aethelford unload grain, iron, and pitch while defense patrols assemble.

### Districts Registry
- ID '0': **Frontier Buffer & Necrotic Borderlands** (buffer)
  - Lore: Unzoned forest wilderness where creeping death-fog drifts from the Blighted Mire, bounded north by the Northern Ribs.
- ID '1': **The Staging Thoroughfare** (square)
  - Lore: The main corduroy thoroughfare and staging yard inside the outpost, heavily traversed by marsh wardens and defense supply wagons.
- ID '2': **Defensive Works & Saw Pits** (crafts)
  - Lore: Saw pits, tool smithies, and timber yards converted to mass-producing defensive barricades, iron-bound stakes, and siege barriers.
- ID '3': **Vigil & Warden Quarters** (residential)
  - Lore: Timber barracks and dugout shelters housing woodcutters, trackers, and marsh wardens stationed along the perilous border.
- ID '4': **Palisade Ramparts & Moat** (keep)
  - Lore: Iron-banded hemlock-log palisades, elevated sentinel bastions, and a flooded moat-trench guarding against necrotic incursions.
