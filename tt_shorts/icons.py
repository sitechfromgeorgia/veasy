"""Icons and pictograms (ROADMAP C7, D3): a visual vocabulary for every story, without photos.

    assets/icons/lucide.json   250 Lucide stroke icons on a 24 px grid (ISC; tools/build_icons.py rebuilds it)
    STEMS                      Georgian stem -> icon, tolerant of case endings (გაზი, გაზის, გაზით... -> flame)
    VERBS                      what a `sign` scene shows happening to its icon, with the Georgian stems that say it

The writer names an icon by its English name (flame, train-front) or by the Georgian word for the thing (გაზი,
მეტრო); resolve() turns either into a library name. Three places draw icons:
  sign     one pictogram that draws itself stroke by stroke, then its verb plays (stops: a bar closes across it)
  stat     with "icon", a count of 2-30 whole things is drawn as that many icons (isotype); never "1 icon = N"
  motif    the story's main icon tiled faintly in the background (variety.py's "icons" motif)

News rule N10 (news_check.pictograms): a sign's verb must be said in its part of the narration, and there are no
pictograms at all for the crime family (crime, incidents) or for stories about deaths.

Matching: a token matches the longest stem it starts with; a stem that maps to None blocks a shorter one (გაზეთი is a
newspaper, not gas; გაზრდა is growth). A stem ending in "=" matches only that exact token (მთა=, not მთავრობა).
"""
import functools
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "assets" / "icons" / "lucide.json"
ISOTYPE = (2, 30)  # a stat value in this range is drawn as that many icons; outside it, the bar
MOTIONS = ("draw", "pop", "pulse", "count", "morph", "sketch")
DEFAULT_MOTION = "draw"

# icon -> Georgian stems (nominative minus its ending, so every case and postposition matches)
_BY_ICON = {
    # energy
    "flame": "გაზ ცეცხლ ხანძარ ხანძრ ალის გაზსადენ გაზმომარაგებ აირი= აირის= აირით= აირმა=",
    "zap": "დენ ელექტრო ელექტროენერგ ენერგ ძაბვ ჰიდროენერგ გენერაცი",
    "zap-off": "უშუქობ ელექტროგათიშვ",
    "lightbulb": "ნათურ განათებ შუქ ინოვაცი",
    "utility-pole": "ელექტროგადამც ბოძ",
    "solar-panel": "მზის_პანელ სოლარ",
    "fuel": "საწვავ ბენზინ დიზელ საწვავგასამართ ავტოგასამართ ნავთობპროდუქტ",
    "dam": "კაშხალ კაშხლ ჰეს ჰიდროელექტრო",
    "factory": "ქარხან საწარმო ინდუსტრი მრეწველ",
    "atom": "ატომ ბირთვულ",
    "radiation": "რადიაცი",
    "heater": "გათბობ გამათბობ გათბობის_სისტემ",
    "gauge": "მრიცხველ",
    "cylinder": "ბალონ",
    "barrel": "ნავთობ ბარელ",
    "battery": "ბატარე აკუმულატორ",
    "battery-charging": "დატენვ",
    "ev-charger": "ელექტრომობილ დამტენ ელექტროდამტენ",
    "power": "ჩართვ გამორთვ ძალაუფლებ",
    "plug-zap": "როზეტ შტეფსელ",
    # water and waste
    "droplet": "წყალ წყლ სასმელ_წყალ სარწყავ მორწყვ",
    "droplets": "ნალექებ ტენიანობ ცვარ",
    "faucet": "ონკან წყალსადენ წყალმომარაგებ წყალსაქაჩ მილგაყვანილობ",
    "waves-horizontal": "მდინარ ზღვ ტბა= ტბის= ტბაზე= ტბაში= წყალდიდობ ღვარცოფ შტორმ ზვირთ ტალღ",
    "trash": "ნაგავ ნაგვ ნარჩენ ნაგავსაყრელ",
    "recycle": "გადამუშავებ",
    "construction": "მშენებლობ რემონტ სარემონტო რეაბილიტაცი სამშენებლო_ნებართვ დეველოპერ ინფრასტრუქტურ",
    "hard-hat": "მშენებელ",
    # transport
    "bus": "ავტობუს მიკროავტობუს მარშრუტკ ავტოპარკ მუნიციპალურ_ტრანსპორტ",
    "train-front": "მეტრო მატარებ ელმატარებ ვაგონ მატარებლის_მოძრაობ რკინიგზელ",
    "train-track": "რკინიგზ",
    "tram-front": "ტრამვა",
    "car": "მანქან ავტომობილ ავტო მძღოლ ავტომანქან ტრანსპორტ სატრანსპორტო",
    "car-taxi-front": "ტაქს",
    "truck": "სატვირთ ტვირთ ტრაილერ",
    "bike": "ველოსიპედ ველორბოლ",
    "scooter": "სკუტერ სამოკატ",
    "plane": "თვითმფრინავ ფრენ ავიაკომპანი ავია უვიზო ჩარტერ ავიარეის ფრენებ",
    "plane-takeoff": "აეროპორტ აფრენ ტერმინალ",
    "ship": "გემ ბორან",
    "anchor": "ნავსადგურ პორტ",
    "cable-car": "საბაგირო ბაგირ",
    "helicopter": "ვერტმფრენ",
    "traffic-cone": "საცობ შეზღუდვ საგზაო_სამუშაო",
    "road": "საგზაო გზატკეცილ ქუჩ მაგისტრალ ავტომაგისტრალ გზაგამტარ ასფალტ სავალ_ნაწილ",
    "route": "გზ მარშრუტ",
    "bridge": "ხიდ ესტაკად ესტაკადის გადასასვლელ",
    "map": "რუკ რაიონ ტერიტორი",
    "map-pin": "მისამართ უბან",
    "circle-parking": "პარკირ ავტოსადგომ",
    "ticket": "ბილეთ მგზავრობ ვაუჩერ",
    "luggage": "ბარგ ტურისტ ტურიზმ მოგზაურ ემიგრაცი ემიგრანტ მიგრანტ",
    "footprints": "ქვეით ტროტუარ ტროტუარზე ფეხით_მოსიარულ",
    "accessibility": "შშმ ეტლ პანდუს ადაპტირებ",
    "tractor": "ტრაქტორ მეურნეობ ფერმ",
    "container": "კონტეინერ იმპორტ ტვირთბრუნვ ლოგისტიკ",
    "ship-cargo": "ექსპორტ",
    "signpost": "ნიშნულ მიმართულებ მაჩვენებელ",
    "door-open": "შესასვლელ კარი_გაღებ",
    "door-closed": "გასასვლელ კარი_ჩაკეტ",
    "package": "ამანათ პაკეტ გზავნილებ",
    # health
    "hospital": "საავადმყოფო კლინიკ ჰოსპიტალ ამბულატორი სამშობიარო სტაციონარ პოლიკლინიკ",
    "ambulance": "სასწრაფო რეანიმობილ გადაუდებელ",
    "stethoscope": "ექიმ მედიცინ სამედიცინო ქირურგ თერაპევტ პედიატრ ექთან",
    "heart-pulse": "ჯანმრთელობ ჯანდაცვ რეანიმაცი პულს",
    "heart": "გულ",
    "syringe": "ვაქცინ აცრ იმუნიზაცი ვაქცინაცი შრატ",
    "pill": "წამალ წამლ მედიკამენტ ანტიბიოტიკ ფარმაცევტ ფარმაცი",
    "pill-bottle": "აფთიაქ",
    "thermometer": "ტემპერატურ გრადუს ავადმყოფობ",
    "virus": "ვირუს კოვიდ გრიპ ეპიდემი პანდემი ინფექცი ბაქტერი",
    "brain": "ტვინ",
    "microscope": "მეცნიერ კვლევ ლაბორატორი გენეტიკ დნმ",
    "baby": "ბავშვ ახალშობილ შობადობ ბაგა საბავშვო ახალშობილებ დეკრეტ დედობ",
    "eye": "თვალ",
    "hand-heart": "ქველმოქმედ დახმარებ ჰუმანიტარულ სოციალურ_დახმარებ",
    "heart-handshake": "მოხალისე",
    # schools
    "school": "სკოლ სასწავლ საჯარო_სკოლ გიმნაზი ლიცეუმ",
    "backpack": "მოსწავლ ზურგჩანთ სასკოლო სახელმძღვანელო",
    "presentation": "მასწავლებ პედაგოგ ლექცი სემინარ პრეზენტაცი",
    "graduation-cap": "განათლებ სტუდენტ აბიტურიენტ მაგისტრატურ ბაკალავრიატ დოქტორანტურ დიპლომ",
    "university": "უნივერსიტეტ აკადემი კოლეჯ ფაკულტეტ რექტორ",
    "clipboard-check": "გამოცდ",
    "book": "წიგნ",
    "book-open": "ლიტერატურ სწავლ სასწავლო_პროცეს სახელმძღვანელოებ",
    "library": "ბიბლიოთეკ",
    "feather": "მწერალ მწერლ პოეზი პოეტ",
    "award": "პრემი ჯილდო",
    "calculator": "მათემატიკ",
    # courts, police, government
    "scale": "სასამართლ კანონ სამართალ სამართლ ომბუდსმენ დამცველ მოსარჩელ მოპასუხ იურისტ ადვოკატ სამართალწარმოებ",
    "gavel": "მოსამართლ ვერდიქტ განაჩენ გადაწყვეტილებ სააპელაციო საკასაციო",
    "landmark": "მთავრობ სამინისტრო პარლამენტ მერი მერმა= საკრებულ ბანკ ძეგლ მუზეუმ მემკვიდრეობ სააგენტო მუნიციპალიტეტ გამგეობ დეპარტამენტ",
    "user": "მინისტრ პრემიერ პრეზიდენტ პრემიერ-მინისტრ ვიცე-პრემიერ თავმჯდომარ",
    "vote": "არჩევნ კენჭისყრ ამომრჩევ ბიულეტენ საარჩევნო რეფერენდუმ საარჩევნო_უბან ცესკო პლებისციტ",
    "flag": "დროშ ჰიმნ სიმბოლიკ",
    "file-text": "კანონპროექტ დოკუმენტ",
    "scroll": "კონსტიტუცი ბრძანებ დადგენილებ რეგულაცი წეს კოდექს საკანონმდებლო ნორმატიულ მუხლ",
    "stamp": "ნებართვ ლიცენზი რეგისტრაცი სალიცენზიო ნებართვის",
    "megaphone": "განცხადებ აქცი საპროტესტო პროტესტ მიტინგ დემონსტრაცი მანიფესტაცი პროტესტანტ შეკრებ",
    "mic": "ინტერვიუ ბრიფინგ პრესკონფერენცი",
    "handshake": "შეთანხმებ ხელშეკრულებ თანამშრომლობ პარტნიორ მემორანდუმ მოლაპარაკების_რაუნდ პარტნიორობ ალიანს",
    "messages-square": "მოლაპარაკებ",
    "id-card": "პირადობ პასპორტ მოქალაქეობ ვიზა= ვიზის= საიდენტიფიკაციო ბინადრობ",
    "shield": "პოლიცი შსს თავდაცვ დაცვ სამხედრ არმი",
    "shield-check": "უსაფრთხოებ კიბერუსაფრთხოებ დაცულობ",
    "shield-alert": "კიბერ",
    "siren": "პატრულ",
    "search": "გამოძიებ",
    "ban": "აკრძალ სანქცი ემბარგო",
    "fence": "საზღვარ საზღვრ ღობე სასაზღვრო დემარკაცი",
    "crown": "მეფ დედოფალ მონარქ",
    "newspaper": "გაზეთ ჟურნალისტ მედი",
    "tv": "ტელევიზი ტელეკომპანი არხ სერიალ",
    "radio": "რადიო",
    "mail": "ფოსტ ელფოსტ წერილ გზავნილ",
    "users": "მოქალაქე მოსახლეობ ადამიან ხალხ მგზავრ თანამშრომ საზოგადოებ ოჯახ",
    "languages": "ენა= ენის= ენაზე= ენებ თარგმან მთარგმნ",
    # money and prices
    "banknote": "ლარ ფულ ეროვნული_ბანკ ნაღდ კუპიურ",
    "banknote-arrow-up": "ხარჯვ გაძვირებ ფასმატებ",
    "banknote-arrow-down": "შემოდინებ გაიაფებ შემოსავლის_ზრდ",
    "dollar-sign": "დოლარ",
    "euro": "ევრო",
    "georgian-lari": "ვალუტ",
    "coins": "მონეტ თანხ ინვესტიცი ხურდ თეთრი= თეთრის= თეთრზე=",
    "hand-coins": "დაფინანსებ სესხ პენსი სუბსიდი გრანტ თანადაფინანსებ გრანტებ დონორ",
    "wallet": "ბიუჯეტ ხელფას შემოსავალ შემოსავლ საბიუჯეტო სახელფასო დაგროვებ",
    "credit-card": "ბარათ ბანკომატ გადახდ კრედიტ უნაღდო ტერმინალებ ტრანზაქცი",
    "piggy-bank": "დანაზოგ დეპოზიტ ანაბარ საპენსიო ანაბრებ დანაზოგებ",
    "receipt": "გადასახად დღგ საშემოსავლო ჯარიმ ხარჯ ქვითარ ანგარიშ საგადასახადო დეკლარაცი ბაჟ",
    "tag": "ფას ტარიფ საფასურ ღირებულებ",
    "badge-percent": "ფასდაკლებ აქციებ ფასდაკლების",
    "percent": "პროცენტ",
    "trending-up": "ინფლაცი მოგებ ეკონომიკური_ზრდ რეკორდულ",
    "trending-down": "ზარალ რეცესი დეფიციტ",
    "chart-line": "ეკონომიკ აქციონერ ბირჟ",
    "chart-column": "მშპ სტატისტიკ საქსტატ",
    "store": "მაღაზი ბაზარ ვაჭრობ სავაჭრო_ცენტრ სავაჭრო",
    "shopping-cart": "სუპერმარკეტ მყიდველ მომხმარებ საყიდლ სავაჭრო_ქსელ რითეილ",
    "shopping-basket": "პროდუქტ",
    "briefcase": "ბიზნეს სამსახურ დასაქმებ უმუშევრ ვაკანსი ოფის დასაქმებულ შრომით დამსაქმებელ",
    "briefcase-business": "კომპანი კორპორაცი ჰოლდინგ",
    "bitcoin": "ბიტკოინ კრიპტო",
    "key": "ქირ პაროლ",
    # weather
    "sun": "მზე მზის= მზით= მზიან ზაფხულ გვალვ ანომალიურ_სიცხ მზის_დარტყმ",
    "moon": "მთვარ ღამე= ღამის= ღამით=",
    "cloud": "ღრუბ მოღრუბლ",
    "cloud-rain": "წვიმ ნალექ კოკისპირ წვიმიან თავსხმ შხაპუნ",
    "cloud-lightning": "ჭექა ქუხილ ელვ მეხ ჭექა-ქუხილ",
    "snowflake": "თოვლ თოვ ყინულ ზამთარ ზამთრ ყინვებ მოყინულობ დიდთოვლობ",
    "cloud-fog": "ნისლ",
    "cloud-hail": "სეტყვ",
    "wind": "ქარ ჰაერ ქარიშხლიან შტორმულ",
    "tornado": "ქარიშხალ ქარიშხლ ტორნადო გრიგალ ტორნადოს ქარბორბალ",
    "umbrella": "ქოლგ",
    "thermometer-sun": "სიცხ კლიმატ",
    "thermometer-snowflake": "სიცივ ყინვ",
    "haze": "დაბინძურებ",
    "cloud-sun": "ამინდ",
    "mountain-snow": "ზვავ მყინვარ სათხილამურო გუდაურ ბაკურიან ზვავსაშიშროებ",
    "mountain": "მთა= მთის= მთაში= მთაზე= მთები= მთებ მთიან მეწყერ",
    "activity": "მიწისძვრ სეისმურ მიწისქვეშა_ბიძგ",
    # buildings
    "house": "სახლ საცხოვრებ უძრავ იპოთეკ საკარმიდამო აგარაკ კოტეჯ",
    "building": "შენობ კორპუს ბინ მრავალსართულიან საცხოვრებელი_კორპუს",
    "building-complex": "კომპლექს ქალაქ",
    "houses": "დასახლებ სოფელ სოფლ",
    "hotel": "სასტუმრო ჰოსტელ სასტუმრო_კომპლექს",
    "warehouse": "საწყობ ლოგისტიკურ_ცენტრ ტერმინალის_საწყობ",
    "church": "ეკლესი ტაძარ ტაძრ მონასტერ მონასტრ საპატრიარქო პატრიარქ ჯვარ",
    "mosque": "მეჩეთ",
    "castle": "ციხესიმაგრ",
    "tent": "კარავ კარვ ბანაკ",
    "brick-wall": "კედელ კედლ",
    # nature
    "tree-pine": "ტყე ტყის= შობ ნაძვ წიწვოვან",
    "tree-deciduous": "ხე= ხეს= ხემ= ხეებ",
    "trees": "ნაკრძალ პარკ სკვერ სატყეო ეროვნული_პარკ",
    "leaf": "ფოთოლ ფოთლ შემოდგომ ეკოლოგი გარემო",
    "sprout": "გაზაფხულ ნერგ გამწვანებ",
    "flower": "ყვავილ ბაღ",
    "fish": "თევზ",
    "bird": "ფრინველ ჩიტ",
    "dog": "ძაღლ",
    "cat": "კატა= კატას= კატის= კატებ",
    "paw-print": "ცხოველ ვეტერინარ მიუსაფარ ზოოპარკ",
    "bug": "მწერ ფაროსან ხარვეზ ჰაკერ",
    "wheat": "ხორბალ ხორბლ მარცვლეულ პურ მოსავალ მოსავლ მარცვალ მარცვლ სასურსათო",
    "apple": "ვაშლ",
    "grape": "ყურძენ ყურძნ რთველ ვაზი= ვაზის= ვენახ რთველის",
    "wine": "ღვინ მეღვინეობ ღვინის_ქარხან",
    "amphora": "ქვევრ მარან არქეოლოგ ქვევრის ღვინის_მარან",
    "carrot": "ბოსტნეულ კარტოფილ",
    "earth": "დედამიწ",
    "globe": "მსოფლიო გლობალურ საერთაშორისო ევროპ საიტ ვებგვერდ",
    # sport
    "trophy": "ჩემპიონ გამარჯვებ თასი= თასის= თასზე= ტურნირ კალათბურთ ჩოგბურთ",
    "medal": "მედალ ოლიმპიურ ოლიმპიად",
    "goal": "ფეხბურთ საფეხბურთო გოლ სტადიონ",
    "volleyball": "ფრენბურთ",
    "rugby-ball": "რაგბ",
    "dumbbell": "სპორტ ფიტნეს ძალოსნ ჭიდაობ ძიუდო",
    "whistle": "მატჩ მწვრთნელ",
    "shirt": "ნაკრებ მოთამაშ",
    "chess-knight": "ჭადრაკ",
    "waves-ladder": "ცურვ აუზ",
    "sport-shoe": "მარათონ სირბილ",
    # culture
    "theater": "თეატრ ოპერ",
    "drama": "სპექტაკლ ბალეტ მსახიობ",
    "music": "მუსიკ სიმღერ ორკესტრ ჯაზ",
    "mic-vocal": "კონცერტ მომღერალ მომღერლ ევროვიზი",
    "guitar": "გიტარ",
    "piano": "პიანინ ფორტეპიანო",
    "film": "ფილმ",
    "clapperboard": "კინო რეჟისორ",
    "camera": "ფოტო კამერ",
    "cctv": "ვიდეოკამერ ვიდეოთვალთვალ",
    "video": "ვიდეო",
    "palette": "ხელოვნებ მხატვარ მხატვრ ნახატ გამოფენ გალერე",
    "party-popper": "ფესტივალ დღესასწაულ საახალწლო",
    "star": "ვარსკვლავ რეიტინგ",
    "sparkles": "ბრწყინვალ სისუფთავ",
    "chef-hat": "მზარეულ",
    "utensils": "რესტორან საკვებ კვებ სადილ",
    "coffee": "კაფე ყავ",
    "parasol": "კურორტ პლაჟ",
    "dices": "აზარტ კაზინო",
    "gamepad": "ვიდეოთამაშ",
    "gift": "საჩუქარ საჩუქრ",
    # tech
    "microchip": "ჩიპ ნახევარგამტარ პროცესორ ვიდეობარათ მიკროპროცესორ ნანოტექნოლოგ",
    "smartphone": "ტელეფონ სმარტფონ მობილურ აპლიკაცი მობილურის მესენჯერ გაჯეტ",
    "laptop": "ლეპტოპ ნოუთბუქ კომპიუტერ კომპიუტერულ პერსონალურ_კომპიუტერ",
    "wifi": "ინტერნეტ უსადენო ინტერნეტკავშირ პროვაიდერ",
    "bot": "რობოტ ჩატბოტ ხელოვნური_ინტელექტ ალგორითმ",
    "brain-circuit": "ინტელექტ",
    "server": "სერვერ",
    "database": "მონაცემ მონაცემთა_ბაზ სერვერულ რეესტრ",
    "code": "კოდ პროგრამისტ პროგრამირებ პითონ დეველოპმენტ",
    "satellite": "თანამგზავრ ორბიტ კოსმოსურ",
    "rocket": "კოსმოს სტარტაპ",
    "radio-tower": "ანძ კავშირგაბმულობ ოპერატორ სატელეკომუნიკაციო ფიჭურ",
    "network": "ქსელ",
    "drone": "დრონ უპილოტო კვადროკოპტერ",
    "headphones": "ყურსასმენ",
    "robot-arm": "ავტომატიზაცი",
    "lock": "დაშიფვრ უსაფრთხო_კავშირ კიბერდაცვ",
    "lock-open": "განბლოკვ",
    # time and signals
    "calendar": "კალენდარ თარიღ",
    "calendar-clock": "გრაფიკ",
    "clock": "საათ",
    "hourglass": "ვად",
    "timer": "წუთ",
    "bell": "შეტყობინებ",
    "triangle-alert": "საფრთხ გაფრთხილებ ავარი",
}
# Longer words that share a stem's start but mean something else: they block it (None) or name their own icon above.
_BLOCK = ("გაზრდ გაზიარ გაზაფხ ქართ ქარტ ქარავ ქარიზმ მზერ ავტორ ავტონომ ავტომატ გზავნ ფასად ფასეულ დენონს "
          "ზღვარ ტყემალ ბინძურ ბინადარ მერიდიან პორტალ პორტრეტ პორტფელ პორტუგალ გემო გემრიელ გამოცდილ ოპერაცი "
          "ოპერატიულ გულისხმ გულშემატკივ გულწრფელ გულგრილ ბაღდად წესრიგ ფერმენტ არხეოლოგ შუქნიშ ბანკეტ "
          "თვალსაზრის მედიატორ გოლფ ტარებ ენერგიულ გაზიან ბაზრობ სალარო კოდირებ")
STEMS = {}
for _icon, _stems in _BY_ICON.items():
    for _s in _stems.split():
        STEMS[_s.replace("_", " ")] = _icon
for _s in _BLOCK.split():
    STEMS.setdefault(_s, None)
# words whose short stem would be ambiguous, as exact words (ჯარი the army, not ჯარიმა the fine)
STEMS.update({"ჯარი=": "shield", "ჯარის=": "shield", "ჯარისკაც": "shield", "ვალი=": "receipt", "ვალის=": "receipt",
              "ვალებ": "receipt", "მედიკოს": "stethoscope"})
_PAIRS = {s: v for s, v in STEMS.items() if " " in s and v}  # two-word stems (მზის პანელი: solar, not the sun)

# sign verbs -> the Georgian stems that say them (found anywhere in a word: prefixes like გა-, შე-, და- come first)
VERBS = {
    "rises": ("გაიზარდ", "იზრდებ", "გაზრდ", "ზრდა", "ზრდის", "მოიმატ", "იმატებ", "მატულობ", "მომატებ", "გაძვირ",
              "ძვირდებ", "აიწი", "მაღლდებ", "ამაღლდ"),
    "falls": ("შემცირ", "მცირდებ", "კლებ", "იკლო", "იკლებ", "დაიკლ", "დაეც", "გაიაფ", "იაფდებ", "ვარდნ",
              "ჩამოვარდ", "დაბლდ"),
    "stops": ("შეწყდ", "შეუწყდ", "წყდებ", "შეწყვ", "შეუწყვ", "შეჩერ", "შეაჩერ", "ჩერდებ", "გაითიშ", "გათიშ",
              "ითიშებ"),
    "opens": ("გაიხსნ", "გახსნ", "იხსნებ", "გაეხსნ", "გაიღო", "აღდგ", "აღადგ", "ჩაირთ", "ირთვებ", "ამოქმედ"),
    "closes": ("დაიხურ", "დახურ", "იხურებ", "იკეტ", "ჩაკეტ", "გადაკეტ", "დაბლოკ", "იბლოკ"),
    "moves": ("გადავიდ", "გადადი", "გადაიტან", "გადატან", "გადაად", "გადაინაცვლ", "გადანაცვლ", "გადაიყვან",
              "გადაყვან", "გადასვლ", "გადავა", "გადაიდ", "გადადებ"),
    "splits": ("გაიყო", "გაიყოფ", "გაყოფ", "იყოფ", "დაიშალ", "დაშლ", "გაიხლიჩ", "გახლეჩ", "გამოეყო"),
    "joins": ("შეუერთ", "უერთდებ", "შეიერთ", "გაერთიანდ", "გაერთიანებ", "შერწყ", "ერწყმ", "შეერთდ", "უერთდ"),
}
# words that contain a verb stem but say something else (გადაწყდება: it will be decided, not stopped; აღდგომა is
# Easter; გაიყოლა took along; აღზრდა upbringing)
VERBS_NOT = {"stops": ("გადაწყ",), "rises": ("აღზრდ", "ზრდილ"), "falls": ("კლებულ",), "opens": ("აღდგომ",),
             "splits": ("გაიყოლ",), "joins": ("გაერთიანებულ",)}
VERB_WORDS = {"rises": "გაიზარდა, იზრდება, გაძვირდა", "falls": "შემცირდა, იკლებს, გაიაფდა",
              "stops": "შეწყდება, შეჩერდა, გაითიშა", "opens": "გაიხსნება, იხსნება, აღდგა",
              "closes": "დაიხურება, ჩაიკეტა, გადაიკეტა", "moves": "გადავა, გადაიტანეს, გადაიდო",
              "splits": "გაიყო, დაიშალა", "joins": "შეუერთდა, გაერთიანდა"}
VERB_MOTION = {"rises": "it lifts, with an arrow up", "falls": "it sinks, with an arrow down",
               "stops": "a bar closes across it", "opens": "its doors swing open", "closes": "doors close over it",
               "moves": "it travels left to right", "splits": "it splits in two",
               "joins": "two halves come together"}
VERB_ABOUT = {v: f"{VERB_MOTION[v]} ({VERB_WORDS[v]})" for v in VERBS}

_WORD = re.compile(r"[ა-ჰa-z0-9-]+")


@functools.lru_cache(maxsize=1)
def library():
    """name -> [[tag, {attr: value}], ...] on the 24 px grid."""
    return json.loads(LIBRARY.read_text(encoding="utf-8"))["icons"]


def names():
    return sorted(library())


def mapped():
    """Every icon the stem map can produce (the asset must have them all)."""
    return sorted({v for v in STEMS.values() if v})


def unknown():
    """Icons the stem map names that the library lacks: must be [] (tests/test_icons.py)."""
    return [n for n in mapped() if n not in library()]


def words(text):
    return _WORD.findall((text or "").lower())


def _match(token):
    """The icon of one word: its exact entry, else its longest stem; None when nothing (or a blocker) matches."""
    if f"{token}=" in STEMS:
        return STEMS[f"{token}="]
    for n in range(len(token), 1, -1):
        hit = STEMS.get(token[:n], False)
        if hit is not False:
            return hit
    return None


def find(text):
    """The icons a Georgian text names, in the order they first appear: find("გაზის მიწოდება შეწყდება") -> ["flame"]."""
    toks = words(text)
    out = []
    for i, t in enumerate(toks):
        two = f"{t} {toks[i + 1]}" if i + 1 < len(toks) else ""
        hit = next((v for s, v in _PAIRS.items() if two.startswith(s)), None) or _match(t)
        if hit and hit not in out:
            out.append(hit)
    return out


def resolve(value):
    """An icon name or a Georgian word -> a library name, or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    v = value.strip()
    if v in library():
        return v
    found = [n for n in find(v) if n in library()]
    return found[0] if found else None


def nodes(name):
    return library().get(name) if name else None


def said(verb, text):
    """Does the text say the verb? Any of its stems inside a word, unless the word is one of VERBS_NOT's."""
    skip = VERBS_NOT.get(verb, ())
    return any(stem in w for w in words(text) if not any(x in w for x in skip) for stem in VERBS.get(verb, ()))


def isotype(scene):
    """A stat whose value is drawn as that many icons: an icon, a whole number of 2-30 things, not a percent.
    Supports part-of-whole when total is present (e.g. 7 out of 10)."""
    v = scene.get("value")
    if scene.get("type") != "stat" or not resolve(scene.get("icon")):
        return False
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or float(v) != int(v):
        return False
    if "%" in f"{scene.get('prefix') or ''}{scene.get('suffix') or ''}":
        return False
    total = scene.get("total")
    if total is not None:
        if isinstance(total, bool) or not isinstance(total, (int, float)) or not math.isfinite(total) or float(total) != int(total):
            return False
        if not (ISOTYPE[0] <= int(total) <= ISOTYPE[1]) or int(v) > int(total):
            return False
    return ISOTYPE[0] <= int(v) <= ISOTYPE[1]


def scene_problems(s):
    """Shape problems of a sign scene or a stat's icon (engine.shape_problems)."""
    out = []
    t = s.get("type")
    if t == "sign" or s.get("icon") is not None:
        if not resolve(s.get("icon")):
            out.append(f"icon: {s.get('icon')!r} is neither an icon name nor a Georgian word the map knows "
                       f"(engine options -> icons)")
    if t == "sign" and s.get("verb") not in VERBS:
        out.append(f"verb: {s.get('verb')!r}, use one of {', '.join(VERBS)}")
    if s.get("motion") is not None and s.get("motion") not in MOTIONS:
        out.append(f"motion: {s.get('motion')!r}, use one of {', '.join(MOTIONS)}")
    if s.get("morph_from") is not None and not resolve(s.get("morph_from")):
        out.append(f"morph_from: {s.get('morph_from')!r} is neither an icon name nor a Georgian word the map knows")
    if s.get("total") is not None:
        tot = s.get("total")
        val = s.get("value", 0)
        if isinstance(tot, bool) or not isinstance(tot, (int, float)) or not math.isfinite(tot) or tot < val:
            out.append("total: must be a number >= value")
    return out


def motif_problems(story):
    m = story.get("motif")
    if m is not None and not resolve(m):
        return [f"story: motif {m!r} is neither an icon name nor a Georgian word the map knows"]
    return []


def story_problems(story):
    """Every icon problem of a story, for the writer's repair loop (the news side is news_check.pictograms, N10)."""
    out = motif_problems(story)
    for i, s in enumerate(story.get("scenes") or []):
        if s.get("type") in ("sign", "stat"):
            out += [f"scene {i} ({s['type']}): {x}" for x in scene_problems(s)]
    return out


def story_icon(story):
    """The story's main icon: its "motif", else the first icon the hook names, else its first sign's or stat's;
    None when the story may carry no pictograms (N10: crime family, deaths)."""
    from tt_shorts import news_check
    if news_check.no_pictograms(story):
        return None
    scenes = story.get("scenes") or []
    hook = next((s for s in scenes if s.get("type") == "hook"), {})
    candidates = [story.get("motif")] if story.get("motif") else []
    candidates += find(" ".join(str(x) for x in hook.get("lines") or []))
    candidates += [s.get("icon") for s in scenes if s.get("type") in ("sign", "stat") and s.get("icon")]
    return next((n for n in map(resolve, candidates) if n), None)


def attach(scenes, story):
    """Render props: each sign and icon stat gets its icon's nodes ("glyph"); a stat is marked "isotype" when its count
    is drawn as icons. Nothing is attached to a story that may carry no pictograms (N10)."""
    from tt_shorts import news_check
    if news_check.no_pictograms(story):
        return [{k: v for k, v in s.items() if k != "icon"} if s.get("type") == "stat" else s for s in scenes]
    out = []
    for s in scenes:
        if s.get("type") in ("sign", "stat") and resolve(s.get("icon")):
            name = resolve(s["icon"])
            motion = s.get("motion") if s.get("motion") in MOTIONS else DEFAULT_MOTION
            patch = {"icon": name, "glyph": nodes(name), "motion": motion}
            if s.get("morph_from") and resolve(s.get("morph_from")):
                patch["morphGlyph"] = nodes(resolve(s["morph_from"]))
            if s.get("total") is not None:
                patch["total"] = s["total"]
            s = {**s, **patch}
            if s["type"] == "stat":
                s["isotype"] = isotype(s)
        if s.get("type") == "points":
            s = {**s, "glyphs": point_glyphs(s)}
        out.append(s)
    return out


def point_glyphs(s):
    """A points scene's icons, one per item, when every item's own words name a different one; else None and each item
    gets a plain rule. Points have equal weight: they are never numbered (owner, 2026-11-07: „1, 2, 3“ on everything
    bores)."""
    items = [x if isinstance(x, str) else "" for x in s.get("items") or []]
    names = [next((n for n in find(t) if n in library()), None) for t in items]
    if not items or None in names or len(set(names)) < len(names):
        return None
    return [nodes(n) for n in names]


def options():
    """What `engine options` shows an agent."""
    return {"about": "Lucide stroke icons (ISC), named in English or by a Georgian word (the stem map); used by the "
                     "sign scene, a stat's icon (2-30 drawn as that many) and the story's motif. N10: none for crime, "
                     "incidents or deaths",
            "count": len(library()), "verbs": VERB_ABOUT, "motions": list(MOTIONS),
            "charts": ["isotype", "part_of_whole", "unit_chart"],
            "isotype": list(ISOTYPE), "contact_sheet": "python -m tt_shorts.engine contact-sheet", "names": names(),
            "georgian_examples": {"გაზი": "flame", "დენი": "zap", "წყალი": "droplet", "მეტრო": "train-front",
                                  "ავტობუსი": "bus", "სკოლა": "school", "საავადმყოფო": "hospital",
                                  "სასამართლო": "scale", "ფასი": "tag", "ლარი": "banknote", "გზა": "route",
                                  "ხიდი": "bridge", "თოვლი": "snowflake"}}
