# Locale Map: Aethelford
- **Feature ID:** `aethelford`
- **Classification:** Settlement
- **Scale Profile:** Small / Compact (Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.)
- **Registered Features:** 5

### Geographic & World Context
- **Overview Lore:** A pioneer river-haven and timber stockade founded on the western bank of the Silver Channel, guarding the primeval crossing into the Greenwood Vault.
- **Host Region:** Aethelford Crofts (Cleared_Land)
  - *Host Region Lore:* "Tilled river-silt crofts and barley strips wrested from the ancient hemlocks of the Greenwood Vault, watered by the Silver Channel."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Greenwood Vault (Forest)
    - *Lore Context:* "An unbroken canopy of moss-cloaked hemlocks and broad oaks, newly pierced along the Silver Channel by mortal woodcutters and the tilled crofts of Aethelford."
  - **SOUTH & EAST BORDER:** The Silver Channel (River)
    - *Lore Context:* "A majestic, half-league-wide river carrying mountain runoff through a fractured piedmont of rolling hills into the primeval basin."
  - **WEST BORDERS:** Transition into host region (Aethelford Crofts — Cleared_Land).
    - *Lore Context:* "Tilled river-silt crofts and barley strips wrested from the ancient hemlocks of the Greenwood Vault, watered by the Silver Channel."
- **External Ingress & Connected Destinations:**
  - **NORTH Approach:** The Downs-Way (Road) -> Leads toward Dun Kestrel (Settlement)
    - *Road Lore:* "A beaten dirt and crushed-limestone track hacked through the western fringes of the Greenwood Vault, linking Dun Kestrel to the river wharf at Aethelford."
    - *Destination Context:* "A hill-clan redoubt perched atop the chalk bluffs of the Undulating Downs, encircled by timber palisades and pastoral sheep-runs."

### World Relations & Material Flow
Aethelford channels harvested hemlock timber up the Downs-Way to Dun Kestrel in exchange for pastoral wool, mutton, and chalk, while shipping surplus river-silt barley down the Silver Channel.

### Architectural & Spatial Rationale
The timber palisade guards the northern perimeter against primeval forest hazards, while the central thoroughfare connects the Downs-Way directly to the timber sawmill, barley granary, and southern river wharf.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: &&&,,,,&+&,,,,&&                            |    00: 0000000030000000
01: &&&,,,,&+&,,,,&&                            |    01: 0000000030000000
02: &&&,,###/###,,&&                            |    02: 0000001111100000
03: :::,,...|...,,,&                            |    03: 4440011111110000
04: :::,,...|...,,,&                            |    04: 4440011111110000
05: :::..+++H+++..,~                            |    05: 4441111111111100
06: :::..S.+++G+..,~                            |    06: 4441111111111100
07: :::..+++.+++..;;                            |    07: 4441111111111100
08: ,,,..+++.+++..;;                            |    08: 0001111111111100
09: ,,,..+++====~~;;                            |    09: 0001111122222000
10: ,,,,..+D.++=~~~~                            |    10: 0000111222220000
11: ,,,,:::::::~~~~~                            |    11: 0000444440000000
12: ;;;;:::::::~~~~~                            |    12: 0000444440000000
13: ~~~~~~~~~~~~~~~~                            |    13: 0000000000000000
14: ~~~~~~~~~~~~~~~~                            |    14: 0000000000000000
15: ~~~~~~~~~~~~~~~~                            |    15: 0000000000000000
```

### Features Registry
- ID 'granary': **Barley Granary & Store** ['G'] (granary)
  - Position: [X: 10, Y: 06]
  - Lore: A stilted timber storehouse holding dried river-silt barley and preserved winter rations harvested from local crofts.
- ID 'north_gate': **Downs-Way Gatehouse** ['/'] (gate)
  - Position: [X: 08, Y: 02]
  - Lore: A stout double-timber gate guarding the northern entry into Aethelford along the Downs-Way road from Dun Kestrel.
- ID 'pioneer_hearth': **Aethelford Pioneer Lodge** ['H'] (hearth)
  - Position: [X: 08, Y: 05]
  - Lore: A massive flagstone hearth and log hall serving as the settlement's meeting place, shelter, and central warmth.
- ID 'river_wharf': **Silver Channel Wharf** ['D'] (docks)
  - Position: [X: 07, Y: 10]
  - Lore: A reinforced log wharf and boardwalk facilitating river transport and trade with downriver settlements.
- ID 'sawmill': **Greenwood Sawmill & Yard** ['S'] (smithy)
  - Position: [X: 05, Y: 06]
  - Lore: A water-assisted pit saw mill that processes hemlock and oak timber felled in the Greenwood Vault for export and construction.

### Districts Registry
- ID '0': **Frontier Buffer & Wilderness** (buffer)
  - Lore: The dense hemlock canopy of the Greenwood Vault to the north and the wide, churning currents of the Silver Channel to the south and east.
- ID '1': **Stockade Enclosure & Yard** (residential)
  - Lore: A compact timber-walled haven housing pioneer lodgings, a central hearth fire, and timber processing yards.
- ID '2': **Silver Channel Wharf** (harbor)
  - Lore: A heavy oak river landing and timber pier where rafts, barges, and ferries dock along the Silver Channel.
- ID '3': **Downs-Way Trailhead** (square)
  - Lore: The north gate approach where crushed limestone from the Undulating Downs meets Aethelford's palisade.
- ID '4': **Silver-Silt Crofts** (farmland)
  - Lore: Fertile riverbank barley strips and tilled soil wrested from the forest edge.
