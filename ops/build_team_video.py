"""A short about the newsroom team itself: one human, three agents, one memory."""
import json
import pathlib

NARRATION = (
    "ეს არის რედაქცია, სადაც ადამიანი ერთია. "
    "რედაქტორი ამოწმებს ქართულს. "
    "მკვლევარი ამოწმებს ფაქტებს. "
    "პროდიუსერი ამოწმებს ვიდეოს. "
    "რედაქტორს ქართული კარიბჭე აქვს. "
    "მკვლევარს კანონი და რეესტრები. "
    "პროდიუსერს ვიდეოს ძრავა. "
    "მე ვაკოორდინირებ და ვაქვეყნებ. "
    "ყველა ერთ სისტემაზე მუშაობს. "
    "საერთო მეხსიერება, საერთო წესები და საერთო ხმა. "
    "თითოეული თავის საქმეს აკეთებს და შედეგს მე გადმოსცემს. "
    "ადამიანი წყვეტს, რა გამოქვეყნდეს. "
    "დანარჩენს სისტემა აკეთებს. "
    "tbilisi.today მუშაობს გამუდმებით."
)

SCENES = [
    {"type": "hook", "at": "ეს არის რედაქცია",
     "kicker": "გუნდი", "lines": ["რედაქცია,", "სადაც", "ადამიანი ერთია"]},
    {"type": "points", "at": "რედაქტორი ამოწმებს ქართულს",
     "kicker": "სამი როლი", "items": ["რედაქტორი: ქართული", "მკვლევარი: ფაქტები", "პროდიუსერი: ვიდეო"]},
    {"type": "points", "at": "რედაქტორს ქართული კარიბჭე აქვს",
     "kicker": "ხელსაწყოები", "items": ["ქართული კარიბჭე", "კანონი და რეესტრები", "ვიდეოს ძრავა"]},
    {"type": "points", "at": "ყველა ერთ სისტემაზე მუშაობს",
     "kicker": "საერთო", "items": ["მეხსიერება", "წესები", "ხმა"]},
    {"type": "points", "at": "ადამიანი წყვეტს",
     "kicker": "გადაწყვეტილება", "items": ["ადამიანი წყვეტს", "სისტემა ასრულებს"]},
    {"type": "end", "at": "tbilisi.today მუშაობს"},
]

story = {
    "id": 900002,
    "lang": "ka",
    "category": "tech",
    "date": "2026-11-03T10:00:00+04:00",
    "url": "https://tbilisi.today/support",
    "sources": ["tbilisi.today"],
    "narration": NARRATION,
    "scenes": SCENES,
    "say": {},
}
pathlib.Path("demo/team-video.json").write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
print("words", len(NARRATION.split()))
