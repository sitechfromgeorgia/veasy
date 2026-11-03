# Pirosmani Naive (`pirosmani-naive`)

> Deep black oilcloth canvas with luminous hand-painted figures, feasts, and honest silhouettes inspired by Niko Pirosmani's public domain masterworks.

## 1. At-a-Glance Signature
- Deep, matte black oilcloth ground (`#0D0D0E`) with visible subtle grain and sheen.
- Luminous chalk-white (`#FDFBF7`), raw umber (`#6B4423`), warm ochre (`#D97706`), and cinnabar red (`#B91C1C`) brushstrokes painted directly on dark fabric.
- Bold naive silhouettes with honest, direct outward gazes, monumental simplicity, and pure Georgian soul.
- Handcrafted Georgian Mkhedruli signboard lettering painted with bristle texture.

## 2. Public Domain & Cultural Heritage
- Niko Pirosmani (1862–1918) was a self-taught Georgian painter whose entire body of work resides in the **public domain worldwide**.
- This style celebrates authentic Georgian cultural heritage, wine culture, historic culinary feasts (სუფრა), pastoral life, and urban Tbilisi characters.
- **Brand Law Invariant**: **Palette: Own & Fonts: Own**. Strictly forbidden for hard breaking news (`news`). Allowed for cultural documentaries, tourism explainers, and heritage stories when listed in `brand.json` `"styles"`.

## 3. Vertical (1080×1920) Geometry & Safe Zones
- Oilcloth canvas: 1080×1920 px.
- Hero figures or feast compositions occupy the vertical center ($x \in [100, 980]$, $y \in [280, 1340]$).
- Signboard headers: painted at top of stage ($y \in [260, 360]$).
- Lower third: Captions sit comfortably at $y \in [1380, 1552]$ on a dark oilcloth strip.
- Right margin clear zone: $x \le 940$ below $y = 1100$.

## 4. Georgian Mkhedruli Typography
- Painted signboard lettering reminiscent of historic Tbilisi tavern signs (დუქანი).
- Bold, unadorned Mkhedruli characters with distinct brushstroke weight transitions.
- High contrast chalk-white on black oilcloth ensuring absolute legibility.

## 5. Motion & Animation Rules
- Painted brush reveals: figures emerge stroke by stroke or layer by layer on the oilcloth.
- Subtle painterly camera breathing or gentle push-in towards the eyes of the portrait.
- Transitions: oilcloth curtain cut or dry-brush wipe across the grain.

## 6. Sound Craft
- Georgian acoustic folk instruments: authentic **Panduri** (Eastern Georgian lute) or **Chonguri** (Western Georgian lute) plucked-string physical modeling (`tools/pluck.py`).
- Constant audio level without ducking or artificial volume pumps.
- SFX: subtle canvas rustle whoosh (`whoosh`), wooden wine cask thud (`thud`).
