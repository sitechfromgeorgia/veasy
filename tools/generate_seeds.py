"""Build and validate 26 new seed drawings for Veasy."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import art, icons

SEEDS_DIR = pathlib.Path(__file__).resolve().parent.parent / "assets" / "drawings"

NEW_SEEDS = [
    {
        "name": "airplane",
        "motif": "plane",
        "about": "a passenger aircraft on the runway preparing for takeoff",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="540" x2="902" y2="540" stroke="LINE" stroke-width="6"/>'
            '<line x1="120" y1="540" x2="840" y2="540" stroke="MUTED" stroke-width="4" stroke-dasharray="40 30"/></g>'
            '<g class="s" style="--d:0.5s"><path d="M120 400 C180 340 300 320 620 320 C760 320 830 350 840 390 C840 430 760 450 600 450 L200 450 C150 450 120 420 120 400 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M220 325 L140 160 L240 160 L320 322 Z" stroke="INK" stroke-width="7" fill="none"/></g>'
            '<g class="r" style="--d:0.9s"><path d="M740 350 L790 365 L785 390 L735 380 Z" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<rect x="280" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="340" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="400" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="460" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="520" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="580" y="365" width="28" height="24" rx="6" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.2s"><path d="M420 420 L300 500 L380 500 L540 420 Z" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="410" y="470" width="100" height="42" rx="14" stroke="MUTED" stroke-width="6"/>'
            '<line x1="460" y1="512" x2="460" y2="540" stroke="INK" stroke-width="6"/>'
            '<circle cx="460" cy="540" r="14" stroke="INK" stroke-width="5" fill="CANVAS"/>'
            '<line x1="720" y1="450" x2="720" y2="540" stroke="INK" stroke-width="5"/>'
            '<circle cx="720" cy="540" r="12" stroke="INK" stroke-width="5" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="180" cy="155" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "ambulance-car",
        "motif": "ambulance",
        "about": "an emergency medical ambulance with lights and cross",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="140" y="220" width="670" height="260" rx="28" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M620 220 L730 310 L810 320" stroke="INK" stroke-width="7" fill="none"/>'
            '<line x1="140" y1="375" x2="810" y2="375" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="r" style="--d:0.8s"><path d="M630 240 L715 315 L630 315 Z" stroke="MUTED" stroke-width="6" fill="none"/>'
            '<rect x="380" y="250" width="160" height="90" rx="12" stroke="MUTED" stroke-width="5"/>'
            '<path d="M250 280 L290 280 L290 240 L330 240 L330 280 L370 280 L370 320 L330 320 L330 360 L290 360 L290 320 L250 320 Z" stroke="INK" stroke-width="6" fill="none"/></g>'
            '<g class="p" style="--d:1.1s"><circle cx="300" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="300" cy="480" r="18" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="680" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="680" cy="480" r="18" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.4s"><rect x="390" y="180" width="120" height="40" rx="10" stroke="INK" stroke-width="6"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="450" cy="195" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "cargo-ship",
        "motif": "ship",
        "about": "a container cargo vessel sailing across open water",
        "svg": (
            '<g class="s" style="--d:0.2s"><path d="M40 500 Q 150 480 260 500 T 480 500 T 700 500 T 912 500" stroke="LINE" stroke-width="6" fill="none"/>'
            '<path d="M80 540 Q 190 520 300 540 T 520 540 T 740 540 T 870 540" stroke="LINE" stroke-width="5" fill="none"/></g>'
            '<g class="s" style="--d:0.5s"><path d="M100 360 L180 490 L760 490 L850 360 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="190" y="210" width="140" height="150" rx="14" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="210" y="235" width="100" height="35" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<line x1="260" y1="210" x2="260" y2="150" stroke="INK" stroke-width="6"/>'
            '<line x1="235" y1="170" x2="285" y2="170" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="r" style="--d:1.1s"><rect x="360" y="300" width="120" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="500" y="300" width="120" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="640" y="300" width="120" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="420" y="240" width="120" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="560" y="240" width="120" height="60" rx="8" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="790" cy="410" r="14" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="820" cy="350" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "credit-card",
        "motif": "credit-card",
        "about": "a modern payment terminal and contactless smart card",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="80" y1="570" x2="872" y2="570" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="490" y="150" width="340" height="420" rx="28" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="530" y="200" width="260" height="140" rx="14" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="530" y1="380" x2="790" y2="380" stroke="LINE" stroke-width="5"/>'
            '<circle cx="575" cy="430" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="660" cy="430" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="745" cy="430" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="575" cy="495" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="660" cy="495" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="745" cy="495" r="16" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="r" style="--d:1.1s"><rect x="120" y="260" width="380" height="240" rx="20" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="170" y="330" width="70" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<path d="M430 310 A 30 30 0 0 1 430 360" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M445 295 A 50 50 0 0 1 445 375" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<line x1="170" y1="430" x2="390" y2="430" stroke="MUTED" stroke-width="5" stroke-dasharray="24 16"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="660" cy="180" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "dam-hydro",
        "motif": "dam",
        "about": "a hydroelectric dam reservoir with water flow and powerhouse",
        "svg": (
            '<g class="s" style="--d:0.2s"><path d="M50 320 L240 180 L400 280" stroke="LINE" stroke-width="6" fill="none"/>'
            '<path d="M550 280 L710 180 L902 320" stroke="LINE" stroke-width="6" fill="none"/></g>'
            '<g class="s" style="--d:0.5s"><path d="M220 250 L730 250 L680 540 L270 540 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<line x1="180" y1="250" x2="770" y2="250" stroke="INK" stroke-width="6"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="320" y="250" width="80" height="140" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="435" y="250" width="80" height="140" rx="6" stroke="MUTED" stroke-width="5"/>'
            '<rect x="550" y="250" width="80" height="140" rx="6" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.1s"><path d="M360 390 L340 540" stroke="MUTED" stroke-width="5"/>'
            '<path d="M475 390 L475 540" stroke="MUTED" stroke-width="5"/>'
            '<path d="M590 390 L610 540" stroke="MUTED" stroke-width="5"/>'
            '<path d="M120 540 Q 200 525 280 540" stroke="LINE" stroke-width="5" fill="none"/>'
            '<path d="M670 540 Q 750 525 830 540" stroke="LINE" stroke-width="5" fill="none"/></g>'
            '<g class="r" style="--d:1.4s"><rect x="640" y="420" width="130" height="120" rx="10" stroke="INK" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="705" cy="400" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "database-server",
        "motif": "database",
        "about": "a high-density data center rack cabinet with mounted server blades",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="120" y1="560" x2="832" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="300" y="100" width="352" height="460" rx="22" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.7s"><rect x="330" y="140" width="292" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="330" y="220" width="292" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="330" y="300" width="292" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="330" y="380" width="292" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="330" y="460" width="292" height="60" rx="8" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="r" style="--d:1.1s"><circle cx="560" cy="170" r="8" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="560" cy="250" r="8" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="560" cy="330" r="8" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="560" cy="410" r="8" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="560" cy="490" r="8" stroke="MUTED" stroke-width="4"/>'
            '<path d="M220 200 C270 200 270 300 330 300" stroke="LINE" stroke-width="6" fill="none"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="590" cy="170" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "drone-flight",
        "motif": "drone",
        "about": "a multirotor aerial surveillance drone in flight",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="390" y1="290" x2="190" y2="190" stroke="INK" stroke-width="7"/>'
            '<line x1="562" y1="290" x2="762" y2="190" stroke="INK" stroke-width="7"/>'
            '<line x1="390" y1="360" x2="190" y2="460" stroke="INK" stroke-width="7"/>'
            '<line x1="562" y1="360" x2="762" y2="460" stroke="INK" stroke-width="7"/></g>'
            '<g class="s" style="--d:0.5s"><rect x="386" y="270" width="180" height="110" rx="24" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="436" y="380" width="80" height="60" rx="14" stroke="MUTED" stroke-width="6"/>'
            '<circle cx="476" cy="410" r="18" stroke="INK" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:0.9s"><circle cx="190" cy="190" r="22" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="762" cy="190" r="22" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="190" cy="460" r="22" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="762" cy="460" r="22" stroke="MUTED" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="r" style="--d:1.2s"><ellipse cx="190" cy="190" rx="90" ry="24" stroke="LINE" stroke-width="5" stroke-dasharray="24 16"/>'
            '<ellipse cx="762" cy="190" rx="90" ry="24" stroke="LINE" stroke-width="5" stroke-dasharray="24 16"/>'
            '<ellipse cx="190" cy="460" rx="90" ry="24" stroke="LINE" stroke-width="5" stroke-dasharray="24 16"/>'
            '<ellipse cx="762" cy="460" rx="90" ry="24" stroke="LINE" stroke-width="5" stroke-dasharray="24 16"/>'
            '<line x1="476" y1="270" x2="476" y2="210" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="200" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "electric-charger",
        "motif": "ev-charger",
        "about": "an electric vehicle fast charging station with cable and connector",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="80" y1="560" x2="872" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="320" y="130" width="312" height="430" rx="26" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="366" y="180" width="220" height="120" rx="14" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="416" y="220" width="120" height="40" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="476" cy="350" r="26" stroke="LINE" stroke-width="5" fill="none"/>'
            '<path d="M476 395 L460 435 L484 435 L468 475" stroke="INK" stroke-width="6" fill="none"/></g>'
            '<g class="s" style="--d:1.2s"><path d="M600 390 C690 420 730 460 700 510 C670 560 620 530 620 490 L620 380" stroke="INK" stroke-width="7" fill="none"/>'
            '<rect x="600" y="340" width="40" height="50" rx="8" stroke="INK" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="155" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "fire-truck",
        "motif": "siren",
        "about": "an emergency fire engine with rescue ladder and equipment",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="560" x2="902" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="120" y="240" width="712" height="240" rx="24" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M680 240 L790 320 L832 340 L832 480 L680 480 Z" stroke="INK" stroke-width="7" fill="none"/>'
            '<path d="M690 260 L775 325 L690 325 Z" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="150" y="280" width="140" height="150" rx="10" stroke="MUTED" stroke-width="5"/>'
            '<rect x="310" y="280" width="140" height="150" rx="10" stroke="MUTED" stroke-width="5"/>'
            '<rect x="470" y="280" width="140" height="150" rx="10" stroke="MUTED" stroke-width="5"/>'
            '<line x1="160" y1="330" x2="280" y2="330" stroke="LINE" stroke-width="4"/>'
            '<line x1="320" y1="330" x2="440" y2="330" stroke="LINE" stroke-width="4"/>'
            '<line x1="480" y1="330" x2="600" y2="330" stroke="LINE" stroke-width="4"/></g>'
            '<g class="s" style="--d:1.1s"><line x1="140" y1="200" x2="640" y2="200" stroke="INK" stroke-width="6"/>'
            '<line x1="140" y1="220" x2="640" y2="220" stroke="INK" stroke-width="6"/>'
            '<line x1="240" y1="200" x2="240" y2="220" stroke="MUTED" stroke-width="4"/>'
            '<line x1="340" y1="200" x2="340" y2="220" stroke="MUTED" stroke-width="4"/>'
            '<line x1="440" y1="200" x2="440" y2="220" stroke="MUTED" stroke-width="4"/>'
            '<line x1="540" y1="200" x2="540" y2="220" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.4s"><circle cx="270" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="270" cy="480" r="18" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="410" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="410" cy="480" r="18" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="710" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="710" cy="480" r="18" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="710" cy="215" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "graduation",
        "motif": "graduation-cap",
        "about": "an academic mortarboard cap and rolled graduate diploma",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="80" y1="550" x2="872" y2="550" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><polygon points="476,140 760,230 476,320 192,230" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M310 265 L310 370 C310 430 642 430 642 370 L642 265" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="310" y1="370" x2="642" y2="370" stroke="MUTED" stroke-width="5"/>'
            '<path d="M476 230 C580 240 670 290 680 370" stroke="MUTED" stroke-width="6" fill="none"/>'
            '<rect x="668" y="370" width="24" height="60" rx="6" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="r" style="--d:1.2s"><rect x="180" y="460" width="340" height="70" rx="16" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="320" y="450" width="36" height="90" rx="8" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="180" cy="495" rx="14" ry="35" stroke="MUTED" stroke-width="5" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="230" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "hotel-building",
        "motif": "hotel",
        "about": "a multi-story metropolitan hotel with glass entrance and canopy",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="560" x2="902" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="240" y="100" width="472" height="460" rx="20" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="396" y="60" width="160" height="40" rx="8" stroke="MUTED" stroke-width="5" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s">'
            '<rect x="290" y="140" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="390" y="140" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="490" y="140" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="590" y="140" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="290" y="220" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="390" y="220" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="490" y="220" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="590" y="220" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="290" y="300" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="390" y="300" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="490" y="300" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="590" y="300" width="60" height="50" rx="8" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.2s"><rect x="376" y="460" width="200" height="24" rx="6" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="416" y="484" width="120" height="76" rx="8" stroke="INK" stroke-width="6"/>'
            '<line x1="476" y1="484" x2="476" y2="560" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="80" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "laptop-code",
        "motif": "laptop",
        "about": "an open notebook computer displaying software code",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><path d="M120 480 L832 480 L802 530 L150 530 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="180" y="120" width="592" height="360" rx="18" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="210" y="150" width="532" height="300" rx="10" stroke="MUTED" stroke-width="5"/>'
            '<rect x="416" y="490" width="120" height="35" rx="6" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="s" style="--d:1.1s"><line x1="250" y1="190" x2="420" y2="190" stroke="MUTED" stroke-width="6"/>'
            '<line x1="280" y1="230" x2="520" y2="230" stroke="LINE" stroke-width="5"/>'
            '<line x1="280" y1="270" x2="480" y2="270" stroke="LINE" stroke-width="5"/>'
            '<line x1="310" y1="310" x2="590" y2="310" stroke="MUTED" stroke-width="6"/>'
            '<line x1="280" y1="350" x2="440" y2="350" stroke="LINE" stroke-width="5"/>'
            '<line x1="250" y1="390" x2="360" y2="390" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="476" cy="135" r="10" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "microchip-circuit",
        "motif": "microchip",
        "about": "a central semiconductor silicon microprocessor on a motherboard",
        "svg": (
            '<g class="s" style="--d:0.2s"><rect x="296" y="140" width="360" height="360" rx="28" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="386" y="230" width="180" height="180" rx="14" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="r" style="--d:0.6s">'
            '<line x1="160" y1="200" x2="296" y2="200" stroke="MUTED" stroke-width="6"/>'
            '<line x1="160" y1="260" x2="296" y2="260" stroke="MUTED" stroke-width="6"/>'
            '<line x1="160" y1="320" x2="296" y2="320" stroke="MUTED" stroke-width="6"/>'
            '<line x1="160" y1="380" x2="296" y2="380" stroke="MUTED" stroke-width="6"/>'
            '<line x1="160" y1="440" x2="296" y2="440" stroke="MUTED" stroke-width="6"/>'
            '<line x1="656" y1="200" x2="792" y2="200" stroke="MUTED" stroke-width="6"/>'
            '<line x1="656" y1="260" x2="792" y2="260" stroke="MUTED" stroke-width="6"/>'
            '<line x1="656" y1="320" x2="792" y2="320" stroke="MUTED" stroke-width="6"/>'
            '<line x1="656" y1="380" x2="792" y2="380" stroke="MUTED" stroke-width="6"/>'
            '<line x1="656" y1="440" x2="792" y2="440" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="s" style="--d:1.0s">'
            '<line x1="360" y1="40" x2="360" y2="140" stroke="MUTED" stroke-width="6"/>'
            '<line x1="420" y1="40" x2="420" y2="140" stroke="MUTED" stroke-width="6"/>'
            '<line x1="480" y1="40" x2="480" y2="140" stroke="MUTED" stroke-width="6"/>'
            '<line x1="540" y1="40" x2="540" y2="140" stroke="MUTED" stroke-width="6"/>'
            '<line x1="600" y1="40" x2="600" y2="140" stroke="MUTED" stroke-width="6"/>'
            '<line x1="360" y1="500" x2="360" y2="600" stroke="MUTED" stroke-width="6"/>'
            '<line x1="420" y1="500" x2="420" y2="600" stroke="MUTED" stroke-width="6"/>'
            '<line x1="480" y1="500" x2="480" y2="600" stroke="MUTED" stroke-width="6"/>'
            '<line x1="540" y1="500" x2="540" y2="600" stroke="MUTED" stroke-width="6"/>'
            '<line x1="600" y1="500" x2="600" y2="600" stroke="MUTED" stroke-width="6"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="340" cy="180" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "police-car",
        "motif": "shield",
        "about": "a law enforcement patrol car with security shield badge",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="140" y="260" width="670" height="220" rx="26" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M260 260 L360 170 L600 170 L700 260 Z" stroke="INK" stroke-width="7" fill="none"/>'
            '<line x1="140" y1="350" x2="810" y2="350" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="r" style="--d:0.8s"><path d="M370 190 L460 190 L460 250 L310 250 Z" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M490 190 L585 190 L650 250 L490 250 Z" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M440 310 L510 310 L510 360 C510 395 475 415 475 415 C475 415 440 395 440 360 Z" stroke="INK" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:1.1s"><circle cx="290" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="290" cy="480" r="18" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="660" cy="480" r="54" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="660" cy="480" r="18" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.4s"><rect x="446" y="140" width="60" height="30" rx="8" stroke="INK" stroke-width="6"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="476" cy="155" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "radio-antenna",
        "motif": "radio-tower",
        "about": "a tall broadcast transmission tower with signal radiation",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="80" y1="560" x2="872" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><line x1="320" y1="560" x2="476" y2="100" stroke="INK" stroke-width="7"/>'
            '<line x1="632" y1="560" x2="476" y2="100" stroke="INK" stroke-width="7"/>'
            '<line x1="476" y1="100" x2="476" y2="50" stroke="INK" stroke-width="6"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="360" y1="460" x2="592" y2="460" stroke="MUTED" stroke-width="5"/>'
            '<line x1="360" y1="460" x2="550" y2="350" stroke="MUTED" stroke-width="4"/>'
            '<line x1="592" y1="460" x2="400" y2="350" stroke="MUTED" stroke-width="4"/>'
            '<line x1="400" y1="350" x2="550" y2="350" stroke="MUTED" stroke-width="5"/>'
            '<line x1="400" y1="350" x2="515" y2="230" stroke="MUTED" stroke-width="4"/>'
            '<line x1="550" y1="350" x2="435" y2="230" stroke="MUTED" stroke-width="4"/>'
            '<line x1="435" y1="230" x2="515" y2="230" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.2s"><path d="M430 80 A 60 60 0 0 0 430 20" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M522 80 A 60 60 0 0 1 522 20" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M400 100 A 100 100 0 0 0 400 0" stroke="LINE" stroke-width="5" fill="none"/>'
            '<path d="M552 100 A 100 100 0 0 1 552 0" stroke="LINE" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="50" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "satellite-orbit",
        "motif": "satellite",
        "about": "an orbital communication satellite with photovoltaic solar panels",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="386" y1="320" x2="140" y2="320" stroke="INK" stroke-width="6"/>'
            '<line x1="566" y1="320" x2="812" y2="320" stroke="INK" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="386" y="240" width="180" height="160" rx="20" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M476 400 L476 490" stroke="INK" stroke-width="6"/>'
            '<path d="M400 510 C440 470 512 470 552 510" stroke="INK" stroke-width="7" fill="none"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="140" y="200" width="100" height="240" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<rect x="260" y="200" width="100" height="240" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<rect x="592" y="200" width="100" height="240" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<rect x="712" y="200" width="100" height="240" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/></g>'
            '<g class="r" style="--d:1.1s"><circle cx="476" cy="300" r="28" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<line x1="476" y1="490" x2="476" y2="460" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="476" cy="300" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "solar-farm",
        "motif": "solar-panel",
        "about": "a photovoltaic solar panel array collecting sunlight",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="540" x2="902" y2="540" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><polygon points="160,200 792,200 732,390 100,390" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<line x1="270" y1="390" x2="270" y2="540" stroke="INK" stroke-width="7"/>'
            '<line x1="682" y1="390" x2="682" y2="540" stroke="INK" stroke-width="7"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="318" y1="200" x2="258" y2="390" stroke="MUTED" stroke-width="5"/>'
            '<line x1="476" y1="200" x2="416" y2="390" stroke="MUTED" stroke-width="5"/>'
            '<line x1="634" y1="200" x2="574" y2="390" stroke="MUTED" stroke-width="5"/>'
            '<line x1="140" y1="265" x2="772" y2="265" stroke="MUTED" stroke-width="5"/>'
            '<line x1="120" y1="330" x2="752" y2="330" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.1s"><rect x="426" y="440" width="100" height="100" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<circle cx="790" cy="110" r="30" stroke="LINE" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="476" cy="480" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "supermarket-cart",
        "motif": "shopping-cart",
        "about": "a retail shopping cart with goods in a supermarket",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="80" y1="560" x2="872" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><path d="M220 180 L760 180 L680 400 L280 400 Z" stroke="INK" stroke-width="7" fill="none"/>'
            '<path d="M140 140 L220 180" stroke="INK" stroke-width="7"/>'
            '<circle cx="140" cy="140" r="16" stroke="INK" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="360" y1="180" x2="350" y2="400" stroke="LINE" stroke-width="5"/>'
            '<line x1="440" y1="180" x2="430" y2="400" stroke="LINE" stroke-width="5"/>'
            '<line x1="520" y1="180" x2="510" y2="400" stroke="LINE" stroke-width="5"/>'
            '<line x1="600" y1="180" x2="590" y2="400" stroke="LINE" stroke-width="5"/>'
            '<line x1="680" y1="180" x2="670" y2="400" stroke="LINE" stroke-width="5"/>'
            '<line x1="240" y1="250" x2="735" y2="250" stroke="LINE" stroke-width="5"/>'
            '<line x1="260" y1="325" x2="708" y2="325" stroke="LINE" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.1s"><path d="M260 400 L300 490 L680 490 L660 400" stroke="INK" stroke-width="7" fill="none"/>'
            '<rect x="380" y="220" width="120" height="140" rx="10" stroke="MUTED" stroke-width="5" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.4s"><circle cx="320" cy="530" r="30" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="320" cy="530" r="10" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="660" cy="530" r="30" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="660" cy="530" r="10" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="440" cy="270" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "traffic-barrier",
        "motif": "traffic-cone",
        "about": "a roadworks safety barrier and traffic cone",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="140" y="240" width="460" height="160" rx="12" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<line x1="220" y1="400" x2="180" y2="560" stroke="INK" stroke-width="7"/>'
            '<line x1="520" y1="400" x2="560" y2="560" stroke="INK" stroke-width="7"/></g>'
            '<g class="r" style="--d:0.8s"><path d="M160 400 L240 240" stroke="MUTED" stroke-width="8"/>'
            '<path d="M260 400 L340 240" stroke="MUTED" stroke-width="8"/>'
            '<path d="M360 400 L440 240" stroke="MUTED" stroke-width="8"/>'
            '<path d="M460 400 L540 240" stroke="MUTED" stroke-width="8"/></g>'
            '<g class="s" style="--d:1.1s"><path d="M680 200 L610 520 L750 520 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="580" y="520" width="200" height="35" rx="8" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<path d="M648 350 L712 350" stroke="MUTED" stroke-width="7"/>'
            '<path d="M632 430 L728 430" stroke="MUTED" stroke-width="7"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="370" cy="200" r="18" stroke="INK" stroke-width="5" fill="CANVAS"/>'
            '<circle cx="370" cy="200" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "truck-freight",
        "motif": "truck",
        "about": "a heavy freight transport semi-truck for cargo transit",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="560" x2="902" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="100" y="160" width="500" height="300" rx="18" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M600 240 L720 240 L770 340 L840 370 L840 480 L600 480 Z" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="180" y1="160" x2="180" y2="460" stroke="LINE" stroke-width="5"/>'
            '<line x1="260" y1="160" x2="260" y2="460" stroke="LINE" stroke-width="5"/>'
            '<line x1="340" y1="160" x2="340" y2="460" stroke="LINE" stroke-width="5"/>'
            '<line x1="420" y1="160" x2="420" y2="460" stroke="LINE" stroke-width="5"/>'
            '<line x1="500" y1="160" x2="500" y2="460" stroke="LINE" stroke-width="5"/>'
            '<path d="M720 260 L760 340 L670 340 L670 260 Z" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:1.1s"><circle cx="210" cy="490" r="50" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="210" cy="490" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="320" cy="490" r="50" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="320" cy="490" r="16" stroke="MUTED" stroke-width="5"/>'
            '<circle cx="750" cy="490" r="50" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<circle cx="750" cy="490" r="16" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.4s"><rect x="450" y="470" width="120" height="40" rx="10" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="p" style="--d:1.7s"><circle cx="820" cy="410" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "warehouse-logistics",
        "motif": "warehouse",
        "about": "a modern distribution warehouse with loading bays and packages",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="50" y1="560" x2="902" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="140" y="180" width="672" height="380" rx="18" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M120 180 L476 80 L832 180" stroke="INK" stroke-width="7" fill="none"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="190" y="360" width="150" height="200" rx="10" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="380" y="360" width="150" height="200" rx="10" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="570" y="360" width="150" height="200" rx="10" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<rect x="240" y="240" width="180" height="60" rx="8" stroke="MUTED" stroke-width="5"/>'
            '<rect x="490" y="240" width="180" height="60" rx="8" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.2s"><line x1="200" y1="410" x2="330" y2="410" stroke="LINE" stroke-width="4"/>'
            '<line x1="200" y1="460" x2="330" y2="460" stroke="LINE" stroke-width="4"/>'
            '<line x1="390" y1="410" x2="520" y2="410" stroke="LINE" stroke-width="4"/>'
            '<line x1="390" y1="460" x2="520" y2="460" stroke="LINE" stroke-width="4"/>'
            '<line x1="580" y1="410" x2="710" y2="410" stroke="LINE" stroke-width="4"/>'
            '<line x1="580" y1="460" x2="710" y2="460" stroke="LINE" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="455" cy="330" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "wheat-harvest",
        "motif": "wheat",
        "about": "ears of golden wheat in an agricultural field",
        "svg": (
            '<g class="s" style="--d:0.2s"><path d="M60 550 Q 250 530 476 550 T 892 550" stroke="LINE" stroke-width="6" fill="none"/></g>'
            '<g class="s" style="--d:0.4s"><path d="M476 550 Q 476 340 476 120" stroke="INK" stroke-width="7" fill="none"/>'
            '<path d="M300 550 Q 320 380 270 200" stroke="INK" stroke-width="6" fill="none"/>'
            '<path d="M652 550 Q 632 380 682 200" stroke="INK" stroke-width="6" fill="none"/></g>'
            '<g class="r" style="--d:0.8s">'
            '<ellipse cx="440" cy="180" rx="30" ry="14" transform="rotate(-30 440 180)" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="512" cy="180" rx="30" ry="14" transform="rotate(30 512 180)" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="440" cy="240" rx="30" ry="14" transform="rotate(-30 440 240)" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="512" cy="240" rx="30" ry="14" transform="rotate(30 512 240)" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="440" cy="300" rx="30" ry="14" transform="rotate(-30 440 300)" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<ellipse cx="512" cy="300" rx="30" ry="14" transform="rotate(30 512 300)" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="s" style="--d:1.2s"><line x1="476" y1="120" x2="476" y2="40" stroke="MUTED" stroke-width="4"/>'
            '<line x1="440" y1="180" x2="380" y2="100" stroke="MUTED" stroke-width="4"/>'
            '<line x1="512" y1="180" x2="572" y2="100" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="120" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "wine-qvevri",
        "motif": "amphora",
        "about": "a traditional Georgian wine qvevri clay vessel",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="316" y="520" width="320" height="40" rx="10" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<path d="M356 180 C310 180 240 260 240 360 C240 450 340 520 476 520 C612 520 712 450 712 360 C712 260 642 180 596 180 Z" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="356" y="130" width="240" height="50" rx="12" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<path d="M260 320 C320 350 420 365 476 365 C532 365 632 350 692 320" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M290 400 C340 430 420 440 476 440 C532 440 612 430 662 400" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="s" style="--d:1.2s"><path d="M680 180 C680 140 730 140 740 180" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<circle cx="710" cy="190" r="12" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="735" cy="190" r="12" stroke="MUTED" stroke-width="4"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="476" cy="155" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "wind-turbine",
        "motif": "wind",
        "about": "a renewable wind energy turbine generator on a hill",
        "svg": (
            '<g class="s" style="--d:0.2s"><path d="M50 560 Q 350 480 650 530 T 902 560" stroke="LINE" stroke-width="6" fill="none"/></g>'
            '<g class="s" style="--d:0.4s"><path d="M450 510 L470 180 L482 180 L502 510 Z" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<rect x="436" y="150" width="80" height="40" rx="12" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<circle cx="446" cy="170" r="16" stroke="INK" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><path d="M446 170 C436 100 440 40 446 10 C452 40 456 100 446 170" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<path d="M446 170 C510 210 560 250 590 280 C570 270 510 240 446 170" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<path d="M446 170 C390 220 340 270 300 310 C320 280 380 230 446 170" stroke="INK" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="s" style="--d:1.2s"><path d="M120 220 Q 200 190 280 220" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M160 270 Q 240 240 320 270" stroke="MUTED" stroke-width="5" fill="none"/>'
            '<path d="M600 130 Q 700 100 800 130" stroke="MUTED" stroke-width="5" fill="none"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="496" cy="150" r="12" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "forest-nature",
        "motif": "tree-pine",
        "about": "pine evergreen trees in a mountain nature reserve",
        "svg": (
            '<g class="s" style="--d:0.2s"><path d="M50 560 Q 400 490 892 560" stroke="LINE" stroke-width="6" fill="none"/>'
            '<path d="M120 400 L240 260 L380 400" stroke="LINE" stroke-width="5" fill="none"/>'
            '<path d="M580 400 L720 240 L860 400" stroke="LINE" stroke-width="5" fill="none"/></g>'
            '<g class="s" style="--d:0.4s"><rect x="460" y="440" width="32" height="100" rx="6" stroke="INK" stroke-width="6" fill="CANVAS"/>'
            '<polygon points="476,140 540,240 412,240" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<polygon points="476,210 570,330 382,330" stroke="INK" stroke-width="7" fill="CANVAS"/>'
            '<polygon points="476,300 610,450 342,450" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><rect x="260" y="450" width="26" height="90" rx="4" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<polygon points="273,230 340,340 206,340" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<polygon points="273,310 366,450 180,450" stroke="MUTED" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="r" style="--d:1.1s"><rect x="680" y="450" width="26" height="90" rx="4" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<polygon points="693,230 760,340 626,340" stroke="MUTED" stroke-width="6" fill="CANVAS"/>'
            '<polygon points="693,310 786,450 600,450" stroke="MUTED" stroke-width="6" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.5s"><circle cx="476" cy="140" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
    {
        "name": "weather-station",
        "motif": "cloud-rain",
        "about": "a meteorological weather monitoring station during rain",
        "svg": (
            '<g class="s" style="--d:0.2s"><line x1="60" y1="560" x2="892" y2="560" stroke="LINE" stroke-width="6"/></g>'
            '<g class="s" style="--d:0.4s"><path d="M260 240 C230 240 200 270 200 300 C200 340 240 370 280 370 L700 370 C740 370 780 330 780 290 C780 250 740 220 700 220 C680 170 610 130 540 130 C490 130 430 160 400 200 C370 180 320 180 290 210 C275 220 265 230 260 240 Z" stroke="INK" stroke-width="7" fill="CANVAS"/></g>'
            '<g class="r" style="--d:0.8s"><line x1="280" y1="410" x2="250" y2="470" stroke="MUTED" stroke-width="5"/>'
            '<line x1="360" y1="410" x2="330" y2="470" stroke="MUTED" stroke-width="5"/>'
            '<line x1="440" y1="410" x2="410" y2="470" stroke="MUTED" stroke-width="5"/>'
            '<line x1="520" y1="410" x2="490" y2="470" stroke="MUTED" stroke-width="5"/>'
            '<line x1="600" y1="410" x2="570" y2="470" stroke="MUTED" stroke-width="5"/>'
            '<line x1="680" y1="410" x2="650" y2="470" stroke="MUTED" stroke-width="5"/></g>'
            '<g class="s" style="--d:1.2s"><line x1="740" y1="560" x2="740" y2="380" stroke="INK" stroke-width="6"/>'
            '<rect x="710" y="420" width="60" height="60" rx="8" stroke="MUTED" stroke-width="5" fill="CANVAS"/>'
            '<line x1="710" y1="380" x2="770" y2="380" stroke="MUTED" stroke-width="4"/>'
            '<circle cx="710" cy="380" r="10" stroke="MUTED" stroke-width="4" fill="CANVAS"/>'
            '<circle cx="770" cy="380" r="10" stroke="MUTED" stroke-width="4" fill="CANVAS"/></g>'
            '<g class="p" style="--d:1.6s"><circle cx="740" cy="450" r="14" fill="ACCENT" stroke="none"/></g>'
        ),
    },
]

def main():
    print(f"Validating {len(NEW_SEEDS)} new seeds...")
    errors = []
    for s in NEW_SEEDS:
        name = s["name"]
        motif = s["motif"]
        svg = s["svg"]
        resolved = icons.resolve(motif)
        if resolved != motif:
            errors.append(f"[{name}] motif '{motif}' does not resolve to itself (got '{resolved}')")
        probs = art.scene_problems(svg)
        if probs:
            errors.append(f"[{name}] art.scene_problems: {probs}")
    
    if errors:
        print("FAILURES FOUND:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    
    print("All 26 seeds passed art.scene_problems and motif checks!")
    # Write to assets/drawings
    for s in NEW_SEEDS:
        path = SEEDS_DIR / f"{s['name']}.json"
        data = {
            "motif": s["motif"],
            "about": s["about"],
            "svg": s["svg"]
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path.name}")

if __name__ == "__main__":
    main()
