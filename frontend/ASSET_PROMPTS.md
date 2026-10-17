# EduPad AI Office visual asset prompts

Generated with the built-in Imagegen tool on 2026-10-13. The user's supplied office image was
used only as a composition and style reference. All project assets were generated as original
artwork and saved locally. Files loaded by the office at runtime live in `public/assets/`;
source sheets and earlier versions live in `art/` (same folder layout) so they are not shipped
with the dashboard build.

## Office map

> Production Phaser 3 game environment background for EduPad AI Office. Create an original,
> premium 16-bit pixel-art office in strict orthographic top-down view, landscape 3:2. Use a
> symmetrical three-room top and three-room bottom layout: Command Center, Research Lab, Tutor
> Room, Planning Hub, Analytics Room, and Knowledge Server. Connect them with a broad central
> corridor and planted knowledge-globe atrium. Use navy architecture, cyan/blue technology,
> pale stone floors, warm wood, green plants, and small yellow accents. Leave unobstructed paths
> and clean character floor space. Environment only: no characters, embedded text, logos,
> watermark, isometric angle, blur, antialiasing, or furniture blocking corridors.

Output: `art/office/edupad-office-map-v1.png`.

## Calm structural office shell v2

> Edit the referenced EduPad AI Office pixel-art map into a calm structural base map for a
> Phaser game. Preserve the exact 3:2 canvas, orthographic top-down perspective, six-room
> architectural layout, walls, windows, doors, floor materials, and connected corridors.
> Remove all characters, labels, logos, furniture, computers, server racks, bookshelves,
> whiteboards, sofas, globe sculpture, plants, cabinets, lamps, loose props, and decorative
> clutter. Keep generous walkable floor space with restrained navy architecture, pale warm
> stone floors, subtle cyan highlights, and small yellow light accents. No text, characters,
> furniture, or objects.

Output: `art/office/edupad-office-shell-v2.png`.

## Modular office furniture atlas v1

> Create a transparent 4x4 pixel-art furniture atlas matching the office shell's exact
> orthographic/top-down perspective and navy, cyan, pale warm, white, and yellow palette.
> Place exactly one isolated object in each equal cell with transparent padding. In strict row
> order: command console, research workbench, tutor desk, planning desk; analytics console,
> server racks, indexing terminal, globe planter; bookshelf, whiteboard, scanner cabinet,
> navy sofa; tall plant, small plant, office chair, technology kiosk. No characters, labels,
> logos, background, visible grid, borders, or cropped objects.

Output: `art/office/office-furniture-atlas-v1.png`.

### Safe-gutter atlas v2

The furniture set was regenerated with every complete object constrained to the center of its
cell. Because generative output still crossed the mathematical 313.5-pixel boundaries, the
source was deterministically repacked by `scripts/repack-office-atlas.ps1` into an exact
1536x1536 sheet with sixteen 384x384 frames. Every frame now has at least 39 pixels of horizontal
gutter and 47 pixels of vertical gutter, preventing Phaser from clipping or leaking adjacent
objects.

Outputs:

- `art/office/office-furniture-atlas-source-v2.png`
- `public/assets/office/office-furniture-atlas-v2.png`

## Foreground wall layer v1

> Derive an exact transparent foreground wall layer from the structural office shell. Preserve
> the 1536x1024 canvas, coordinates, scale, corners, pillars, and door openings. Keep only outer
> wall frames, interior divider walls, front-facing wall caps, door jambs and headers, cyan wall
> lights, and structural pillars. Remove all floors, room fills, corridor fills, furniture,
> characters, text, labels, and decoration. Every non-wall pixel is transparent and every door
> opening remains transparent.

Output: `art/office/edupad-office-walls-v1.png`.

## PIXEL walk sheet

> Transparent production pixel-art spritesheet for Phaser 3. Create exactly 16 frames of the
> same compact white, cyan, navy, and yellow AI robot PIXEL in an exact 4x4 conceptual grid.
> Row 1: four-frame walk facing down. Row 2: walk left. Row 3: walk right. Row 4: walk up. Keep
> identical silhouette, scale, palette, face, antenna, accessories, and aligned feet. Use crisp
> handcrafted 16-bit pixels with no antialiasing. Transparent background; no labels, borders,
> floor, shadow, logo, watermark, props, cropped limbs, or character redesign between frames.

Output: `art/agents/pixel/pixel-walk-v1.png`.

## PIXEL action sheet

> Use the walk sheet as the strict identity anchor. Create exactly 16 transparent frames in a
> 4x4 conceptual grid. Row 1: idle and blink facing down. Row 2: typing/working facing up at an
> implied computer, without props. Row 3: completed celebration with a small yellow success
> sparkle. Row 4: failed state with red warning eyes and a lowered head. Preserve the exact
> design, proportions, palette, pixel scale, and aligned feet. No text, visible grid, panels,
> floor, desk, extra characters, logo, or watermark.

Output: `public/assets/agents/pixel/pixel-actions-v1.png`.

## PIXEL seated action sheet v2

> Use the previous action and walk sheets as strict identity anchors. Preserve the 4x4 layout,
> Rows 1, 3, and 4, and change only Row 2 into a seated four-frame typing loop viewed from
> behind: compact bent legs, lower torso, and alternating arms reaching toward an implied
> keyboard. Do not draw the desk, chair, keyboard, or computer because those are part of the
> office map. Keep the background genuinely transparent and preserve the exact silhouette,
> palette, scale, anchor, and pixel treatment.

Output: `art/agents/pixel/pixel-actions-seated-v2.png`.

## Role-based work action sheet v1

> Use the PIXEL sheets as strict identity anchors. Create exactly sixteen transparent frames in
> a 4x4 grid. Row 1: seated typing from behind. Row 2: standing and checking documents/tablet.
> Row 3: standing server maintenance facing right/up-right. Row 4: standing tutor/planning
> gestures. Preserve character scale, proportions, palette, antenna, outline, pixel density, and
> stable anchors. Do not draw floors, desks, chairs, large props, text, labels, or borders.

Output: `art/agents/pixel/pixel-work-actions-v1.png`.

NOVA, SORA, TEMPO, METRIC, and NEXUS intentionally reuse the same canonical walk/action sheets.
Phaser applies each agent's configured accent tint at runtime. This prevents per-frame geometry
drift and guarantees identical animation timing while keeping each character visually distinct.

