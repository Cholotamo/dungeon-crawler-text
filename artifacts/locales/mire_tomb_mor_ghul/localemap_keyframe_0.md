# Locale Map: The Mire-Tomb of Mor-Ghul
- **Feature ID:** `mire_tomb_mor_ghul`
- **Classification:** Dungeon
- **Registered Features:** 6

### Geographic & World Context
- **Overview Lore:** A half-submerged necropolis amidst the stagnant oxbows of the Drowned Clearings, where witch-fires dance over moss-choked sarcophagi and primeval spirits whisper.
- **Host Region:** The Drowned Clearings (Lake)
  - *Host Region Lore:* "A tangled web of oxbow lakes, glassy freshwater sheets, and reed-choked marshes where water-lilies bear the weight of nesting herons."
- **Surrounding Perimeters:**
  - **SOUTH & WEST BORDER:** The Greenwood Vault (Forest)
    - *Lore Context:* "An unbroken canopy of moss-cloaked hemlocks and broad oaks, newly pierced along the Silver Channel by mortal woodcutters and the tilled crofts of Aethelford."
  - **NORTH & EAST BORDERS:** Transition into host region (The Drowned Clearings — Lake).
    - *Lore Context:* "A tangled web of oxbow lakes, glassy freshwater sheets, and reed-choked marshes where water-lilies bear the weight of nesting herons."
- **External Ingress & Connected Destinations:**
  - **Perimeter Approach:** None -> Wilderness Traversal
    - *Destination Context:* "None. (Isolated wilderness site; entry is via local terrain traversal)."

### World Relations & Material Flow
Isolated amidst swampy oxbows, the tomb sits at the boundary of the Greenwood Vault forest, drawing brave herbalists and tomb-raiders from mortal crofts like Aethelford who seek witch-fire moss, ancient votive relics, and swamp timber.

### Architectural & Spatial Rationale
Built partly above water and partly sunken into marshy ground, the tomb features raised wooden boardwalks spanning stagnant shallows to connect the outer forest approach with stone crypts and an elevated spirit sanctum safe from seasonal oxbow flooding.

### Map Inspection (Side-by-Side)
```text
    [--- COMPOSITE MAP (Terrain + Features) ---]         [--- DISTRICT GRID (Zoning IDs) ---]
    0123456789012345                                     0123456789012345
00: ~~~~~~~~~~;;;&&&                            |    00: 0000000000000000
01: ~~~~~~~;;;;;&&&&                            |    01: 0000000000000000
02: ~~~~~;;######;;;                            |    02: 0000004444440000
03: ~~~;;;##B...####                            |    03: 0000004444440555
04: ~~;;;##......#A#                            |    04: 0000004444440555
05: ~~;;;##../##...#                            |    05: 0000004444440555
06: ~;;;+WWW+##/...#                            |    06: 0002222222225555
07: ~;;;+;;;+/.....#                            |    07: 0002222223333330
08: &;;;+;;;+#F.S..#                            |    08: 0002222223333330
09: &&,++WWW+#.....#                            |    09: 1112222223333330
10: &&,+,&;;;###/###                            |    10: 1111222223333330
11: &,,,,&;;T......#                            |    11: 1111111111111110
12: &,,,,&&&+......#                            |    12: 1111111111111110
13: &,,,,&&&+......#                            |    13: 1111111111111110
14: &&&&&&&&+,,,,,,,                            |    14: 1111111111111110
15: &&&&&&&&+,,,,,,,                            |    15: 1111111111111110
```

### Features Registry
- ID 'outer_threshold': **The Moss-Draped Threshold** ['T'] (threshold)
  - Position: [X: 08, Y: 11]
  - Lore: A weather-worn stone archway choked with damp lichen, marking the outer boundary between the wild forest and the mire-tomb.
- ID 'oxbow_boardwalk': **Oxbow Boardwalk Bridge** ['W'] (bridge)
  - Footprint: 6 tiles ([X: 05..07, Y: 06..09])
  - Lore: Decaying timber spans lashed over stagnant shallows, providing passage across the flooded oxbow waters.
- ID 'sarcophagus': **Lichen-Encrusted Sarcophagus of Mor-Ghul** ['S'] (sarcophagus)
  - Position: [X: 12, Y: 08]
  - Lore: A massive stone tomb carved with ancient runes, wrapped in glowing green moss and dancing witch-fires.
- ID 'spirit_altar': **Altar of the Primeval Spirit** ['A'] (altar)
  - Position: [X: 14, Y: 04]
  - Lore: A raised monolithic slab where spirits of the drowned marsh are invoked, adorned with votive reeds and dried water-lilies.
- ID 'votive_basin': **Submerged Votive Basin** ['B'] (basin)
  - Position: [X: 08, Y: 03]
  - Lore: A sunken stone basin fed by oxbow waters, holding shimmering witch-fire residue and tarnish-green copper offerings.
- ID 'witch_brazier': **Witch-Fire Brazier** ['F'] (brazier)
  - Position: [X: 10, Y: 08]
  - Lore: An ancient iron basin crackling with cold, ethereal green flame that illuminates the dark crypt without heat.

### Districts Registry
- ID '0': **Frontier Buffer & Drowned Margins** (buffer)
  - Lore: Stagnant oxbow waters of the Drowned Clearings to the north and east, and dense hemlock forest of the Greenwood Vault to the south and west.
- ID '1': **Overgrown Approach** (antechamber)
  - Lore: A mud-soaked trail winding through mossy trees and submerged stones toward the tomb's outer threshold.
- ID '2': **Flooded Courtyard** (hall)
  - Lore: A half-submerged stone plaza choked with reeds, shallows, and decaying wooden boardwalks.
- ID '3': **Crypt of Mor-Ghul** (crypt)
  - Lore: Ancient stone chambers where witch-fires light row upon row of lichen-encrusted sarcophagi.
- ID '4': **Submerged Catacombs** (catacomb)
  - Lore: Flooded lower passages filled with stagnant water, glowing witch-fire moss, and ancient votive niches.
- ID '5': **Inner Sanctum** (sanctum)
  - Lore: The high chamber resting above the waterline on a natural stone outcrop, housing the primeval spirit altar.
