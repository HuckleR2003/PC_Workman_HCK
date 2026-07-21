# hck_GPT - Question Bank & Expansion Blueprint

Research base for the next hck_GPT expansion (2026-07). 56 question sets
collected from: real tester questions (incl. the RTX-4090 power user), the
most common help-forum / vendor-support themes (Intel, Microsoft Support, HP,
Dell, Computer Hope "why is my PC slow" canon), and what PC Workman's own
data can uniquely answer (live sensors, learned baselines, process library,
startup/services, driver scans, hardware identity, 183-day history).

Legend: **[EXTEND x]** = grow existing intent `x` with phrases/logic ·
**[NEW]** = new intent · **[FLOW]** = multi-step guided flow (4-5 steps,
stateful) · every set ships PL + EN phrasings, short AND complex forms.

---

## A. Slowness diagnosis (the #1 forum theme)

1. "dlaczego mój komputer jest wolny" / "why is my pc slow" - short + "why is
   my pc so slow all of a sudden, it was fine yesterday" **[EXTEND why_slow]**
2. "komputer wolno działa po aktualizacji" / "pc slow after windows update"
   **[EXTEND why_slow]** - check: update history timestamp vs perf history.
3. "czemu wszystko się tnie jak gram" / "everything lags only when gaming"
   **[EXTEND game_hardware_stress]** - workload-aware verdict.
4. "komputer wolno startuje" / "boot takes forever" **[EXTEND startup_slowdown]**
   - real numbers from startup entries + measured impact.
5. "laptop zwalnia po godzinie pracy" / "gets slower the longer it runs"
   **[NEW slow_over_time]** - session history: RAM creep, temp throttle, leak
   suspects (process RAM trend from process history).
6. "co mnie teraz spowalnia, konkretnie" / "what exactly is slowing me down
   right now" **[EXTEND top_resource_hog]** - one verdict, not four tables.
7. "czy mój dysk jest wąskim gardłem" / "is my disk the bottleneck"
   **[EXTEND upgrade_advice]** - disk queue/usage vs CPU/RAM evidence.
8. "wszystko działa, ale czuję że kiedyś było szybciej" / "feels slower than
   months ago, prove it" **[NEW perf_regression]** - 183-day baselines: honest
   "yes, avg CPU load +X% vs May" or "no, numbers are flat".

## B. Guided optimization flows (4-5 steps, no getting lost) - all **[FLOW]**

9.  "zoptymalizuj mój komputer" / "optimize my pc" - THE master flow:
    (1) measure now, (2) startup cleanup, (3) services profile, (4) RAM/disk
    action, (5) re-measure + verdict with numbers. **[EXTEND tuneup_guide]**
10. "przyspiesz mi gry" / "make my games run better" - gaming flow: temps
    check, TURBO+plan, background trim, overlay on, verify FPS (RTSS).
11. "przygotuj komputer do pracy/szkoły" / "set up for work" - Economy
    profile, autostart audit, browser tabs advice.
12. "posprzątaj dysk" / "clean up my disk" - usage map, cache/temp candidates,
    driver-store leftovers (roadmap #4), verify freed GB.
13. "obniż temperatury" / "lower my temps" - baseline check, dust/curve
    advice, fan profile, verify delta after N minutes.
14. "wydłuż baterię" / "make battery last longer" - drain rate now, top
    drainers, power plan, verify est. gain. **[EXTEND battery_drain]**
15. "przyspiesz start windows" / "speed up boot" - startup entries by impact,
    disable via StartupApproved, measure next boot.
16. "miesięczny przegląd komputera" / "monthly checkup" - health score,
    trends vs last month, 3 actions. **[EXTEND health_check]**

## C. Hardware understanding & upgrades (power-user roadmap #1/#2)

17. "czy mogę włożyć ten procesor w moją płytę" / "will a 5800X3D work on my
    board" **[DONE 2026-07-17: upgrade_compat]** - offline library shipped as
    core/hardware_compat_db.py (320 entries), engine in core/hardware_compat.py,
    handlers in r_upgrade.py, parser part-model override.
18. "ile RAM mogę dołożyć i jaki" / "what RAM should I buy for this board"
    **[DONE 2026-07-17: ram_compat]** - DDR gen + speed vs platform, XMP/EXPO
    and chipset-lock caveats. (Slot-count questions stay in upgrade_feasibility.)
19. "co ulepszyć najpierw za 1000 zł" / "best upgrade under X" **[EXTEND
    upgrade_advice]** - bottleneck evidence + budget tiers.
20. "czy zasilacz wytrzyma nową kartę" / "will my PSU handle a 4070"
    **[PARTIAL 2026-07-17]** - GPU verdicts now state card TDP + recommended
    system PSU wattage from the library; honest gap: we cannot read the
    installed PSU's label. A dedicated psu_headroom intent (ask for PSU model)
    is still open.
21. "jaka dokładnie mam płytę główną / bios" / "exact motherboard + bios"
    **[EXTEND hw_motherboard]** - now grounded in real identity.
22. "czy mój komputer udźwignie [gra]" / "can I run X" **[EXTEND game_can_run]**
23. "co w moim komputerze jest najsłabsze" / "weakest part of my rig"
    **[EXTEND upgrade_advice]** - one component, one reason, one number.

## D. Processes & apps

24. "co to jest [proces] i czy mogę zabić" / "what is svchost, can I kill it"
    **[EXTEND process_info/process_kill]** - protected-guard aware answer.
25. "co mi zjada RAM/CPU/dysk/internet TERAZ" / "what's eating my ram right
    now" **[EXTEND ram_why_high/top_resource_hog]**
26. "które aplikacje są bezczynne od godziny" / "what's idle and safe to
    sleep" **[NEW idle_apps]** - app_activity_tracker data + one-click hint.
27. "czy [proces] to wirus" / "is X a virus" **[EXTEND virus_check]** -
    signature + path + typosquat verdict, plain language.
28. "dlaczego chrome ma 40 procesów" / "why does chrome have 40 processes"
    **[NEW browser_explainer]** - educational + per-tab RAM reality.
29. "co się uruchomiło nowego dzisiaj" / "what new processes appeared today"
    **[EXTEND pc_changes]** - process history diff.

## E. Temps / cooling / fans

30. "czy 85 stopni to dużo" / "is 85C bad" **[EXTEND temperature]** - learned
    per-workload verdict (our killer feature - lead with YOUR normal).
31. "wentylatory wyją, co się dzieje" / "fans suddenly loud" **[EXTEND
    fan_noise_history]** - correlate RPM history with load/temp events.
32. "komputer się wyłączył sam, czy to przegrzanie" / "pc shut down by
    itself, overheating?" **[NEW thermal_shutdown_check]** - max temps before
    the gap in history + honest verdict.
33. "jak ustawić krzywą wentylatorów" / "fan curve advice" **[EXTEND
    cooling_advice]**
34. "czy throttluje mi CPU/GPU" / "am I throttling" **[EXTEND throttle_check]**

## F. Startup & services

35. "co mogę bezpiecznie wyłączyć z autostartu" / "what's safe to disable at
    startup" **[EXTEND startup_check]** - tiered: safe/consider/keep.
36. "czy wyłączenie [usługi] coś zepsuje" / "is it safe to disable X service"
    **[EXTEND startup_safety]** - the 4-tier services DB speaks.
37. "onedrive wraca po wyłączeniu, czemu" / "onedrive keeps coming back"
    **[NEW stubborn_startup]** - explain StartupApproved (we DO it right).
38. "ile sekund zabiera mi autostart" / "how much time does startup cost me"
    **[EXTEND startup_slowdown]** - measured, not estimated.

## G. Windows repair advisor (roadmap #3) - all **[NEW + FLOW]**

39. "windows się psuje, jak naprawić bez reinstalki" / "repair windows without
    reinstalling" - guided DISM -> SFC flow: explain, show command, interpret
    result, next step. Never run without confirmation.
40. "co znaczy błąd sfc/dism [wynik]" / "sfc found corrupt files, now what"
41. "menedżer urządzeń pokazuje żółty trójkąt" / "unknown device with yellow
    triangle" - PNP scan + driver hint.
42. "windows update wisi/failuje" / "update stuck at 0%" - safe checklist.
43. "czy mój windows jest zdrowy" / "is my windows install healthy" - repair
    readiness report (build, update age, disk SMART, sfc history if known).

## H. Drivers (roadmap #4)

44. "które sterowniki są stare" / "which drivers are outdated" **[EXTEND
    driver_status]** - age from real scan, no fake "updater" promises.
45. "duchy sterowników - co można usunąć" / "leftover drivers safe to remove"
    **[NEW driver_cleanup]** - Ghost Hunter data + risk explanation + steps.
46. "po aktualizacji sterownika gpu jest gorzej" / "gpu driver update made
    things worse" **[NEW driver_regression]** - perf history around
    driver_date + rollback guidance.

## I. History / trends / learning (unique to us)

47. "co się zmieniło od wczoraj/tygodnia" / "what changed since yesterday"
    **[EXTEND session_compare/weekly_trends]**
48. "czego się o mnie nauczyłeś" / "what have you learned about my pc"
    **[EXTEND ai_context]** - the heart showcase.
49. "pokaż mój najgorętszy/najcięższy dzień" / "worst day this month"
    **[NEW history_extremes]** - query_api day extremes.
50. "czy moje napięcia są stabilne" / "are my voltages healthy" **[EXTEND
    voltage_check]** - SPC verdict in human words.
51. "o której godzinie mój pc pracuje najciężej" / "when is my pc busiest"
    **[NEW usage_pattern]** - hourly aggregates.

## J. Trust / safety / meta

52. "czy mogę ci ufać / co zbierasz" / "what data do you collect" **[EXTEND
    privacy_data]**
53. "czy przez ciebie nie dostanę bana w grze" / "will optimization get me
    banned" **[NEW anticheat_safety]** - the protected-processes story, our
    strongest trust answer.
54. "co zrobiłeś mojemu komputerowi" / "what did you change on my pc"
    **[NEW action_ledger]** - list of applied actions (prefs history:
    changed_by/disabled_at already persisted!) + how to undo each.

## K. Context & follow-ups (the "thinking" upgrade)

55. Follow-up chains: "a teraz?", "pomogło?", "zrób to", "a druga opcja?",
    "wróć do tego co mówiłeś", "ile to było przed chwilą?" - see Logic
    Upgrades below.
56. Vague openers: "wolno", "coś nie tak", "pomocy", "popraw coś" -
    disambiguation question with 3 tappable directions instead of a guess.

---

## Logic upgrades (design - extend, never duplicate; per ARCHITECTURE.md)

1. **FlowEngine (generalize `tuneup_guide`).** The stateful 4-step coaching
   already works; extract its pattern into a small engine: a flow = list of
   steps {measure -> advise -> confirm -> act -> verify}; session carries
   {flow_id, step, numbers_before}. "dalej/next/stop/pomiń" navigate. All B.9
   to B.16 flows become DATA (step definitions), not new code paths.
2. **Response ledger (memory of what WE said).** session_memory keeps the
   last N responses' key facts: {intent, headline numbers, entities}. Enables:
   "ile to było?" (repeat a number), "porównaj z poprzednim" (delta between
   two measurements), "wróć do tamtego" (re-open earlier topic). Dies with
   the session by design - context, not surveillance.
3. **Verify-after-action.** When a flow step changes state (flush, disable,
   plan switch), store the before-numbers; the NEXT related question answers
   with measured delta ("RAM 82% -> 61%, -21 pp"). This is the single most
   trust-building behavior an optimizer-assistant can have.
4. **Action ledger** (J.54): read the existing prefs histories
   (disabled_by/disabled_at, service_prefs changed_by) - the data is already
   persisted; it just needs a voice.
5. **Disambiguation for one-word queries** (K.56): confidence low + message
   short -> ask ONE question with 3 concrete options, carry the choice.
6. **Honesty rules stay supreme:** no "100% compatible" without data, name
   missing data explicitly, never run repair commands without confirmation,
   estimated values always labeled.

## Suggested build order

| Wave | Scope | Why first |
|---|---|---|
| 1 | FlowEngine + master flow B.9 + verify-after-action | multiplies everything else |
| 2 | A-set slowness phrases + D/E/F extensions (cheap vocabulary+logic wins) | daily-driver questions |
| 3 | Upgrade compat C.17-18 + compat library (roadmap #1/#2) | power-user promise, identity data ready |
| 4 | Repair advisor G + driver cleanup H (roadmap #3/#4) | needs FlowEngine from wave 1 |
| 5 | Ledgers + history extremes I/J/K | the "it remembers and proves" wow |
