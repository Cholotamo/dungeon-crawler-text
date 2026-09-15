# Locale Map: Dun Kestrel
- **Feature ID:** `dun_kestrel`
- **Classification:** Settlement
- **Scale Profile:** Large Urban Citadel & Highland Capital.
- **Registered Features:** 8

### Geographic & World Context
- **Overview Lore:** As one of the twin sovereign citadels of the highland realm alongside Ironcrest, Dun Kestrel has expanded its ashlar fortifications, heavy iron foundries, and supply yards, serving as the high administrative, agricultural, and martial capital of the chalklands.
- **Host Region:** The Undulating Downs (Hills)
  - *Host Region Lore:* "Anchored between the twin sovereign citadels of Dun Kestrel and Ironcrest, the high rolling chalklands have transformed into a fortified highland realm of martial discipline, deep limestone quarries, terraced barley slopes, and rumbling iron-wains traversing the paved trace."
- **Surrounding Perimeters:**
  - **ALL BORDERS:** Transition into host region (The Undulating Downs — Hills).
    - *Lore Context:* "Anchored between the twin sovereign citadels of Dun Kestrel and Ironcrest, the high rolling chalklands have transformed into a fortified highland realm of martial discipline, deep limestone quarries, terraced barley slopes, and rumbling iron-wains traversing the paved trace."
- **External Ingress & Connected Destinations:**
  - **WEST Approach:** The Hollow-Trace (Road) -> Leads toward The Hollow Polders (Waterworks)
    - *Road Lore:* "A graded chalk-gravel road descending the steep western spurs of Dun Kestrel to connect the mountain citadel with the hydraulic ditches and barley fields of the Hollow Polders."
    - *Destination Context:* "The Hollow Polders (Waterworks): A vast hydraulic grid of drainage trenches, sluices, and dykes where reclaimed peat-bogs produce abundant barley and grain for the highland garrisons."
  - **EAST Approach:** The Downs-Way (Road) -> Leads toward Aethelford (City)
    - *Road Lore:* "A heavily traveled beaten dirt and crushed-limestone track linking Dun Kestrel's east gate directly to the bustling river markets and ashlar quays of Aethelford."
    - *Destination Context:* "Aethelford (City): The sovereign river-city of the Silver Channel, boasting stone quays, granaries, and a fortified timber-and-stone citadel guarding the crossing into the eastern forest."
  - **NORTH Approach:** The Iron-Trace (Road) -> Leads toward Ironcrest (Citadel)
    - *Road Lore:* "A heavily paved causeway of basalt and crushed limestone ballast, carrying continuous heavy iron-wain convoys between the twin citadels of Dun Kestrel and Ironcrest."
    - *Destination Context:* "Ironcrest (Citadel): Elevated from a frontier mining redoubt into a sovereign mountain fortress-citadel. Crowned with cyclopean slate ramparts, soaring blast furnaces, and deep labyrinthine adits delved into the roots of the Northern Ribs, Ironcrest now stands as the supreme industrial and martial bastion of the highland clans, supplying cold-forged magnetite steel to the entire realm."

### World Relations & Material Flow
Dun Kestrel receives continuous heavy shipments of dark slate slabs and raw magnetite ore from Ironcrest along the Iron-Trace, forging masterwork steel weaponry and plate armor while distributing polder barley, cut limestone, and finished ironware down the Downs-Way to Aethelford and Confluence Watch.

### Architectural & Spatial Rationale
To support its role as the administrative and agricultural capital alongside Ironcrest's industrial powerhouse, Dun Kestrel paved key interior thoroughfares with dressed flagstone, expanded its storage depots and iron foundries, and fortified its northern and eastern gatehouses with heavy stone bastions to manage non-stop wain traffic.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^,^,,,^+,,,,,,,,                            |    00: 0000006600000000
01: ,,,,,^+,,,,,,,,,                            |    01: 0000006600000000
02: ,,,####N###,,,,,                            |    02: 0001111111100000
03: ,,,#.B.+.S.#,:|:                            |    03: 0001111111100330
04: ^,,#.+..+..#,:|:                            |    04: 0001111111100330
05: ,,,#.V.#...+,:|:                            |    05: 0001111111100330
06: ++++W...+...+:::                            |    06: 5555111111100330
07: ++++#...+...E+++                            |    07: 5555111111144444
08: ^,,#.C.#.G.+::::                            |    08: 0002222222200330
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
  - Lore: Expanded into heavy blast foundries processing magnetite iron ore from Ironcrest into dark steel weaponry and defensive armor plating.
- ID 'east_gatehouse': **Downs-Way East Gate** ['E'] (gatehouse)
  - Position: [X: 12, Y: 07]
  - Lore: The monumental stone entrance opening onto the Downs-Way, equipped with iron portcullises and guard barracks.
- ID 'grain_vaults': **Highland Grain & Polder Vaults** ['V'] (granary)
  - Position: [X: 05, Y: 05]
  - Lore: Deep stone subterranean vaults storing thousands of bushels of barley harvested from the Hollow Polders to feed the highland garrisons.
- ID 'high_beacon': **High Chalk Beacon Tower** ['B'] (hearth)
  - Position: [X: 05, Y: 03]
  - Lore: A towering stone beacon kiln built over the ancient chalk hearth, burning continuous coal-and-hardwood fires to signal night supply trains along the Iron-Trace.
- ID 'limestone_quarry': **Chalk-Stone Supply Depot** ['G'] (vault)
  - Position: [X: 09, Y: 08]
  - Lore: Heavy stone storehouses and dressed ashlar yards holding cut limestone blocks, dark slate slabs, and raw magnetite ore from Ironcrest.
- ID 'north_gatehouse': **Iron-Trace North Gate** ['N'] (gatehouse)
  - Position: [X: 07, Y: 02]
  - Lore: A massive ashlar gatehouse flanked by twin beacon turrets, guarding the steep northern ascent of the Iron-Trace causeway leading to Ironcrest.
- ID 'thanes_citadel': **High Thane's Citadel** ['C'] (keep)
  - Position: [X: 05, Y: 08]
  - Lore: A grand ashlar-walled citadel crowning the highest bluff, co-sovereign seat of the highland realm reinforced with dark slate roofing and iron-plated gates.
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
- ID '6': **Iron-Trace Approach** (crafts)
  - Lore: The steep northern causeway approach connecting Dun Kestrel to the mountain fortress-citadel of Ironcrest.
