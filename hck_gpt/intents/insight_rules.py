"""hck_gpt.intents.insight_rules - questions that want a conclusion (2026-11-17).

From the 63-question library of the third long test (2026-11-17). These
phrasings ask "is my PC fine / what limits it / can I trust this", and the
answers live in hck_gpt.responses.r_insight.

route_insight(text) is used twice:
  * by semantic_rules, first in the chain, for ordinary phrasings;
  * by the response builder, for exact vocabulary phrases that the parser
    keeps under their old intent (the vocabulary trains the classifier and
    stays unchanged; see the memory note on hck_GPT vocabulary).
Text is folded first: lower case, no Polish letters, no punctuation.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


def fold(text: str) -> str:
    value = "".join(c for c in unicodedata.normalize("NFD", (text or "").lower())
                    if unicodedata.category(c) != "Mn")
    value = value.translate(str.maketrans({"ł": "l"}))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s.-]", " ", value)).strip()


_PC = r"(komputer\w*|kompa?\w*|pc\w*|pecet\w*|sprzet\w*|laptop\w*|computer|machine)"

# names of PC Workman's own features (hck_gpt.responses.r_features)
_FEAT = (r"(oczyszczani\w*|raport\w* zdrowia|health report|twoj\w* profil|centrum (informacji o )?proces\w*|process (information )?cent(er|re)|deep ?monitor\w*|nagrani\w*|nagrywani\w*|obserwacj\w*|fan ?dashboard|fan ?control|centrum ac|"
         r"monitoring (i |and )?learning|learning center|centrum nauki|nakladk\w*|overlay\w*|mini ?overlay|mini ?monitor|"
         r"activity ?memory|pamiec\w* aktywnosci|silnik turbo|turbo|process ?guard|responsiveness ?guard|hibernac\w*|"
         r"app hibernation|ram ?flush|flush ram|upgrade ?readiness|map\w* (pc|komputera)|test\w* stabilnosc\w*|"
         r"stability tests?|recent ?events?|ostatnie zdarzeni\w*|hck ?labs|startup ?manager|services ?manager)")

# internet words for the network intents (hck_gpt/responses/r_network.py)
_NET = r"(internet\w*|\bnet\b|neta|necie|wi ?fi|siec\w*|polaczeni\w*|lacz\w*|connection|router\w*)"

RULES = [
    # ── fifth long test (2026-11-17): the program's own features ───────────
    ("observe_start", r"^(nagrywaj|nagraj|record|start recording)$"),
    ("feature_info", r"^(a |ok )?(czym (jest|sa)|co to( jest| za)?|co robi|do czego (sluzy|jest)|jak dziala|"
                     r"what is|what s|what does|explain) (ten |ta |to )?" + _FEAT),
    ("feature_info", r"^" + _FEAT + r"( w (pc ?workman\w*|programie))?$"),
    ("app_capabilities", r"co (moge|mozna|da sie) (tu )?(robic|zrobic) (w|z) (tym )?(programie|pc ?workman\w*|aplikacji)|"
                         r"co (potrafi|umie|oferuje|robi) (ten )?(program|pc ?workman|aplikacja)|"
                         r"jakie (sa |ma )?(funkcje|mozliwosci|opcje) (ma )?(ten )?(program\w*|pc ?workman\w*|aplikacj\w*)|"
                         r"(funkcje|mozliwosci) (programu|pc ?workman\w*|aplikacji)|"
                         r"what can i do (in|with) (the app|pc ?workman|this program|it)|what does pc ?workman do|(app|program) features"),
    # ── internet, tested first (2026-11-20, hck_gpt/responses/r_network.py) ──
    ("network_speed", r"(predkosc\w*|szybkosc\w*|transfer\w*) (mojego |mego )?(internet\w*|neta|lacza|pobierania|wi ?fi)|"
                      r"speed ?test\w*|speedtest|internet speed|download speed|how fast is (my )?(internet|connection|wifi)|"
                      r"jak szybki (jest )?(moj |mi )?(internet|net|wi ?fi)|zmierz (mi )?(predkosc|szybkosc|internet)|"
                      r"ile (mam |daje )?(mega|mb ?s|mbps|megabit)\w*|test predkosci"),
    ("network_dns", r"(wyczysc|wyczyscic|czyszczenie|flush|odswiez)\w* (pamiec\w* |cache )?dns|dns (nie dziala|problem|blad)|"
                    r"flush ?dns|dns (cache|error)"),
    ("network_down", r"(nie mam|brak|bez|zero) (dostepu do )?(internet\w*|neta|wi ?fi|sieci|polaczenia)|"
                     r"(internet|net|neta|wi ?fi|siec|router)\w* (mi )?(nie dziala|padl|padl\w*|nie ma|lezy|nie odpowiada|nie laduje|wysiadl\w*|nie idzie)|"
                     r"(strony|strona|youtube|przegladark\w*|google)\w* .{0,15}(nie (laduj|otwier|wczytuj|dziala|chca)|dlugo (sie )?(laduj|otwier|wczytuj))|"
                     r"no internet|internet (is )?(down|not working|gone)|(wifi|wi-fi|connection) (is )?(down|not working)|"
                     r"(cannot|can t|cant) (connect|get online|load (pages|websites))|pages (won t|dont|do not) load|"
                     r"brak dostepu do sieci|ograniczona lacznosc|bez dostepu do internetu"),
    ("network_check", r"(sprawdz|sprawdzisz|przetestuj|przetestowac|zbadaj|zdiagnozuj|test\w*|check|diagnose) .{0,12}" + _NET + r"|"
                      r"czy (mam|dziala|jest|chodzi) (mi )?(internet|net|neta|wi ?fi|polaczenie)|"
                      r"(jaki|jak[aie]?|ile) (mam |jest |wynosi )?(ping\w*|opoznieni\w*)|(moj|mój) ping|"
                      r"(jakosc|stan|kondycj\w*|stabilnosc\w*) (mojego |mego )?" + _NET + r"|"
                      r"czy (moj |mój )?(internet|wi ?fi|net) (jest )?(dobry|ok|stabilny|w porzadku|szybki)|"
                      r"(is|how is) my (internet|connection|wifi|network) (ok|working|good|fine|stable|doing)|"
                      r"(check|test) (my )?(internet|connection|wifi|network|ping)|ping test|connection test|what s my ping|my ping|"
                      r"(lagi|laguje|lagow) .{0,15}(online|w grze|w grach|multiplayer)|packet loss|utrat\w* pakiet\w*|gubi pakiet\w*"),
    ("network_slow", r"(wolny|wolno dziala|slaby|zamula|muli|przerywa|rwie|zrywa|lagujacy) .{0,10}(internet\w*|\bnet\b|neta|necie|wi ?fi|siec\w*|polaczeni\w*)|"
                     r"(internet\w*|\bnet\b|neta|wi ?fi)\w* .{0,15}(wolny|wolno|slabo|slaby|zamula|muli|przerywa|rwie|zrywa|nie dziala|laguje|tnie)|"
                     r"(slow|bad|laggy) (internet|wifi|wi-fi|connection)|internet is slow|"
                     r"ping\w* .{0,10}(wysoki|duzy|skacze)|(wysoki|duzy) ping|high ping"),
    ("gpu_overclock", r"(podkrec\w*|overclock\w*|\boc\b) .{0,25}(kart\w*|gpu|grafik\w*|rtx|gtx|radeon)|"
                      r"(kart\w*|gpu|grafik\w*) .{0,15}(podkrec|overclock)"),
    ("virus_check", r"czy .{0,20}\b(ma|mam|jest|sa|nie ma)\b .{0,10}wirus|wirus\w* .{0,10}(na|w) (moim |tym )?" + _PC + r"|"
                    r"jak sprawdzic .{0,15}wirus|(any|a) virus on (my )?(pc|computer)"),
    ("error_help", r"^czy (mam|sa|wystepuja|widzisz) (jakies )?(bledy|bled)$|^jakies bledy$"),
    ("stale_apps", r"^(a )?co (moge |mozna |warto |powinienem )?odinstalowac\??$"),
    ("free_space", r"^(a )?co (moge |mozna |warto |powinienem )?(usunac|skasowac|wyrzucic)$"),
    ("about_assistant", r"^kto (ty )?jestes|^kim (ty )?jestes|^who are you|^(opowiedz|powiedz) (mi )?(cos )?(wiecej )?o sobie$|^(opowiedz|powiedz) (mi )?cos( wiecej)?$"),
    ("presence", r"^czy (dobrze |w ogole |poprawnie )?dzialasz|^dzialasz (dobrze|poprawnie)"),
    ("joke", r"(opowiedz|powiedz|rzuc|daj|znasz) .{0,10}(zart|dowcip|kawal|cos smiesznego)|^(zart|dowcip|kawal)$|tell (me )?a joke|^joke$"),
    ("recent_events", r"(duzo|wiele|sporo|za duzo|tyle) .{0,10}(recent ?events?|zdarzen)"),
    # "wyłącz teams" outside the guide: the startup list, where it is one click
    ("startup_check", r"^(wylacz|wylaczyc|zablokuj|usun z autostartu) (mi )?(autostart )?"
                      r"(teams|msteams|discord|steam|spotify|opera\w*( gx)?|onedrive|edge|skype|epic\w*|battle ?net)$"),
    # ── fourth long test (2026-11-17): data, the project, plain talk ───────
    ("data_export_run", r"^(zrob|wykonaj|zacznij|start) (mi )?(export|eksport)|^eksportuj dane|^export (data )?now$"),
    ("data_export", r"(przeniesc|przenies|przeniose|eksport|export|wyeksportowac|zachowac) .{0,30}(dan|nauk|nauczyl|pc ?workman|ustawien)|"
                    r"nowy (system|windows)|nowego (systemu|windowsa)|reinstal\w* (windows|system)|format\w* (dysku|systemu)|"
                    r"(move|transfer|export|backup) .{0,15}(my |the )?(data|learning|settings)"),
    ("data_reset", r"(usun|usunac|wyczysc|wyczyscic|skasuj|skasowac|zresetuj|zrestartuj|resetuj)\w* .{0,25}(dan|nauk|naucz|histori|pamiec|wiedz)|"
                   r"(dane|nauke|nauczanie) od (nowa|zera)|zacznij .{0,10}od (nowa|zera)|(delete|reset|wipe|clear) .{0,15}(data|learning|history)"),
    ("learning_eta", r"ile (jeszcze |dlugo )?(sie )?(bedziesz )?(uczyc|uczysz)|ile (sie )?(jeszcze )?bedziesz sie uczyc|"
                     r"kiedy (skonczysz|przestaniesz) (sie )?uczyc|how (much )?long(er)? .{0,15}learn"),
    ("lhm_help", r"libre ?hardware|\blhm\b|libre\w*.{0,20}(zainstal|pobrac|pobierz|gdzie)|(zainstal\w*|pobrac|pobierz|sciagnac) .{0,15}libre|"
                 r"(gdzie|jak) .{0,20}(pobrac|zainstalowac|sciagnac) .{0,25}(napiec|czujnik|temperatur\w* cpu|wentylator)|"
                 r"(napiecie|napiecia|czujniki) .{0,10}(dzialal|dzialaly|nie dziala)"),
    ("project_status", r"(tworc\w*|autor\w*|marcin) .{0,25}(tworz|rozwija|pracuj|robi)|prace nad .{0,20}(trwaj|sa|ida)|"
                       r"(program|pc ?workman|aplikacja) .{0,10}(sie )?(rozwija|jest rozwijan|jest aktualizowan|bedzie aktualizowan)|"
                       r"is (pc ?workman|it|the app) (still )?(being )?(developed|updated|maintained)"),
    ("version_check", r"(nowa|nowsza|nowej|nowsze) wersj|gdzie (pobiore|znajde|sciagne|pobrac|znalezc) .{0,15}(wersj|aktualizacj)|"
                      r"(zaktualizowac|zaktualizuje|aktualizowac|update) (pc ?workman|program|aplikacj)"),
    ("whats_new", r"^(a |czy |no )?(jest )?(cos|co) (nowego|ciekawego)|znalazl\w* (cos|cokolwiek)|zapisal\w* (cos|cokolwiek)|"
                  r"(na co|czy jest cos na co) .{0,10}zwrocic uwag|anything new|found anything"),
    ("about_assistant", r"czy (jestes|ty jestes) (claude|gemini|copilot|siri|alexa|bard|llama)|are you (claude|gemini|copilot)"),
    ("presence", r"^(halo|hallo|hello\?|jestes|jestes tam|jestes\?|jest tam ktos|ej|hej\?|dzialasz|odezwij sie|are you there|you there)$"),
    ("meta_feedback", r"nie (rozumiesz|rozpoznajesz|ogarniasz|kumasz)|^rozumiesz$|^czy rozumiesz|glupi (bot|jestes)|"
                      r"(you )?(don.?t|do not) understand"),
    ("compliment", r"(fajny|super|swietny|dobry|spoko|mega) (ziomek|ziom|jestes|z ciebie|asystent|bot)|lubie cie|jestes (super|fajny|spoko|swietny)|"
                   r"(good|nice|great) (bot|job|assistant)|i like you"),
    ("error_help", r"^(mam|wyskakuje|wyskoczyl|pokazuje sie|dostaje) (jakis )?(blad|error)|^(cos|co) nie dziala\??$|wyskakuje (mi )?blad|error message"),
    ("virus_check", r"czy (mam|jest) .{0,10}wirus|sprawdzic,? czy mam wirus|skan\w* (antywirus|wirus)|do i have (a )?virus|scan for virus"),
    ("game_can_run", r"\bgta ?(6|vi)\b"),
    ("pc_checkup", r"(cos )?dolega|cos (jest )?nie tak z (moim )?" + _PC),
    ("what_remembered", r"twoj\w* pamiec|twojej pamieci|masz pamiec|stan twojej|co (juz )?zapamietales|your memory"),
    # "coś" must be there: "czy muszę wymienić płytę pod i7 14700K" is a
    # part question for the compatibility checker
    ("bottleneck", r"czy cos (trzeba |warto |musze |powinienem )?wymienic|czy (powinienem|trzeba|warto|musze) cos wymienic|"
                   r"should i (replace|upgrade) (something|anything)"),
    ("process_identity", r"^czym jest (proces |program )?[a-z0-9_.-]{3,}( exe)?$|^co to (jest )?(za )?(proces |program )?(teams|discord|steam|opera|spotify|onedrive)$"),
    # ── follow-ups and the observation note (checked first) ────────────────
    ("observe_stop", r"(zakoncz|zatrzymaj|stop|skoncz|wylacz|przerwij) .{0,10}(nagrywani|obserwacj|nagranie|pomiar)|stop (the )?(recording|observation)"),
    ("observe_start", r"(zacznij|rozpocznij|start\w*|wlacz|uruchom|odpal) .{0,10}(nagrywani|obserwacj|nagranie|pomiar)|"
                      r"nagraj (parametry|statystyki|test|to|gre|mi)|start (a |the )?(recording|observation)|record (it|this|my)"),
    ("observe_howto", r"(jak|skad) .{0,12}(sprawdzic|zmierzyc|sprawdze|zmierze|bede wiedzial|wiem|poznam),? (ze|czy) .{0,20}(poprawa|poprawi|lepiej|pomoglo|szybciej)|"
                      r"how (do i|to|can i|will i) (check|know|measure|tell|see) .{0,25}(better|improv|help|faster)|notatk\w* obserwac|benchmark"),
    ("game_lag", r"(chce|chcialbym|chcialabym|gram|grac|pograc|odpalam|w) .{0,25}(cs2|cs ?go|counter.?strike|fortnite|valorant|minecraft|"
                 r"cyberpunk|gta|apex|warzone|overwatch|elden ring|wiedzmin|witcher|hogwarts|beamng|lol|league).{0,30}"
                 r"(lag|zacina|przycina|tnie|klatkuj|fps|stutter)|(lag|stutter)\w* in (cs2|fortnite|valorant|minecraft|cyberpunk|gta|apex|warzone)"),
    ("top_resource_hog", r"^(a )?co (najbardziej |tak |najwiecej )?(go|je|mi go|komputer|kompa)? ?(obciaza|zjada|bierze)|what (is )?(loading|using) it (the )?most"),
    ("still_lagging", r"(dalej|nadal|wciaz|ciagle) .{0,15}(bedzie )?(zacina|laguje|tnie|przycina|muli)|co (jesli|jak|gdy) (dalej|nadal|to nie pomoze|nie pomoze)|"
                      r"still (lag|stutter)|what if it still|if (it|that) doesn.?t help"),
    ("will_it_help", r"^(a )?czy to (pomoze|cos da|cos zmieni|pomoze mi)|czy (po tym|wtedy|potem) bedzie (szybciej|lepiej)|bedzie szybciej\b|"
                     r"will (it|that|this) help|will it be (faster|better)"),
    ("how_to", r"^(a |ok,? )?jak (to|go|je) (zrobic|zrobie|wylaczyc|zamknac|ustawic|wlaczyc|zmienic)\b|^(a )?jak to\b|^jak\??$|how (do i|to) do (it|that)|^how\??$"),
    ("game_followup", r"(sobie )?(z tym|z nia|z nim|z ta gra) (radzi|poradzi|da rade)|^czy (to|ona|gra) pojdzie\b|"
                      r"(komputer|pc|sprzet|komp) .{0,10}(sobie )?radzi\b|can it (handle|run) (it|that)"),
    ("closable_apps", r"co .{0,20}zamknac przed (gra|graniem|grania)|what (should i )?close before (gaming|playing)"),
    ("recent_changes", r"czy ostatnio .{0,10}(sie )?zmienil|ostatnio .{0,10}zmienil|(anything|something) changed (lately|recently)"),
    # ── trust and personality first: short, unmistakable ───────────────────
    ("about_assistant", r"(prawdziw\w* (ai|sztuczn)|real ai|are you (an )?ai)"),
    ("likes_job", r"lubisz (swoja prace|swoja robote|to co robisz|swoja prac)|like your job|enjoy your (job|work)"),
    ("idle_activity", r"co robisz,? (kiedy|jak|gdy) (nic nie robie|mnie nie ma|nie pisze)|what do you do when"),
    ("watching", r"pilnujesz|czy (mnie |go )?obserwujesz|watching my|are you monitoring"),
    ("pc_tired", _PC + r" .{0,12}zmeczon|is my (pc|computer) tired"),
    ("files_access", r"dostep do (moich )?plikow|czytasz (moje )?pliki|widzisz (moje )?pliki|access to my files|read my files"),
    ("data_stored", r"(zapisujesz|przechowujesz|zbierasz|trzymasz) .{0,12}(dan|o mnie)|co o mnie zapisujesz|(store|keep|collect) my data"),
    ("privacy_data", r"(wysylasz|przesylasz|wysyla) .{0,20}(internet|neta|sieci|online|serwer)|cos wysylasz|send anything|send data online|telemetri"),
    ("what_remembered", r"co (o mnie |o nim )?(pamietasz|zapamietales|zapamietalas|wiesz o mnie)|zobaczyc,? co .{0,15}zapamietal|what (do )?you remember"),
    ("virus_capability", r"(rozpoznac|rozpoznajesz|wykryc|wykryjesz|znalezc|umiesz .{0,10}) .{0,6}wirus|(detect|find|recogni[sz]e) (a )?(virus|viruses|malware)"),
    ("defender_enough", r"defender\w* .{0,12}(wystarczy|starczy|enough|dobry)|czy (sam )?(windows )?defender|is (windows )?defender enough"),
    ("svchost_safety", r"svchost\S* .{0,20}(bezpieczn|safe|ok|wirus)|(kazdy|wszystkie) (proces )?svchost|every svchost"),
    ("signed_trust", r"podpis\w* cyfrow|podpisan\w* program|trust signed|signed (programs|apps)"),
    ("impostor_check", r"podszywa|podrobion\w* (proces|program)|fake (process|program)|impostor|udaje (inny|proces|system)"),
    ("predict_slowdown", r"przewidziec .{0,40}(zwalnia|zwolni|zamula|problem)|przewidzisz|predict .{0,25}(slow|problem)"),
    ("pc_age", r"(czy )?(moj |moja )?" + _PC + r" (jest )?(juz )?(stary|przestarzal)|is my (pc|computer) (old|outdated)|ile lat ma (moj )?" + _PC),
    ("new_pc_advice", r"(kupic|kupie|kupowac|kupic sobie) nowy " + _PC + r"|buy a new (pc|computer)|czas na nowy " + _PC),
    # ── limits and parts ───────────────────────────────────────────────────
    ("cpu_boost", r"taktowani|\bboost\w*|max\w* (zegar|taktow|czestotliw)|max clock|limi\w* mocy|power limi\w*|"
                  r"zwalnia (pod obciazeniem|jak go obciaze|przy obciazeniu)|slow\w* down under load|"
                  r"temperatur\w* throttl|throttl\w* temperatur|hit throttle"),
    ("vram_check", r"\bvram\w*|pamiec\w* (karty|graficzn)"),
    ("gpu_utilization", r"(gpu|karta|grafika|karte)\w* .{0,25}(w pelni|wykorzyst|fully used|full use)"),
    ("gaming_temps", r"temperatur\w* .{0,25}(gr(a|ach|aniu|y|e)\b|gaming)|temps? .{0,15}(while |when )?gaming|bezpieczne podczas grania"),
    ("board_cpu_upgrade", r"plyt\w* .{0,25}(obsluzy|pociagnie|przyjmie|wezmie|udzwignie) .{0,25}(procesor|procek|cpu)|"
                          r"motherboard (handle|support|take) .{0,15}(cpu|processor)"),
    ("disk_speed_check", r"(czy )?(mam )?szybki (dysk|ssd)|(dysk|ssd) .{0,10}(jest )?szybki|is my (drive|disk|ssd) fast|"
                         r"(dysk|ssd) .{0,30}ladowani\w* gier|slowing game load|nvme czy sata"),
    ("ssd_health", r"(ssd|dysk)\w* .{0,25}(kondycj|zdrow|zuzyc)|stan (ssd|dysku|dyskow)|(ssd|drive|disk) .{0,6}healthy|dysk .{0,10}umiera"),
    ("bottleneck", r"waskie gardlo|bottleneck|najslabsz|weakest|wymienic (jako )?(pierwsze|najpierw)|upgrade first|"
                   r"co ogranicza|ogranicza .{0,10}wydajnosc|limiting (my )?performance"),
    ("ram_enough", r"(wystarczajaco|starczy|wystarczy|za malo)\w* .{0,12}(ram|pamieci)|enough ram|czy ram wystarcza"),
    ("part_verdict", r"czy (moj |moja )?(procesor|procek|cpu|karta graficzna|grafika|karta|gpu) (jest )?(jeszcze )?(dobr|daje rade|wystarcz|ok\b|sie nadaje)|"
                     r"(grafika|karta|gpu|procesor|procek) .{0,6}daje rade|is my (cpu|gpu) (still )?good"),
    # ── the state of the PC ────────────────────────────────────────────────
    ("stability_check", r"stabiln|bled\w* .{0,15}(sprzet|hardware)|hardware errors|is my (pc|computer) stable"),
    ("process_anomaly", r"(proces|program)\w* .{0,30}(wiecej|bardziej).{0,20}niz zwykle|using more than usual"),
    ("usage_vs_normal", r"(srednie|srednia|przecietne) .{0,25}(normaln|ok\b|w normie)|average .{0,20}normal|"
                        r"gorzej niz zwykle|worse than usual|normaln\w* (zuzyci|obciazeni|uzyci)|co jest (u mnie )?normaln|"
                        r"pogarsza sie|coraz wolniejsz|getting worse|norma (ramu|ram|cpu|procesora)"),
    ("history_compare_days", r"(dzis|dzisiaj) .{0,30}(niz|a|vs) wczoraj|higher today than yesterday|today than yesterday"),
    ("background_load", r"(niepotrzebnie|bez potrzeby) .{0,20}w tle|w tle .{0,10}niepotrzebnie|smieci w tle|"
                        r"za duzo .{0,25}program|too many programs|in the background for no reason|running in the background"),
    ("slower_lately", r"(ostatnio|od niedawna|ostatnimi dniami) .{0,25}(wolniej|gorzej|zwolnil|muli)|"
                      r"(wolniej|gorzej) .{0,15}ostatnio|wrazenie,? ze .{0,30}wolniej|komputer zwolnil|feels slower|slower lately"),
    ("slowdown_cause", r"co (najbardziej |tak )?(spowalnia|zamula|mi zamula)|wolno dziala|dziala wolno|what slows"),
    ("pc_changes", r"(zmienilo|zmienil) sie od (ostatniej sesji|ostatniego razu|ostatnio)|changed since (last|the last)"),
    ("disk_usage_why", r"(dysk|disk)\w* .{0,15}(caly czas|ciagle|always|non.?stop) (pracuje|mieli|working|busy)"),
    ("fun_roast", r"(nienawidzi|nie lubi|wkurza) mnie|mnie (nienawidzi|nie lubi)|hates? me"),
    ("power_plan", r"(profil|tryb|plan)\w* (wysokiej |maksymalnej )?wydajnosci|high performance (plan|mode|profile)"),
    ("pc_checkup", r"co (tam |slychac )?u (mojego |mego )?" + _PC + r"|jak sie ma (moj |moja )?" + _PC + r"|"
                   r"how is my (pc|computer) doing|musze cos naprawic|(trzeba|nalezy) cos naprawic|"
                   r"cos (trzeba|nalezy|musze) naprawic|do i need to fix|"
                   r"(powinienem|powinnam|mam) sie (czyms )?martwic|cos niepokojacego|should i (be )?worr|"
                   r"czy (moj |moja )?" + _PC + r" (jest )?zdrow|is my (pc|computer) healthy"),
    ("process_kill", r"can i (safely )?(kill|close|end|stop) [a-z0-9]{3,}"),
    ("closable_apps", r"co (moge|mozna|warto) (bezpiecznie )?(zamknac|wylaczyc)|what can i (safely )?close"),
]

_COMPILED = [(intent, re.compile(rx)) for intent, rx in RULES]


def route_insight(text: str, folded: bool = False) -> Optional[str]:
    t = text if folded else fold(text)
    for intent, rx in _COMPILED:
        if rx.search(t):
            return intent
    return None
