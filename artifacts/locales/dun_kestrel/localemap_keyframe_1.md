# Locale Map: Dun Kestrel
- **Feature ID:** `dun_kestrel`
- **Classification:** Settlement
- **Scale Profile:** Small / Compact (Fledgling cluster. Small structural footprint with a high proportion of surrounding natural terrain, open yards, and frontier buffer.)
- **Registered Features:** 5

### Geographic & World Context
- **Overview Lore:** A prospering hill-clan redoubt perched atop the chalk bluffs of the Undulating Downs, serving as a vital wool and limestone supplier to the sovereign river-city of Aethelford.
- **Host Region:** The Undulating Downs (Hills)
  - *Host Region Lore:* "Vast rolling hills of wild rye and fescue interrupted by craggy limestone bluffs, now echoing with the horn-calls of pastoral hill-clans and the hearth-smoke of Dun Kestrel."
- **Surrounding Perimeters:**
  - **ALL BORDERS:** Transition into host region (The Undulating Downs — Hills).
    - *Lore Context:* "Vast rolling hills of wild rye and fescue interrupted by craggy limestone bluffs, now echoing with the horn-calls of pastoral hill-clans and the hearth-smoke of Dun Kestrel."
- **External Ingress & Connected Destinations:**
  - **EAST Approach:** The Downs-Way (Road) -> Leads toward Aethelford (City)
    - *Road Lore:* "A heavily traveled beaten dirt and crushed-limestone track linking Dun Kestrel's east gate directly to the bustling river markets and ashlar quays of Aethelford."
    - *Destination Context:* "Aethelford (City): The sovereign river-city of the Silver Channel, boasting stone quays, granaries, and a fortified timber-and-stone citadel guarding the crossing into the eastern forest."

### World Relations & Material Flow
Dun Kestrel exports high-grade wool bales, salted mutton, and quarried limestone along the Downs-Way to Aethelford, receiving forged steel tools, hemlock timber, and river delicacies from the sovereign city.

### Architectural & Spatial Rationale
The hill-fort retains its elevated timber palisade and central chalk hearth, with its east gate opening directly onto the Downs-Way to facilitate heavy wool wagon and mule trains trading with Aethelford.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ^,^,,,^,,,,,,,,,                            |    00: 0000000000000000
01: ,,,,,^,,,,,,,,,,                            |    01: 0000000000000000
02: ,,,########,,,,,                            |    02: 0001111111100000
03: ,,,#...#...#,:|:                            |    03: 0001111111100330
04: ^,,#.+...+..#F:|                            |    04: 0001111111100330
05: ,,,#.H.#.S.#,:|:                            |    05: 0001111111100330
06: ^,,#...+....#:::                            |    06: 0001111111100330
07: ,,,#...+..../+++                            |    07: 0001111111144444
08: ^,,#.C.#.G.#::::                            |    08: 0002222222200330
09: ,,,#.+...+..#,:|                            |    09: 0002222222200330
10: ,,,########,,:|:                            |    10: 0002222222200330
11: ,,,,,,::::,,,,,,                            |    11: 0000003333000000
12: ^,,,,,::::,,,,^,                            |    12: 0000003333000000
13: ,,,,,,,::,,,,,,,                            |    13: 0000000000000000
14: ^,^,,,,,,,,,,,^,                            |    14: 0000000000000000
15: ,,,^,,,,,,,,,,^,                            |    15: 0000000000000000
```

### Features Registry
- ID 'chieftain_hall': **High Chieftain's Lodge** ['C'] (hall)
  - Position: [X: 05, Y: 08]
  - Lore: A heavy timber-framed hall constructed from Greenwood pine, where the hill chieftains feast and treat with merchants from Aethelford.
- ID 'clan_smithy': **Kestrel Hill Smithy** ['S'] (smithy)
  - Position: [X: 09, Y: 05]
  - Lore: A busy forge converting river-shipped iron ingots from Aethelford into sheep shears, stone-chisels, and hill-clan weapons.
- ID 'great_hearth': **The Great Chalk Hearth** ['H'] (hearth)
  - Position: [X: 05, Y: 05]
  - Lore: A massive central hearth built from limestone slabs where clan elders gather to burn peat and receive trade envoys from Aethelford.
- ID 'sheep_fold': **East Terraced Sheepfold** ['F'] (hurdle)
  - Position: [X: 13, Y: 04]
  - Lore: Woven hurdle enclosures holding hardy hill sheep whose high-grade fleece feeds the growing weaving looms of Aethelford.
- ID 'wool_storehouse': **Downs Wool & Supply Vault** ['G'] (granary)
  - Position: [X: 09, Y: 08]
  - Lore: A sturdy thatched storehouse filled with dense wool bales, dressed stone, and salted mutton packaged for shipment along the Downs-Way to Aethelford.

### Districts Registry
- ID '0': **Frontier Buffer & Wild Downs** (buffer)
  - Lore: Unzoned rolling hills of fescue, wild rye, and craggy limestone bluffs echoing with hill-clan horn calls.
- ID '1': **Redoubt Commons & Hearth Yard** (square)
  - Lore: The inner palisade enclosure centered around the ancient chalk hearth and hill smithy.
- ID '2': **High Lodge Ward** (keep)
  - Lore: The sheltered southern wing housing the chieftain's timber hall and dry wool stores.
- ID '3': **Pastoral Sheep-Runs & Terraces** (farmland)
  - Lore: Enclosed hurdle pens and hillside sheep-runs where hill-clan flocks are folded and shorn.
- ID '4': **Downs-Way Approach** (crafts)
  - Lore: The beaten dirt and limestone track connecting the palisade threshold to Aethelford.
