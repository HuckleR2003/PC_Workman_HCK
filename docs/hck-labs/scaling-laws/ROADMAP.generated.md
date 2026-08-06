# Scaling Laws — Roadmap

> **SHIPPED means we stop making excuses for it.**
>
> A feature is SHIPPED only when it is complete, stable and no longer needs a roadmap disclaimer.

Updated: **2026-08-06**

Status: `✅ SHIPPED` · `◆ PLAYABLE` · `◐ POLISH` · `◇ FOUNDATION` · `○ PLANNED`

## Foundation

The rules that keep every campaign reproducible, saveable and testable.

- ✅ **Deterministic campaign clock** — Campaign time advances through one GameDate timeline beginning on 1 January 2022. _[SHIPPED]_
- ✅ **One ordered daily simulation tick** — Deliveries, compute, market demand, bills, gates and solvency resolve in a fixed order. _[SHIPPED]_
- ✅ **Saved deterministic random state** — The same seed and the same decisions replay to the same numbers. _[SHIPPED]_
- ✅ **Simulation separated from Unity** — Economics and game rules run without UnityEngine so balance tests do not need a scene. _[SHIPPED]_
- ✅ **Versioned save migrations** — Old save shapes move forward one version at a time instead of being silently rewritten. _[SHIPPED]_
- ✅ **Save sanitization** — Loaded fields are clamped and invalid enum values fall back to legal states. _[SHIPPED]_
- ✅ **Projection honesty flags** — Estimated hardware and rival data stay distinguishable from known reference data. _[SHIPPED]_
- ✅ **Training projection separated from outcome** — A projected capability never becomes a deployed score until the run actually finishes. _[SHIPPED]_
- ✅ **Playability campaign test** — A scripted multi-year company must survive and stay competitive without trivially dominating. _[SHIPPED]_
- ✅ **Cross-catalog consistency tests** — Catalog sweeps catch impossible ranges, dangling references and dead research paths. _[SHIPPED]_
- ◐ **Scene wiring guards** — PlayMode checks protect critical visual references that EditMode simulation tests cannot see. _[NOW]_

## Founder & Company

The opening choices that shape cost, research, training and where the company operates.

- ◆ **Founder creation screen** — Create the person behind the lab before the campaign begins. _[NOW]_
- ✅ **Seven founder skills** — Development, Management, Teamwork, Concept, Software, Data Engineering and Safety. _[SHIPPED]_
- ✅ **Neutral skill baseline at 20** — Ignoring a skill is a real weakness instead of merely skipping a bonus. _[SHIPPED]_
- ✅ **Skill XP from completed work** — Experience is awarded for finished runs, research, upgrades and releases, never for idle time. _[SHIPPED]_
- ✅ **Founder traits with downsides** — Every opening trait trades one advantage against a real cost. _[SHIPPED]_
- ◆ **Company identity choices** — Opening company profiles change starting cash, reputation, data and default pricing. _[NOW]_
- ◆ **Custom company identity** — Name and define the player's own lab rather than taking a preset. _[NOW]_
- ◆ **World region selection** — Choose the region used to navigate the registration map. _[NOW]_
- ◆ **Sixteen registration countries** — Countries differ on hardware access, tax, innovation and local competition. _[NOW]_
- ✅ **Corporate tax on operating profit** — A loss-making company is not punished with tax on turnover. _[SHIPPED]_
- ✅ **Regional hardware price modifier** — Registration changes what owned silicon costs. _[SHIPPED]_
- ✅ **Regional innovation modifier** — Country choice changes research and upgrade timing. _[SHIPPED]_
- ✅ **Local competition modifier** — Registration changes the brand pressure in the market split. _[SHIPPED]_
- ○ **Founder appearance in the 3D world** — Connect the creator identity to the physical starter home and later offices. _[NEXT]_

## Models & Data

From a blueprint to a trained model, a shelf decision and a live product.

- ◆ **Staged model creator** — Build a model through Foundation, Scale, Data, Compute and Review instead of one giant form. _[NOW]_
- ◆ **Live capability projection** — The creator shows how the last change moved projected capability. _[NOW]_
- ◆ **Training-time projection** — The bill is not the only cost. Calendar time is visible before committing the run. _[NOW]_
- ◆ **Training-cost projection** — The creator prices the run against cash on hand before the player commits. _[NOW]_
- ✅ **Scaling-law quality model** — Parameter count and token count feed one Chinchilla-style quality function. _[SHIPPED]_
- ✅ **Compute-optimal training pressure** — Undertraining or overtraining can waste the same compute budget. _[SHIPPED]_
- ✅ **Dataset catalog** — Eight corpora feed the data side of the training plan. _[SHIPPED]_
- ✅ **Dataset blending rule** — Multiple corpora combine through one normalized mechanism. _[SHIPPED]_
- ✅ **Five audience segments** — Consumer, Developer, Enterprise, Creative and Autonomous demand change over time. _[SHIPPED]_
- ◇ **Five model types** — Specialized model types trade broad reach for stronger audience fit and price tolerance. _[NOW]_
- ✅ **Shelf before release** — A finished run becomes a trained model on the shelf, not an automatic launch. _[SHIPPED]_
- ◆ **Manual release timing** — The player chooses when a trained model reaches the market. _[NOW]_
- ◆ **Per-model pricing** — Multiple live models can carry different prices. _[NOW]_
- ◆ **Eleven model traits** — Reasoning, knowledge, coding and other traits are measured against the market par of the day. _[NOW]_
- ✅ **Trait upgrades consume time and compute** — Model maintenance competes with training for the same calendar and infrastructure. _[SHIPPED]_
- ✅ **Production serving descendant factor** — Inference is priced as served descendants rather than the full training artifact. _[SHIPPED]_
- ○ **Safety stage in model creator** — Make safety an explicit creation-stage decision before training. _[NEXT]_
- ○ **Keep local vs release flow** — A finished run should branch into internal use or public release instead of one fixed path. _[NEXT]_
- ○ **Serving-capacity decision after training** — Choose rented serving capacity or owned infrastructure after deciding to release. _[NEXT]_

## Research & Architecture

Technology unlocks, in-house architecture work and the calendar cost of getting there.

- ◆ **Technology tree** — Seventeen nodes gate architectures, data, model types, upgrades and compute tiers. _[NOW]_
- ◆ **Four research eras** — Foundations, scaling, autonomy and the late frontier structure the tree. _[NOW]_
- ✅ **Research prerequisite graph** — Every unlock must be reachable and cannot open before its own prerequisite. _[SHIPPED]_
- ✅ **Calendar gates** — Research cannot be brute-forced purely by having more cash. _[SHIPPED]_
- ✅ **Cash cost on research** — Time is hard to buy, but research still competes for company capital. _[SHIPPED]_
- ◇ **Artificial Superintelligence node** — The end-state node is visible early but intentionally unreachable in the opening years. _[LATER]_
- ◆ **In-house architecture designer** — Create a custom family instead of only adopting a published architecture. _[NOW]_
- ◆ **Five architecture research directions** — Sparsity, throughput, quality-per-parameter, serving cost and reasoning divide programme focus. _[NOW]_
- ✅ **Budget × calendar power model** — More money cannot fully substitute for more time, and more time cannot replace all budget. _[SHIPPED]_
- ✅ **Focus dilution** — A programme chasing every direction makes less depth in each one. _[SHIPPED]_
- ✅ **Architecture outcome variance** — Cheap or rushed research is deliberately less predictable. _[SHIPPED]_
- ✅ **Six custom family slots** — House architectures resolve through the same downstream interfaces as published families. _[SHIPPED]_
- ◇ **Iterate an owned family** — Improve a house family more cheaply and quickly, with diminishing returns. _[NEXT]_
- ◐ **Research-era visual polish** — Finish the visual language and card art around the four research eras. _[NOW]_

## Hardware & Compute

The current active development line: rent, own, configure, wait and sometimes regret the timing.

- ✅ **Hardware generation catalog** — Accelerators, host CPUs, node memory and fabric carry launch dates, price, power and capacity data. _[SHIPPED]_
- ✅ **Known vs projected hardware flag** — Future entries can be labelled as projections rather than blended into history. _[SHIPPED]_
- ✅ **Time-based hardware depreciation** — Owned accelerators lose resale value as calendar time passes. _[SHIPPED]_
- ✅ **Successor depreciation** — Meaningful newer parts apply another phased hit after the player's purchase. _[SHIPPED]_
- ✅ **Performance-per-dollar aging index** — The fleet can be compared with what the same money buys today. _[SHIPPED]_
- ✅ **Rented compute in petaflops** — Cloud rental is capacity, not a fragile count of whatever hardware generation happens to be current. _[SHIPPED]_
- ✅ **Cloud hardware availability lag** — Rental availability follows the hardware frontier with a delay. _[SHIPPED]_
- ◇ **Three compute tiers** — Rented cloud, colocated servers and own datacenter form the infrastructure ladder. _[NOW]_
- ✅ **Owned-cluster balance factor** — Accelerators need enough host CPU, memory and fabric to approach their nominal rating. _[SHIPPED]_
- ✅ **Training scaling-efficiency loss** — Large accelerator counts lose efficiency as the fleet scales. _[SHIPPED]_
- ✅ **Inference utilization model** — Serving and training do not pretend to use the same hardware in the same way. _[SHIPPED]_
- ◇ **Hardware purchase screen** — Turn the existing catalog and economics into a player-facing buy flow. _[NOW]_
- ◇ **Hardware sell flow** — Make resale value visible before the player exits an owned batch. _[NOW]_
- ◇ **Server configuration** — Pair accelerators with host CPUs, node memory and fabric instead of buying one magic server score. _[NOW]_
- ◇ **Hardware launch timeline** — Surface generation timing so waiting becomes an explicit decision rather than hidden knowledge. _[NOW]_
- ○ **Colocation acquisition flow** — Buy owned hardware with lead time before the company is ready for a full datacenter. _[NEXT]_
- ○ **Own-datacenter acquisition flow** — Turn the late compute tier into a real capital and infrastructure commitment. _[NEXT]_
- ○ **Supply ramp after launch** — A new accelerator generation should not become infinitely available on day one. _[NEXT]_
- ○ **Supply squeezes and shortages** — Make availability another reason a technically good purchase can fail operationally. _[NEXT]_
- ○ **Physical server racks** — Owned compute should appear in company spaces instead of living only in a table. _[NEXT]_
- ○ **Datacenter power planning** — Owned infrastructure eventually needs limits beyond purchase price. _[LATER]_
- ○ **Datacenter cooling constraints** — Cooling becomes a late physical limit if the infrastructure simulation grows deep enough. _[LATER]_

## Rivals & Intelligence

Competitors that react to timing, plus information that can cost money and still be wrong.

- ✅ **Eight rival labs** — The active field is agent-driven rather than one static score table. _[SHIPPED]_
- ✅ **Historical release seed timeline** — Known releases seed the 2022–2026 opening before agents diverge. _[SHIPPED]_
- ✅ **Patient rival waiting** — Some rivals delay a run when better silicon is close to the planned launch window. _[SHIPPED]_
- ✅ **Rival rush response** — A frontier-focused lab can ship early with a quality penalty when the player opens a large gap. _[SHIPPED]_
- ✅ **Rival capability drift** — Competitors improve between releases instead of freezing until the next launch. _[SHIPPED]_
- ✅ **Procedural post-history releases** — After the known timeline ends, rival strategies generate their own cadence. _[SHIPPED]_
- ✅ **Parody rival naming** — Labs remain recognizable as jokes without using real company names. _[SHIPPED]_
- ◐ **Parody rival logo set** — Finish a consistent small-mark system that remains readable at UI scale. _[NOW]_
- ◇ **Three paid intelligence tiers** — Information quality improves with spend without turning into perfect foresight. _[NOW]_
- ✅ **Real accuracy vs stated confidence** — A report can sound more certain than the underlying signal deserves. _[SHIPPED]_
- ✅ **Hardware launch signals** — Intel can surface an upcoming generation before the player has certainty. _[SHIPPED]_
- ✅ **Price-collapse signals** — Intel can warn about a market event that changes hardware economics. _[SHIPPED]_
- ✅ **Supply-squeeze signals** — Intel can warn that availability is about to tighten. _[SHIPPED]_
- ✅ **Rival-holding signals** — Higher-tier intelligence can flag that a competitor may be waiting on purpose. _[SHIPPED]_
- ○ **Expanded intelligence report UI** — Give evidence, history and uncertainty more room than a single note card. _[NEXT]_
- ○ **Competitor release history view** — Show how each lab actually moved through the campaign, not just where it stands today. _[LATER]_

## Business & Capital

Turn model quality into demand, demand into cash and cash into the next dangerous decision.

- ◆ **Per-model token pricing** — Each live model carries its own price instead of inheriting one company-wide number. _[NOW]_
- ◆ **Free-tier control** — Free access can be used as a deliberate distribution decision. _[NOW]_
- ✅ **Shared market-share model** — The economy and ranking read from the same demand model. _[SHIPPED]_
- ✅ **Capability term in demand** — Better models earn an advantage but do not automatically own the market. _[SHIPPED]_
- ✅ **Brand term in demand** — Reputation changes how equal products split demand. _[SHIPPED]_
- ✅ **Price term in demand** — Price matters independently of capability. _[SHIPPED]_
- ✅ **Model-age term in demand** — A model that nobody replaces gradually becomes stale. _[SHIPPED]_
- ✅ **Audience-segment curves** — Consumer, Developer, Enterprise, Creative and Autonomous markets change size over time. _[SHIPPED]_
- ✅ **Specialist price tolerance** — A narrower model can reach fewer people while selling to an audience that tolerates higher pricing. _[SHIPPED]_
- ◆ **Company marketing programmes** — Marketing spend acts on demand instead of being a decorative button. _[NOW]_
- ◆ **Model launch push** — A release can receive focused marketing rather than only permanent company spend. _[NOW]_
- ◆ **Funding valuation** — Valuation combines frontier proximity, run rate and the sentiment of the year. _[NOW]_
- ✅ **Investor sentiment cycle** — The same company can be priced very differently depending on when it raises. _[SHIPPED]_
- ✅ **Cap table and founder dilution** — Equity rounds permanently change ownership. _[SHIPPED]_
- ✅ **Down-round penalty** — Raising below the previous valuation costs extra equity. _[SHIPPED]_
- ✅ **Debt facilities** — Bridge, venture debt, bond and sovereign compute debt trade dilution for repayment pressure. _[SHIPPED]_
- ✅ **Arrears and default** — Missed payments accumulate before a public default damages standing. _[SHIPPED]_
- ◆ **Ranking board** — Capability, share and brand feed one sorted company board. _[NOW]_
- ○ **Ranking history** — Track movement through time instead of showing only today's order. _[NEXT]_
- ○ **Contextual market events** — Add discrete events only where they reinforce an existing market mechanism. _[LATER]_

## Office, Staff & World

Make company growth visible in rooms, people, cars, buildings and infrastructure.

- ◆ **3D starter home** — The opening company site exists as a real orthographic 3D environment. _[NOW]_
- ◐ **Starter living space** — Living room, workspace and bedroom sell the scale of the first company before expansion. _[NOW]_
- ◐ **Garage** — The starter site includes a garage connected to the planned travel flow. _[NOW]_
- ◐ **Starter car** — The first vehicle gives the world-map transition a physical starting point. _[NOW]_
- ✅ **Fixed orthographic camera** — The scene uses a locked 2.5D presentation rather than free camera navigation. _[SHIPPED]_
- ◐ **Room visual-polish pass** — Keep refining props, lighting and composition without changing the core camera. _[NOW]_
- ○ **Wall hide / transparency** — Remove room obstruction when the founder enters the garage or another hidden space. _[NEXT]_
- ○ **Founder 3D character** — Place the created founder into the physical company view. _[NEXT]_
- ○ **Founder idle animation** — Give the opening scene life without turning movement into simulation authority. _[NEXT]_
- ○ **Founder waypoint walking** — Move between fixed activity points rather than overengineering pathfinding for the camera distance. _[NEXT]_
- ○ **Walk to workstation** — Training and work actions gain a short physical animation at the desk. _[NEXT]_
- ○ **Walk to garage and car** — Travel begins with the founder physically leaving the starter site. _[NEXT]_
- ◇ **World / location map** — Turn location selection into a navigable world layer beyond company registration. _[NEXT]_
- ○ **Rent larger offices** — Company growth should require leaving the starter house. _[NEXT]_
- ○ **Office tiers** — Progress through larger spaces instead of one infinitely expanding room. _[NEXT]_
- ○ **Hiring employees** — Add the team layer that turns empty office capacity into useful company capacity. _[NEXT]_
- ○ **Employee skills** — Staff quality should influence work rather than every hire being interchangeable. _[NEXT]_
- ○ **Employee salaries** — Headcount becomes a continuing operating commitment. _[NEXT]_
- ○ **Physical employee desks** — A hire should appear in the space the company is paying for. _[NEXT]_
- ○ **Walking staff** — Employees move between work points to keep larger spaces alive. _[LATER]_
- ○ **Owned racks populate the office** — The physical view reads the compute pool and shows what the company actually owns. _[NEXT]_
- ○ **Dedicated company HQ** — A late office tier separates the management fantasy from the starter site. _[LATER]_
- ○ **Dedicated datacenter site** — Owned infrastructure eventually becomes a place rather than only a finance line. _[LATER]_

## Safety & Incidents

Safety should be a decision with tail risk, not a virtue stat that only moves brand.

- ✅ **Founder Safety skill** — Founder creation already changes incident-risk pressure through the skill system. _[SHIPPED]_
- ◆ **Model Safety trait** — Safety is one of the traits measured against the market par of the day. _[NOW]_
- ✅ **Safety brand effect** — Falling behind on safety already affects how a product is received. _[SHIPPED]_
- ◇ **Incident-risk multiplier foundation** — The simulation has the inputs needed to turn weak safety choices into tail risk. _[NEXT]_
- ○ **Safety stage in model creator** — Make safety visible before training instead of burying it in later upgrades. _[NEXT]_
- ○ **Model safety incidents** — A model far below the safety expectation can produce a costly event. _[NEXT]_
- ○ **Reputation damage from incidents** — Incidents should hit standing that took time and money to build. _[NEXT]_
- ○ **Regulatory attention** — Serious safety failures can create pressure outside the normal demand model. _[LATER]_
- ○ **Incident response decisions** — Give the player a recovery choice rather than only applying an automatic penalty. _[LATER]_

## Interface & Presentation

The game needs to stay legible while the simulation gets denser.

- ◆ **Bottom control HUD** — The main navigation lives in a bottom control bar instead of a wide left rail. _[NOW]_
- ◆ **Day clock dial** — A half-disc shows date and day progress without controlling the simulation rules. _[NOW]_
- ◆ **Pause / X1 / X2 / X3** — Time controls map cleanly onto the whole-day simulation. _[NOW]_
- ◆ **Skip Day** — Run exactly one day and stop, even when the game is paused. _[NOW]_
- ◐ **Unified accent gradient** — Coral, wine and pale violet are treated as one line moving through the interface. _[NOW]_
- ◐ **Bottom category icon set** — Finish the white single-weight icon language across the major screens. _[NOW]_
- ◐ **Skill icon set** — Seven founder-skill icons are already present and being normalized as one family. _[NOW]_
- ◐ **Section banner art** — Research, Business, Funding and other screens share low-contrast panoramic art. _[NOW]_
- ◇ **Responsive UI Toolkit layout** — Creators and panels defend against shrink, wrap and small-window layout faults. _[NOW]_
- ○ **Tooltip pass** — Move long explanations out of cramped controls without hiding decisions. _[NEXT]_
- ○ **Resolution and scaling pass** — Test the game across the target window and display sizes. _[NEXT]_
- ○ **Accessibility pass** — Review contrast, focus, motion and readability before a public release. _[LATER]_
- ○ **Audio feedback** — Add restrained confirmation and warning sounds once the interaction language is stable. _[LATER]_
- ○ **UI motion pass** — Animate state changes only where motion clarifies what changed. _[LATER]_

## Public Build & Release

The public footprint around the game: source, website, roadmap, playtests and store pages.

- ✅ **Public source repository** — The code and engineering notes are visible while the game changes. _[SHIPPED]_
- ✅ **HCK Labs hub** — Scaling Laws has a permanent home beside the other HCK Labs work. _[SHIPPED]_
- ✅ **Scaling Laws landing page** — The public game page separates current systems from planned work. _[SHIPPED]_
- ✅ **Development mechanism page** — The simulation rules and real-world references have their own crawlable technical page. _[SHIPPED]_
- ✅ **Public roadmap** — This page is the living status map and the JSON behind it is the source of truth. _[SHIPPED]_
- ✅ **Roadmap JSON data source** — One structured file drives the roadmap state and can feed other presentation formats. _[SHIPPED]_
- ○ **Devlog index** — Create a home for build notes that can be indexed outside social platforms. _[NEXT]_
- ○ **Media gallery** — Collect screenshots, room-evolution clips and later trailers in one crawlable place. _[NEXT]_
- ◇ **itch.io project page** — Prepare the first game-specific public page and devlog channel. _[NOW]_
- ○ **IndieDB project page** — Add a second game-specific public footprint with indexed development updates. _[NEXT]_
- ○ **First public playable build** — Move from screenshots and source to something outside testers can actually run. _[NEXT]_
- ○ **Closed playtest loop** — Collect focused feedback before a wider demo. _[NEXT]_
- ○ **Feedback capture** — Give early players one clear place to report friction and balance problems. _[NEXT]_
- ○ **Steam Coming Soon page** — Start collecting wishlists once the visual direction and core loop can sell the game honestly. _[LATER]_
- ○ **Playable demo** — A public slice of the loop that proves the game beyond screenshots. _[LATER]_
- ○ **Gameplay trailer** — Cut the strongest in-game stories once the footage can represent the real loop. _[LATER]_
- ○ **Release candidate** — Freeze the feature line and spend time on bugs, balance and compatibility. _[LATER]_
- ○ **Commercial release** — Ship when the game is stable enough that the roadmap no longer has to explain away missing fundamentals. _[LATER]_
