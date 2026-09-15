# World State: The Unmeasured Expanse
- Dimensions: 32x32 (X: 00..31, Y: 00..31)
- Registered Features: 0

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- REGION GRID (Biome IDs) ---]
    00000000001111111111222222222233             00000000001111111111222222222233
    01234567890123456789012345678901             01234567890123456789012345678901
00: ,,,,,,,,,##,^,^^^,^,^^^,^,^^^,^^    |    00: 55555555544111111111111111111111
01: ,,,,,,,,,##^,^^^,^,^~^,^,^^~,^,^    |    01: 55555555544111111111311111121111
02: ,,,,,,,,,#&,^^^,^,^~~,^,^^~~/,^^    |    02: 55555555544111111113311111222111
03: ,,//,,,,#&#^^^,^,^~~,^,^^^~/,^^^    |    03: 55555555444111111133111111221111
04: ,,,,,,,,&##,^,^,^~~,^,^,^~~/^,^,    |    04: 55555555444111111331111112221111
05: ,%%,,,,,###^,^,^~~,^,^,^,~/^,^,^    |    05: 56655555444111113311111112211111
06: ,%,,,,,###&#^,^~~,^,^,^,~~/,^,^,    |    06: 56555554444411133111111122211111
07: ,,,,,,,##&###^~~,^,^,^,^~/,^,^,^    |    07: 55555554444441331111111122111111
08: ,,,,,,,#&###&~~,^,^,^,^~~/^,^,^,    |    08: 55555554444443311111111222111111
09: ,//,,,#&###&~~#&###&###~/##&###&    |    09: 55555544444433444444444224444444
10: ,,,,,,&###&#~#&###&###~~/#&###&#    |    10: 55555544444434444444442224444444
11: ,,,,%%###&#~~&###&###&~/#&###&##    |    11: 55556644444334444444442244444444
12: ,,,,%###&##~&##%~%##&~~/&###&###    |    12: 55556444444344477744422244444444
13: ,,,,,##&##~~###~%~%&#~/&###&###&    |    13: 55555444443344477774422444444444
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
*(No features registered yet)*

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
  - Lore: An unbroken canopy of moss-cloaked hemlocks, broad oaks, and lichen-streaked birches rooted in a soft, black mattress of ancient decay.
- ID '5': **The Undulating Downs** (hills)
  - Lore: Vast rolling hills of wild rye and fescue interrupted by craggy limestone bluffs that resemble the drowned bones of sea-beasts.
- ID '6': **The Peat-Hollow Bogs** (swamp)
  - Lore: Misty, sulfurous hollows where dark ale-colored peat-water stands stagnant among cotton-grass and gnarled dwarf willows.
- ID '7': **The Drowned Clearings** (lake)
  - Lore: A tangled web of oxbow lakes, glassy freshwater sheets, and reed-choked marshes where water-lilies bear the weight of nesting herons.
- ID '8': **The Silent Meeting** (river)
  - Lore: The silent, monstrous confluence of the sister-rivers where their massive floods unite before cleaving the lowland forest toward the sea.
- ID '9': **The Labyrinthine Delta** (swamp)
  - Lore: A colossal web of mud-bars, braided channels, and tidal flats where freshwater violently collides with the salt of incoming sea storms.
- ID 'A': **The Storm-Claw Coast** (cliffs)
  - Lore: A battered barrier of black shale cliffs, basalt sea-stacks, and long peninsulas reaching into the churning foam of the sea.
- ID 'B': **The Deep Salt Sea** (ocean)
  - Lore: The vast, restless oceanic expanse from which deep-sea storms sweep in to hurl towers of grey brine against the continental stone.