#!/usr/bin/env python3
"""Build a private portrait film on Edisher Mzhavanadze.

Facts are limited to the public registry (NAPR through companyinfo.ge),
Geostat, sitech.ge and tbilisi.today. The personal number is used only to
confirm identity and never appears on screen or in the narration.
"""
import json
from pathlib import Path

OUT = Path("/root/.hermes/shared-plugins/veasy/demo/film-edisher-full.json")

DRAW = (
    '<g class="s" style="--d:0.2s">'
    '<line x1="476" y1="320" x2="190" y2="170" stroke="LINE" stroke-width="6"/>'
    '<line x1="476" y1="320" x2="760" y2="170" stroke="LINE" stroke-width="6"/>'
    '<line x1="476" y1="320" x2="476" y2="540" stroke="LINE" stroke-width="6"/>'
    '<line x1="476" y1="320" x2="170" y2="460" stroke="LINE" stroke-width="6"/>'
    '<line x1="476" y1="320" x2="790" y2="460" stroke="LINE" stroke-width="6"/>'
    '</g>'
    '<g class="p" style="--d:0.4s">'
    '<circle cx="476" cy="320" r="76" fill="none" stroke="ACCENT" stroke-width="8"/>'
    '<text x="476" y="327" text-anchor="middle" font-size="28" font-weight="700" fill="INK">ედიშერ</text>'
    '</g>'
    '<g class="s" style="--d:0.7s">'
    '<circle cx="190" cy="170" r="62" fill="none" stroke="INK" stroke-width="6"/>'
    '<text x="190" y="177" text-anchor="middle" font-size="24" font-weight="700" fill="INK">SiTech</text>'
    '<circle cx="760" cy="170" r="72" fill="none" stroke="INK" stroke-width="6"/>'
    '<text x="760" y="177" text-anchor="middle" font-size="24" font-weight="700" fill="INK">tbilisi.today</text>'
    '</g>'
    '<g class="r" style="--d:1.0s">'
    '<circle cx="476" cy="540" r="52" fill="none" stroke="MUTED" stroke-width="6"/>'
    '<text x="476" y="547" text-anchor="middle" font-size="24" font-weight="700" fill="INK">რეესტრი</text>'
    '<circle cx="170" cy="460" r="46" fill="none" stroke="MUTED" stroke-width="6"/>'
    '<circle cx="790" cy="460" r="46" fill="none" stroke="MUTED" stroke-width="6"/>'
    '</g>'
)

SEGMENTS = [
    ({"type": "hook", "kicker": "პორტრეტი", "lines": ["ედიშერ", "მჟავანაძე", "ბათუმიდან"]},
     "ედიშერ მჟავანაძე ბათუმიდან არის SiTech Agency-ის და tbilisi.today-ის დამფუძნებელი. ეს ფილმი მის საჯარო გზასა და პროდუქტებს ეხება."),
    ({"type": "who", "kicker": "ვინ არის", "items": [
        {"name": "SiTech Agency", "role": "ციფრული სააგენტო"},
        {"name": "tbilisi.today", "role": "საინფორმაციო პლატფორმა"}]},
     "ის დგას ციფრული პროდუქტების უკან: ციფრული სააგენტო SiTech და საინფორმაციო პლატფორმა tbilisi.today. ორივე საჯარო გვერდზე მისი სახელით იხსნება."),
    ({"type": "where", "kicker": "სად", "place": "ბათუმი", "sub": "აჭარა · საქართველო",
      "headline": "საწყისი წერტილი"},
     "მისი სამუშაო ბაზა ბათუმია, სადაც დაიწყო პირველი ორგანიზაციები. 2026 წელს ციფრული პროდუქტები აქედან მთელ ქვეყანას ემსახურება."),
    ({"type": "chapter", "n": 1, "of": 3, "kicker": "თავი 1", "lines": ["გზა", "2014", "2026"]},
     "პირველი ნაწილი მის რეგისტრირებულ გზას ეხება, რადგან საჯარო რეესტრი ყველაზე მშრალ და ზუსტ ქრონოლოგიას გვაძლევს."),
    ({"type": "timeline", "kicker": "ქრონოლოგია", "big": "2014 → 2026",
      "start": "2014", "end": "2026", "label": "რეესტრიდან პროდუქტამდე"},
     "საჯარო რეესტრში მისი პირველი ორგანიზაცია 2014 წელს გამოჩნდა, ხოლო 2026 წელს უკვე ხუთ ცოცხალ პროდუქტს უძღვება."),
    ({"type": "rail", "kicker": "ეტაპები", "items": [
        {"when": "5 მარტი 2014", "label": "სანშაინი"},
        {"when": "16 ივნისი 2016", "label": "სინათლის ეპოქა"},
        {"when": "2 აპრილი 2024", "label": "შპს ინფსი"},
        {"when": "2026", "label": "tbilisi.today"}]},
     "ჯერ იყო არასამეწარმეო ორგანიზაცია სანშაინი, შემდეგ სინათლის ეპოქა, 2024 წელს შპს ინფსი, ხოლო 2026 წელს tbilisi.today."),
    ({"type": "who", "kicker": "ორგანიზაციები", "items": [
        {"name": "სანშაინი", "role": "2014, თავმჯდომარე"},
        {"name": "სინათლის ეპოქა", "role": "2016, თავმჯდომარე"}]},
     "სანშაინი 2014 წლის მარტში ბათუმში დარეგისტრირდა, სინათლის ეპოქა კი 2016 წლის ივნისში. ორივეში ის თავმჯდომარეა."),
    ({"type": "sign", "kicker": "ბათუმი", "icon": "building", "verb": "opens",
      "label": "ორი ორგანიზაცია"},
     "ორი არასამეწარმეო ორგანიზაცია ბათუმში გაიხსნა და ორივეს თავმჯდომარეა. რეესტრი მათ აქტიურად აჩვენებს."),
    ({"type": "where", "kicker": "ქობულეთი", "place": "ქობულეთი", "sub": "აჭარა · საქართველო",
      "headline": "შპს ინფსი"},
     "2024 წელს რეესტრში დაემატა შპს ინფსი, რომელიც ქობულეთის რაიონში, სოფელ ხუცუბანშია რეგისტრირებული. ეს არის მისი კომერციული იურიდიული პირი."),
    ({"type": "who", "kicker": "ინფსი", "items": [
        {"name": "ედიშერ მჟავანაძე", "role": "დირექტორი და პარტნიორი"},
        {"name": "შპს ინფსი", "role": "2024, ქობულეთი"}]},
     "შპს ინფსიში ის დირექტორიცაა და პარტნიორიც. კომპანია 2024 წლის ორ აპრილს, GITA-ს რეგიონალური გრანტისთვის დარეგისტრირდა."),
    ({"type": "stat", "kicker": "წილი", "value": 100, "suffix": "%",
      "label": "წილი შპს ინფსიში"},
     "შპს ინფსიში მისი წილი 100 პროცენტია."),
    ({"type": "calendar", "kicker": "რეგისტრაცია", "day": 2, "month": "აპრილი",
      "weekday": "სამშაბათი", "event": "შპს ინფსი", "sub": "2024"},
     "კომპანიის რეგისტრაციის თარიღი 2024 წლის ორი აპრილია."),
    ({"type": "change", "kicker": "ზრდა", "unit": "ერთეული",
      "before": {"label": "2014", "value": 1}, "after": {"label": "2026", "value": 3}},
     "2014 წელს მას ერთი ორგანიზაცია ჰქონდა, 2026 წელს კი სამი."),
    ({"type": "route", "kicker": "გეოგრაფია", "stops": ["ბათუმი", "ქობულეთი"],
      "label": "ორი ქალაქი", "detail": "აჭარა"},
     "მისი იურიდიული პირები ბათუმსა და ქობულეთშია. ეს ორი ქალაქი ერთ რეგიონშია."),
    ({"type": "points", "kicker": "ფორმები", "headline": "სამი ფორმა", "items": [
        "არასამეწარმეო", "შპს", "ინდივიდუალური მეწარმე"]},
     "რეესტრში სამი სამართლებრივი ფორმაა: არასამეწარმეო, შპს და ინდივიდუალური მეწარმე."),
    ({"type": "calendar", "kicker": "მეწარმე", "day": 3, "month": "ოქტომბერი",
      "weekday": "ორშაბათი", "event": "ინდივიდუალური მეწარმე", "sub": "2016"},
     "ინდივიდუალური მეწარმე 2016 წლის სამ ოქტომბერს დარეგისტრირდა."),
    ({"type": "chapter", "n": 2, "of": 3, "kicker": "თავი 2",
      "lines": ["აწყობა", "SiTech", "tbilisi.today"]},
     "მეორე ნაწილი მის პროდუქტებზეა და მათ საჯარო გვერდებზე."),
    ({"type": "checklist", "kicker": "SiTech", "label": "სამი მიმართულება", "items": [
        {"text": "ვებ-განვითარება", "state": "done"},
        {"text": "AI ინტეგრაცია", "state": "done"},
        {"text": "PWA აპლიკაციები", "state": "done"}]},
     "SiTech Agency სამ მიმართულებას აერთიანებს: ვებ, AI და PWA."),
    ({"type": "points", "kicker": "SiTech", "headline": "სამი რიცხვი", "items": [
        "6+ წელი გამოცდილება", "7+ ცოცხალი პროექტი", "1700+ სტატია"]},
     "სააგენტოს გვერდი სამ რიცხვს ასახელებს: 6 წელზე მეტი გამოცდილება, 7-ზე მეტი ცოცხალი პროექტი და 1700-ზე მეტი გამოქვეყნებული სტატია."),
    ({"type": "pair", "kicker": "ორი როლი", "between": "და", "items": [
        {"title": "დამფუძნებელი", "sub": "SiTech Agency, tbilisi.today"},
        {"title": "მეწარმე", "sub": "ინდივიდუალური მეწარმე, 2016"}]},
     "ის ერთდროულად დამფუძნებელიცაა და მეწარმეც, რადგან SiTech ინდივიდუალური მეწარმის სახით მუშაობს."),
    ({"type": "versus", "kicker": "ორი ბრენდი", "between": "VS", "items": [
        {"title": "SiTech Agency", "value": "სააგენტო", "note": "ვებ, AI, PWA"},
        {"title": "tbilisi.today", "value": "პლატფორმა", "note": "23 წყარო, ერთი ნაკადი"}]},
     "ორი ბრენდი ერთი ხელით: SiTech არის სააგენტო, tbilisi.today კი პლატფორმა."),
    ({"type": "draw", "kicker": "რუკა", "svg": DRAW, "label": "ერთი სისტემა",
      "headline": "რეგისტრირებული როლები"},
     "ერთი ადამიანი, რამდენიმე ორგანიზაცია და რამდენიმე პროდუქტი, ეს არის მისი რუკა."),
    ({"type": "chapter", "n": 3, "of": 3, "kicker": "თავი 3",
      "lines": ["პროდუქტები", "5", "ბრენდი"]},
     "მესამე ნაწილი მის პროდუქტებზეა: ჯერ tbilisi.today, შემდეგ დანარჩენი პორტფოლიო."),
    ({"type": "glossary", "kicker": "ტერმინი", "term": "აგრეგატორი",
      "definition": "სიახლეები ერთ სივრცეში", "context": "tbilisi.today"},
     "tbilisi.today არის აგრეგატორი, ანუ აგროვებს სიახლეებს ერთ სივრცეში."),
    ({"type": "stat", "kicker": "წყაროები", "value": 23,
      "label": "ქართული მედია წყარო"},
     "პლატფორმა 23 ქართულ მედია წყაროს ამოწმებს ყოველ რამდენიმე წუთში."),
    ({"type": "points", "kicker": "არქივი", "headline": "პლატფორმის ციფრები", "items": [
        "61,496 სტატია", "16,270 პროფილი"]},
     "2026 წლის ნოემბრის მონაცემებით არქივში 61,496 სტატია და 16,270 პროფილია."),
    ({"type": "sign", "kicker": "ნაკადი", "icon": "newspaper", "verb": "joins",
      "label": "23 წყარო, ერთი ნაკადი"},
     "სხვადასხვა გამოცემის ამბავი ერთ ნაკადში ერწყმის და ერთ ამბად იკრიბება."),
    ({"type": "glossary", "kicker": "კლასტერი", "term": "კლასტერი",
      "definition": "ერთი ამბავი, რამდენიმე წყარო", "context": "tbilisi.today"},
     "სისტემა ერთ მოვლენას რამდენიმე წყაროდან ერთ ამბად აერთიანებს და კონტექსტს აშენებს."),
    ({"type": "stat", "kicker": "კავშირები", "value": 33161,
      "label": "კავშირი პროფილებს შორის"},
     "33,161 კავშირი პროფილებს შორისაა და სისტემა მას ინახავს."),
    ({"type": "quote", "kicker": "ციტატა", "text": "მთელი ეს სისტემა ერთ თვეში ავაწყვეთ",
      "by": "tbilisi.today", "via": "tbilisi.today/support"},
     "მხარდაჭერის გვერდზე წერია: მთელი ეს სისტემა ერთ თვეში ავაწყვეთ. ეს არის მისი ყველაზე მოკლე აღწერა."),
    ({"type": "stat", "kicker": "ერთი თვე", "value": 1,
      "label": "თვეში აწყობილი სისტემა"},
     "ეს ნიშნავს, რომ პლატფორმა ერთ თვეში შეიქმნა. 2026 წელს ის 23 წყაროს და ათასობით სტატიას ემსახურება."),
    ({"type": "quote", "kicker": "რეკლამა", "text": "არც ერთი ბანერი, არც ერთი დაფინანსებული სტატია",
      "by": "tbilisi.today", "via": "tbilisi.today/support"},
     "მხარდაჭერის გვერდი ამბობს: არც ერთი ბანერი, არც ერთი დაფინანსებული სტატია."),
    ({"type": "impact", "kicker": "შედეგი", "target": "მკითხველი",
      "change": "23 წყარო ერთ გვერდზე, რეკლამის გარეშე", "when": "2026"},
     "მკითხველისთვის შედეგი მარტივია: 23 წყარო ერთ გვერდზე, რეკლამის გარეშე."),
    ({"type": "who", "kicker": "პროდუქტები", "items": [
        {"name": "Riger", "role": "რიგის მართვა"},
        {"name": "Staffer", "role": "HR პლატფორმა"},
        {"name": "Uniglot", "role": "სინქრონული თარგმანი"}]},
     "Riger მართავს ცოცხალ რიგს, Staffer თანამშრომლებს, Uniglot კი ღონისძიებებზე სინქრონულ თარგმანს."),
    ({"type": "sign", "kicker": "Riger", "icon": "smartphone", "verb": "opens",
      "label": "რიგი QR-ით"},
     "Riger არის ლაივ რიგის სისტემა, რომელიც QR კოდით იხსნება."),
    ({"type": "glossary", "kicker": "Uniglot", "term": "Uniglot",
      "definition": "სინქრონული თარგმანი", "context": "ღონისძიებები"},
     "Uniglot თარგმნის სინქრონულად, წინადადების დასრულებიდან ერთ ან ორ წამში."),
    ({"type": "where", "kicker": "SiTeach", "place": "ბათუმი", "sub": "AI სკოლა",
      "headline": "SiTeach"},
     "SiTeach არის ბათუმში მდებარე AI სკოლა, სადაც ინტენსივები და ვორქშოპები ტარდება."),
    ({"type": "sign", "kicker": "SiChat", "icon": "network", "verb": "opens",
      "label": "SiChat პანელი"},
     "SiChat არის გუნდური კომუნიკაციის პანელი, რომელიც ერთ სივრცეში იხსნება."),
    ({"type": "versus", "kicker": "ორი სახელი", "between": "VS", "items": [
        {"title": "SiTech", "value": "სააგენტო", "note": "ვებ, AI, PWA"},
        {"title": "SiTeach", "value": "სკოლა", "note": "AI ინტენსივები"}]},
     "SiTech არის სააგენტო, SiTeach კი AI სკოლა. სახელები ახლოსაა, საქმეები სხვადასხვა."),
    ({"type": "stat", "kicker": "პორტფოლიო", "value": 5,
      "label": "ცოცხალი პროდუქტი"},
     "ხუთი ცოცხალი პროდუქტი უკვე წარმატებით მუშაობს."),
    ({"type": "quote", "kicker": "მომავალი", "text": "მე ვაშენებ მომავალს",
      "by": "ედიშერ მჟავანაძე", "via": "2026"},
     "მისი სიტყვებით, ის ყოველდღე აშენებს მომავალს."),
    ({"type": "checklist", "kicker": "ღირებულებები", "label": "ოთხი ღირებულება", "items": [
        {"text": "მიზანზე ორიენტირება", "state": "done"},
        {"text": "ხარისხი", "state": "done"},
        {"text": "სიჩქარე", "state": "done"},
        {"text": "თანამშრომლობა", "state": "done"}]},
     "ოთხი ღირებულება: მიზანზე ორიენტირება, ხარისხი, სიჩქარე, თანამშრომლობა. ეს მისი საჯარო პრინციპებია."),
    ({"type": "quote", "kicker": "პრინციპი",
      "text": "თითოეული ბიზნესი იმსახურებს პროფესიონალურ ციფრულ სივრცეს",
      "by": "SiTech", "via": "sitech.ge"},
     "სააგენტოს პრინციპი ასეა ჩამოწერილი: თითოეული ბიზნესი იმსახურებს პროფესიონალურ ციფრულ სივრცეს. ეს არის მისი სამუშაოს საწყისი წერტილი."),
    ({"type": "sources", "kicker": "წყაროები", "headline": "რეესტრი, პროდუქტები და ავტორი"},
     "ყველა ფაქტი საჯარო რეესტრიდან, პროდუქტების გვერდებიდან და ავტორის განცხადებიდან არის აღებული."),
    ({"type": "end", "kicker": "სტარტაპერი",
      "lines": ["ედიშერ", "მჟავანაძე", "5 პროდუქტი"]},
     "ედიშერ მჟავანაძე, ხუთი ცოცხალი პროდუქტი. ბათუმი, საქართველო."),
]


def main():
    narration = " ".join(s for _, s in SEGMENTS)
    scenes = []
    for sc, sentence in SEGMENTS:
        words = sentence.split()
        at = None
        for length in range(6, len(words) + 1):
            candidate = " ".join(words[:length])
            if narration.count(candidate) == 1:
                at = candidate
                break
        assert at is not None, sentence
        sc = dict(sc)
        sc["at"] = at
        scenes.append(sc)
    positions = [narration.find(s["at"]) for s in scenes]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), positions
    story = {
        "id": 900024,
        "lang": "ka",
        "category": "tech",
        "date": "2026-11-05T05:30:00+04:00",
        "url": "https://sitech.ge/ka/about/",
        "sources": ["NAPR", "საქსტატი", "companyinfo.ge", "sitech.ge", "tbilisi.today", "riger.live", "staffer.live", "uniglot.live", "siteach.live", "sichat.live", "ედიშერ მჟავანაძე"],
        "private": True,
        "brand": "sitech",
        "format": "film",
        "look": "kinetic",
        "theme": "light",
        "captions": "roll",
        "director": "chronicle",
        "music": "tech",
        "sfx": "on",
        "narration": narration,
        "scenes": scenes,
        "say": {
            "SiTech": "საითეჩ",
            "Agency": "ეიჯენსი",
            "tbilisi.today": "თბილისი თუდეი",
            "PWA": "პი დაბლიუ ეი",
            "AI": "ეი აი",
            "SEO": "ეს ეი ოუ",
            "GITA": "გიტა",
            "Riger": "რიგერ",
            "Staffer": "სტაფერ",
            "Uniglot": "იუნიგლოტ",
            "SiTeach": "საითიჩ",
            "SiChat": "საიჩატ",
            "QR": "ქიუ არ",
        },
    }
    OUT.write_text(json.dumps(story, ensure_ascii=False, indent=1))
    print("words", len(narration.split()), "scenes", len(scenes), "types", len({s['type'] for s in scenes}), "->", OUT)


if __name__ == "__main__":
    main()
