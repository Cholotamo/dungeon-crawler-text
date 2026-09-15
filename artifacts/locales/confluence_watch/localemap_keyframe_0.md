# Locale Map: Confluence Watch
- **Feature ID:** `confluence_watch`
- **Classification:** Settlement
- **Scale Profile:** Small / Compact (Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.)
- **Registered Features:** 5

### Geographic & World Context
- **Overview Lore:** A heavily fortified river-bastion and naval station commanding the junction of the Silver Channel and Jade River, enforcing quarantine against Mor-Ghul horrors while exporting felled river-trunks.
- **Host Region:** The Greenwood Vault (Forest)
  - *Host Region Lore:* "The ancient hemlock canopy remains dense and primeval, but its shadowed solitude is now bookended by mortal steel—anchored in the northeast by the battlements of Eaveshold and in the deep south by the water-gates of Confluence Watch, whose lumbermen fell giant river-trunks to supply the shipwrights of the lower basin."
- **Surrounding Perimeters:**
  - **NORTH BORDER:** The Silver Channel (River)
    - *Lore Context:* "A majestic, half-league-wide river carrying mountain runoff through a fractured piedmont of rolling hills into the primeval basin."
  - **EAST BORDER:** The Silent Meeting (River)
    - *Lore Context:* "The primeval solitude of the great sister-confluence has yielded to the ring of iron and the splash of heavy oars; armed river-galleys and stone water-gates from Confluence Watch now patrol the swirling silver and jade eddies, maintaining vigilant quarantine against the poisoned runoff and wandering wights of the northern marshes."
  - **SOUTH & WEST BORDERS:** Transition into host region (The Greenwood Vault — Forest).
    - *Lore Context:* "The ancient hemlock canopy remains dense and primeval, but its shadowed solitude is now bookended by mortal steel—anchored in the northeast by the battlements of Eaveshold and in the deep south by the water-gates of Confluence Watch, whose lumbermen fell giant river-trunks to supply the shipwrights of the lower basin."
- **External Ingress & Connected Destinations:**
  - **Perimeter Approach:** None -> Wilderness Traversal
    - *Destination Context:* "None. (Isolated wilderness site; entry is via local terrain traversal)."

### World Relations & Material Flow
Confluence Watch receives magnetite armor and heavy ironwork from Ironcrest and veteran river-marine garrisons from Aethelford. In return, it secures the riverways for downriver trade and exports giant hemlock river-trunks harvested from the Greenwood Vault to southern shipbuilders.

### Architectural & Spatial Rationale
The outpost is situated on the elevated peninsula tip to maximize sightlines across both river branches. Its northern bastion wall and magnetite keep shield the interior from riverborne wights, while the open southern yard provides access for logging crews entering from the surrounding primeval forest.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ~~~~~~~~~~~~~~~~                            |    00: 0000000000000000
01: ~~~~~~~~~~~~~~~;                            |    01: 0000000000000000
02: ;;;;;;;;;;;;;;;~                            |    02: 0000000000000000
03: &&########;~;~;~                            |    03: 0033333333330000
04: &,#........#~;~;                            |    04: 0033333333330000
05: &/#..KK....#DDDD                            |    05: 0031111133332222
06: &,#..KK....#DDDD                            |    06: 0031111133332222
07: &,#..++++..#DDDD                            |    07: 0033333333332222
08: &,#####/####;;;~                            |    08: 0033333333330000
09: &,,++++++...,;,~                            |    09: 0004444444440000
10: &,,SS::.MMMM,;,~                            |    10: 0004444444440000
11: &,,SS::.MMMM,;,~                            |    11: 0004444444440000
12: &,,::HH.....,;,~                            |    12: 0005555555550000
13: &&,;,;,;,;,;,;,~                            |    13: 0000000000000000
14: ~~~~~~~~~~~~~~~~                            |    14: 0000000000000000
15: ~~~~~~~~~~~~~~~~                            |    15: 0000000000000000
```

### Features Registry
- ID 'lumber_staging': **River-Trunk Lumber Yard** ['M'] (granary)
  - Footprint: 8 tiles ([X: 08..11, Y: 10..11])
  - Lore: Staging racks holding massive primeval hemlock logs harvested from the Greenwood Vault, prepared for downstream raft-transport to southern shipwrights.
- ID 'magnetite_keep': **Magnetite Command Keep** ['K'] (keep)
  - Footprint: 4 tiles ([X: 05..06, Y: 05..06])
  - Lore: A heavily reinforced two-story bastion clad in dark Ironcrest magnetite plates, serving as the strategic command post for river quarantine.
- ID 'marine_armory': **Aethelford Marine Armory** ['S'] (smithy)
  - Footprint: 4 tiles ([X: 03..04, Y: 10..11])
  - Lore: A bustling smithy and armory dedicated to repairing magnetite marine plate and forging heavy ballista bolts from imported Ironcrest iron.
- ID 'signal_hearth': **Vigilance Signal Hearth** ['H'] (hearth)
  - Footprint: 2 tiles ([X: 05..06, Y: 12..12])
  - Lore: A massive stone fire-pit kept primed with pitch-soaked hemlock to signal river alerts north to Eaveshold.
- ID 'water_docks': **Confluence Pier & Water Gate** ['D'] (docks)
  - Footprint: 12 tiles ([X: 12..15, Y: 05..07])
  - Lore: Heavy timber boardwalks and iron-bound pilings anchored into the Silver Channel for mooring heavily armed river-galleys.

### Districts Registry
- ID '0': **Frontier Buffer & Waterway** (buffer)
  - Lore: The turbulent convergence of the Silver Channel and Jade River, framed by the primeval hemlock forest of the Greenwood Vault.
- ID '1': **Magnetite Redoubt** (keep)
  - Lore: A formidable stone and iron command bastion reinforced with Ironcrest magnetite, housing garrison commanders and heavy siege ordnance.
- ID '2': **Iron-Grated Confluence Docks** (harbor)
  - Lore: Heavy wooden piers and iron-grated slipways extending into the confluence to launch armed river-galleys and enforce quarantine.
- ID '3': **Inner Garrison Courtyard** (square)
  - Lore: A compact flagstone and earth yard surrounded by timber-and-stone palisades where Aethelford river-marines drill and stand guard.
- ID '4': **Timber & Marine Logistics Yard** (crafts)
  - Lore: An open working yard where felled river-trunks are dressed for shipment to southern shipwrights and marine armor is maintained.
- ID '5': **Vigilance Signal Battery** (sanctum)
  - Lore: An elevated southern watch platform equipped with a signal hearth to flash warning beacons north toward Eaveshold.
