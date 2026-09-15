# World State: The Unmeasured Expanse
- Epoch: 2
- Dimensions: 32x32 (X: 00..31, Y: 00..31)
- Registered Features: 8

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- REGION GRID (Biome IDs) ---]
    00000000001111111111222222222233             00000000001111111111222222222233
    01234567890123456789012345678901             01234567890123456789012345678901
00: ,,,,,,,,,##,^,^^^,^,^^^,^,^^^,^^    |    00: 55555555544111111111111111111111
01: ,,,,,,,,,##^,^^^,^,^~^,^,^^~,^,^    |    01: 55555555544111111111311111121111
02: ,,,,,,,,,#&,^^^,^,^~~,^,^^~~/,^^    |    02: 55555555544111111113311111222111
03: ,,//,.,,#&#^^^,^,^~~,^,^^^~/,^^^    |    03: 55555555444111111133111111221111
04: ,,,,.o++&##,^,^,^~~,^,^,^~~/^,^,    |    04: 55555555444111111331111112221111
05: ,%%,,,,++##^,^,^~~,^,^,^,~!^,^,^    |    05: 56655555444111113311111112211111
06: ,%,,,,,#++&#^,^~~,^,^,^,~~/,^,^,    |    06: 56555554444411133111111122211111
07: ,,,,,,,##+:::^~~,^,^,^,^~/,^,^,^    |    07: 5555555444CCC1331111111122111111
08: ,,,,,,,#&+++:~~,^,^,^,^~~/^,^,^,    |    08: 555555544CCCC3311111111222111111
09: ,//,,,#&#::O==++o##&###~/##&###&    |    09: 555555444CCC33444444444224444444
10: ,,,,,,&##:::~:&###&###~~/#&###&#    |    10: 555555444CCC3C444444442224444444
11: ,,,,%%###&:~~&###&###&~/#&###&##    |    11: 5555664444C334444444442244444444
12: ,,,,%###&##~&##%~%##&~~/&###&###    |    12: 55556444444344477744422244444444
13: ,,,,,##&##~~###~!~%&#~/&###&###&    |    13: 55555444443344477774422444444444
14: ,,,,,#&###~###&#~%~#~~/###&###&#    |    14: 55555444443444447774222444444444
15: ,,,,#&###&~##&###~%#~/###&###&##    |    15: 55554444443444444774224444444444
16: ,,//&###&#~~&###&##~~/##&###&###    |    16: 55554444443344444442224444444444
17: ,,,,###&###~###&###~/##&###&###&    |    17: 55554444444344444442244444444444
18: ,,,###&###&~~#&###~~/#&###&###&#    |    18: 55544444444334444422244444444444
19: ,,%%#&###&##~~###&~/#&###&###&##    |    19: 55664444444433444422444444444444
20: ,,%#&###&###&~~#&~~/&###&###&###    |    20: 55644444444443344222444444444444
21: ,,#&###&###&##~~~~#&###&###&###&    |    21: 55444444444444382244444444444444
22: ,,&###&###&###&~##&###&###&###&#    |    22: 55444444444444484444444444444444
23: ,,###&###&###&#~~&###&###&###&##    |    23: 55444444444444488444444444444444
24: &###&###&###&###~###&###&###&###    |    24: 44444444444444448444444444444444
25: ///,,,####;~%;~%~~%;~%####,,,,//    |    25: AAAAAA44449999999999994444AAAAAA
26: ///;;;####~%;~%;~%;~%;####;;;;//    |    26: AAAAAA44449999999999994444AAAAAA
27: ///;;;####%;~%;~~;~%;~####;;;;//    |    27: AAAAAA44449999999999994444AAAAAA
28: ~~~~;;;~~~~~~~~~~~~~~~~~~~;;;;~~    |    28: BBBBAAA9999999999999999999AAAABB
29: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |    29: BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
30: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |    30: BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
31: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |    31: BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
```

### Features Registry
- ID 'aethelford': **Aethelford** ['O'] (city)
  - Position: [X: 11, Y: 09]
  - Biome: Region 'C' (Aethelford Crofts) | Natural Ground: ':'
  - Lore: The sovereign river-city of the Silver Channel, boasting stone quays, granaries, and a fortified timber-and-stone citadel guarding the crossing into the eastern forest.
- ID 'downs_way': **The Downs-Way** ['+'] (road, 10 tiles)
  - Span: [X: 06, Y: 04] <---> [X: 11, Y: 08]
  - Coordinates: [[6, 4], [7, 4], [7, 5], [8, 5], [8, 6], [9, 6], [9, 7], [9, 8], [10, 8], [11, 8]]
  - Lore: A beaten dirt and crushed-limestone track hacked through the western fringes of the Greenwood Vault, linking Dun Kestrel to the river wharf at Aethelford.
- ID 'dun_kestrel': **Dun Kestrel** ['o'] (settlement)
  - Position: [X: 05, Y: 04]
  - Biome: Region '5' (The Undulating Downs) | Natural Ground: '.'
  - Lore: A hill-clan redoubt perched atop the chalk bluffs of the Undulating Downs, encircled by timber palisades and pastoral sheep-runs.
- ID 'eaveshold': **Eaveshold** ['o'] (settlement)
  - Position: [X: 16, Y: 09]
  - Biome: Region '4' (The Greenwood Vault) | Natural Ground: '.'
  - Lore: A fortified palisade outpost and pioneer logging haven established at the eastern edge of the cleared trace, keeping vigil against the unquiet horrors of the southern mire.
- ID 'kar_drakh': **Kar-Drakh** ['!'] (dungeon)
  - Position: [X: 26, Y: 05]
  - Biome: Region '2' (Red Sandstone Canyon) | Natural Ground: '/'
  - Lore: A colossal, cyclopean gatehouse hewn into the sheer precipice of the Red Sandstone Canyon, sealed by rune-carved basalt doors whose creators vanished before the dawn of mortal speech.
- ID 'mire_tomb_mor_ghul': **The Mire-Tomb of Mor-Ghul** ['!'] (dungeon)
  - Position: [X: 16, Y: 13]
  - Biome: Region '7' (The Drowned Clearings) | Natural Ground: '%'
  - Lore: A half-submerged necropolis amidst the stagnant oxbows of the Drowned Clearings, where witch-fires dance over moss-choked sarcophagi and primeval spirits whisper.
- ID 'silver_span': **The Silver Span** ['='] (bridge, 2 tiles)
  - Span: [X: 12, Y: 09] <---> [X: 13, Y: 09]
  - Coordinates: [[12, 9], [13, 9]]
  - Lore: A monumental timber-and-stone viaduct resting on sunken ashlar piers, spanning the deep waters of the Silver Channel to link Aethelford with the untamed eastern forest.
- ID 'sylvan_trace': **The Sylvan Trace** ['+'] (road, 2 tiles)
  - Span: [X: 14, Y: 09] <---> [X: 15, Y: 09]
  - Coordinates: [[14, 9], [15, 9]]
  - Lore: A corduroy road of felled hemlock logs and crushed shale running east from the Silver Span, driven through the dense timber to supply the frontier watch at Eaveshold.

### Regional Biomes
- ID '0': **Unnamed Wilderness** (wilderness)
  - Lore: Untamed and primeval wilderness connecting the distinct geographic landmarks of the realm.
- ID '1': **The Northern Ribs** (mountains)
  - Lore: A jagged wall of grey gneiss, dark basalt, and folded slate tearing the sky into cloud ribbons, crowned with eternal snowpacks and paleoglaciers.
- ID '2': **Red Sandstone Canyon** (cliffs)
  - Lore: A dizzying, mile-deep chasm where surging jade-green rapids thresh beneath sheer walls draped in hanging gardens of primordial ferns and liverworts.
- ID '3': **The Silver Channel** (river)
  - Lore: A majestic, half-league-wide river carrying mountain runoff through a fractured piedmont of rolling hills into the primeval basin.
- ID '4': **The Greenwood Vault** (forest)
  - Lore: An ancient expanse of moss-cloaked hemlocks and colossal oaks, now cleaved by the Silver Span and the corduroy logs of the Sylvan Trace as woodcutters push their fortified frontier into the eastern gloom.
- ID '5': **The Undulating Downs** (hills)
  - Lore: Vast rolling hills of wild rye and fescue interrupted by craggy limestone bluffs, now echoing with the horn-calls of pastoral hill-clans and the hearth-smoke of Dun Kestrel.
- ID '6': **The Peat-Hollow Bogs** (swamp)
  - Lore: Misty, sulfurous hollows where dark ale-colored peat-water stands stagnant among cotton-grass and gnarled dwarf willows.
- ID '7': **The Drowned Clearings** (lake)
  - Lore: A haunted wilderness of stagnant oxbow lakes and reed marshes where witch-fires burn brighter since mortal axes approached from the north, its drowned crypts whispering with restless malevolence.
- ID '8': **The Silent Meeting** (river)
  - Lore: The silent, monstrous confluence of the sister-rivers where their massive floods unite before cleaving the lowland forest toward the sea.
- ID '9': **The Labyrinthine Delta** (swamp)
  - Lore: A colossal web of mud-bars, braided channels, and tidal flats where freshwater violently collides with the salt of incoming sea storms.
- ID 'A': **The Storm-Claw Coast** (cliffs)
  - Lore: A battered barrier of black shale cliffs, basalt sea-stacks, and long peninsulas reaching into the churning foam of the sea.
- ID 'B': **The Deep Salt Sea** (ocean)
  - Lore: The vast, restless oceanic expanse from which deep-sea storms sweep in to hurl towers of grey brine against the continental stone.
- ID 'C': **Aethelford Crofts** (farmland)
  - Lore: Broad river-silt barley fields, flax plots, and rye crofts terraced along the fertile bends of the Silver Channel, feeding the bustling markets of Aethelford.

# Timeline

## Epoch 1: The First Hearthfires and the Awakening Stone

- **Dun Kestrel (o) at [5, 4]:** Founded by pastoral clans migrating across the high chalk ridges of the Undulating Downs, establishing a timber-and-earthwork redoubt to shelter sheep-herders from primeval predators.
- **Aethelford (o) at [11, 9]:** Established by river-pioneers on the western bank of the Silver Channel to harvest seasonal salmon runs and fell ancient hemlock for river-barges.
- **The Downs-Way [5, 4] <-> [11, 9]:** Cleared through the western eaves of the Greenwood Vault to connect the highland shepherds of Dun Kestrel with the timber yards and river-trade of Aethelford.
- **Aethelford Crofts (Domain Expansion):** River-silt terraces and barley plots cleared along the fertile bends of the Silver Channel to sustain the growing population of Aethelford.
- **Kar-Drakh (!) at [26, 5]:** Discovered by mountain scouts within a sheer cleft of the Red Sandstone Canyon—a cyclopean gatehouse of rune-carved basalt predating mortal reckoning.
- **The Mire-Tomb of Mor-Ghul (!) at [16, 13]:** Uncovered amidst the stagnant oxbows of the Drowned Clearings when hunters pursued swamp-beasts into half-submerged necromantic ruins where baleful witch-fires burn.
- **The Undulating Downs (Region Lore Mutation):** The quiet fescue hills now echo with pastoral horn-calls, herdsman camps, and the hearth-smoke of the newly raised haven of Dun Kestrel.
- **The Greenwood Vault (Region Lore Mutation):** The primeval silence of the hemlock canopy has been broken by woodcutter axes and tilled crofts along the banks of the Silver Channel.

## Epoch 2: The River Throne and the Crossing of the Silver Channel

- **Aethelford ('o' -> 'O'):** Enriched by flourishing salmon fisheries, timber barging, and trade along the Downs-Way, the humble river stockade was fortified with stone quays, high ashlar granaries, and a lordly river-citadel, rising as the sovereign capital of the central valleys.
- **Aethelford Crofts (Domain Expansion):** The expanding urban populace of Aethelford cleared adjacent light woods and terraced the rich alluvial silts along the western banks of the Silver Channel into productive barley strips, flax fields, and rye crofts.
- **The Silver Span (=) at [12, 9]:** Master masons and timber-wrights drove deep oak pilings and laid ashlar piers across the churning depths of the Silver Channel, erecting a colossal viaduct spanning from [12, 9] to [13, 9] to open mortal passage into the eastern wild.
- **The Sylvan Trace [14, 9] <-> [15, 9]:** A fortified corduroy road of felled hemlock logs and crushed slate was driven eastward through primeval old-growth to supply pioneer lumber camps and convey heavy virgin timber back to the Aethelford mills.
- **Eaveshold (o) at [16, 9]:** Established on cleared ground at the terminus of the Sylvan Trace as a fortified frontier bastion, built to harvest the eastern timberlands and maintain a wary sentinel watch against the necromantic blights festering in the marshes to the south.
- **The Greenwood Vault (Region Lore Mutation):** The primeval silence of the ancient hemlock canopy has been shattered by mortal iron, its western heart cleaved by the stone piers of the Silver Span and the timber-haulers of the Sylvan Trace.
- **The Drowned Clearings (Region Lore Mutation):** Stirred by the encroachment of mortal axes to the north, the ancient spirits within the southern oxbows grow wrathful; green witch-fires flare across the mossy waters and predatory swamp horrors prowl closer to the cleared borders.