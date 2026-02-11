# Stats Guide — LoL Team Analytics

A reference for every stat tracked in the app, how it's calculated, and what it tells you.

---

## Basic Stats

| Stat | Formula | What It Means |
|------|---------|---------------|
| **K / D / A** | Raw kills, deaths, assists | Core scoreline. High deaths = positioning or decision-making issues. |
| **KDA Ratio** | `(Kills + Assists) / max(1, Deaths)` | Overall fight contribution efficiency. Below 2.0 is concerning; above 4.0 is strong. |
| **CS** | `Minions Killed + Neutral Monsters Killed` | Total farm. Higher = better gold income from the map. |
| **Gold** | Total gold earned (end of game) | Raw resource accumulation. |
| **Damage** | Total damage dealt to champions | How much you contributed to hurting the enemy team. |
| **Vision Score** | Riot's composite vision metric | Measures warding, clearing wards, and vision denial. |

---

## Efficiency Stats

| Stat | Formula | What It Means |
|------|---------|---------------|
| **DPM** (Damage Per Minute) | `Total Champion Damage / Game Duration (min)` | Normalizes damage across game lengths. ADCs/mages should be 500+; tanks/supports lower. |
| **CS/M** (CS Per Minute) | `Total CS / Game Duration (min)` | Farming efficiency. Laners aim for 7+; junglers vary. |
| **VS/M** (Vision Score Per Minute) | `Vision Score / Game Duration (min)` | Vision contribution rate. Supports should lead; <0.5 for laners is a red flag. |
| **DPG** (Damage Per Gold) | `Total Champion Damage / Gold Earned` | Gold-to-damage conversion. High = efficient item usage; low = sitting on gold without impacting fights. |

---

## Share Stats

| Stat | Formula | What It Means |
|------|---------|---------------|
| **KP%** (Kill Participation) | `(Kills + Assists) / Team Total Kills × 100` | What % of team kills you were involved in. Low KP = playing isolated or not grouping. Junglers/supports should be highest. |
| **Dmg%** (Damage Share) | `Your Damage / Team Total Damage × 100` | Your share of the team's damage output. Carries should be 25%+. If a support is top damage share, the carries aren't doing their job. |
| **Gold%** (Gold Share) | `Your Gold / Team Total Gold × 100` | How much of the team's resources you're consuming. High gold% with low dmg% = not converting resources. |

---

## Advanced Stats (Laning Phase: 0–14 min)

### Harass Score
| | |
|---|---|
| **Formula** | `Damage Dealt to Champions / Damage Taken from Champions` (at 14 min) |
| **Source** | Timeline participant frames → `damageStats` |
| **Interpretation** | Measures laning trade efficiency. **> 1.0** = dealing more than you take (winning trades). **< 1.0** = losing trades. A score of 0.5 means you're taking 2x the damage you deal. |
| **Useful for** | Identifying who is winning/losing lane through trades, independent of CS or kills. |

### Greed Index
| | |
|---|---|
| **Formula** | Count of "greedy" deaths, where a death qualifies if **any** of these are true: |
| | **A. Deep Death** — Died deep in enemy territory (past x=9000,y=9000 for blue side, below x=6000,y=6000 for red side) |
| | **B. Gold Hoarding** — Died while holding >1500 unspent gold |
| | **C. Overstay** — Died within 30 seconds of getting a kill/assist (didn't back after a play) |
| **Interpretation** | **0** = disciplined. **1** = one risky play. **2+** = pattern of greedy decisions. Common among players who chase kills or refuse to back after winning a fight. |
| **Useful for** | Coaching players to base after plays and avoid unnecessary risks. |

### Jungle Proximity %
| | |
|---|---|
| **Formula** | `(Frames where distance to allied jungler ≤ 2000 units) / Total Frames (0-14 min) × 100` |
| **Source** | Timeline participant frames → position coordinates, compared to jungler's position each minute |
| **Interpretation** | How often your jungler is near you during laning. **High %** for a laner = jungler is camping your lane (good if winning, bad if you need it). **0%** = jungler never comes near you. |
| **Useful for** | Understanding jungle attention distribution. If one lane has 0% proximity and is also dying, the jungler may need to path differently. |

### Gank Deaths
| | |
|---|---|
| **Formula** | Count of deaths (0-14 min) where the **enemy jungler** was either the killer or an assisting participant |
| **Interpretation** | How many times you died to a gank. **0** = safe laning or good ward coverage. **2+** = either poor vision, bad positioning, or not respecting jungle timers. |
| **Useful for** | Identifying who is most vulnerable to ganks. Cross-reference with wards placed and spotted deaths. |

### Wards Placed (Pre-14m)
| | |
|---|---|
| **Formula** | Count of `WARD_PLACED` events by the player before 14 minutes |
| **Interpretation** | Raw early-game warding output. **Supports** should have the most. Laners with 0-1 wards pre-14 are playing blind and at high gank risk. |
| **Useful for** | Quick check on who is contributing to early vision. Pair with gank deaths to see if warding actually prevents deaths. |

### Spotted Deaths / Unspotted Deaths
| | |
|---|---|
| **Formula** | When a player dies to the enemy jungler, check if **any allied ward** was within 1000 units of the enemy jungler's path in the 30 seconds before the kill. |
| | **Spotted** = a ward saw the jungler coming, player died anyway |
| | **Unspotted** = no ward coverage on the jungler's approach |
| **Interpretation** | **Spotted deaths** = the information was available but the player didn't react (awareness issue). **Unspotted deaths** = no vision to begin with (warding issue). |
| **Useful for** | Separating vision problems from awareness problems. Spotted deaths are a player discipline issue; unspotted deaths are a team vision issue. |

---

## Team-Level Stats

### Gold Diff @ 15
| | |
|---|---|
| **Formula** | `(Sum of team gold at 15 min frame) - (Sum of enemy gold at 15 min frame)` |
| **Interpretation** | Positive = your team is ahead at 15 min. The magnitude matters: +500 is slight; +3000 is a huge lead. Tracks early game consistency across matches. |

### Objective Throw Detection
| | |
|---|---|
| **Formula** | Flags when your team **loses** a dragon/baron/herald despite having: |
| | • A gold lead (>1500g ahead), OR |
| | • More players alive/nearby |
| **Interpretation** | Identifies games where you had an advantage but gave up a major objective. These are high-impact mistakes that are often correctable with better coordination. |

---

## Teamfight Stats

### Teamfight Detection
| | |
|---|---|
| **Formula** | Groups `CHAMPION_KILL` events that occur within **15 seconds** and **4000 units** of each other. Requires **3+ kills** minimum to qualify as a teamfight. |
| **Stats tracked** | Outcome (won/lost/even), duration, first engager, kills/deaths per side, participants involved |
| **Useful for** | Identifying teamfight patterns: who engages, whether your team wins even or behind fights, and which players are consistently present or absent. |

---

## Reading the Trends

When viewing player trends over time, look for:

- **Improving KDA + decreasing deaths** → Player is learning to play safer
- **Harass score trending up** → Better laning trades
- **Greed index staying at 0** → Disciplined decision-making
- **Gank deaths decreasing + wards increasing** → Better vision habits
- **Flat or declining DPM with high gold%** → Not converting advantages
- **Low KP% consistently** → Playing too split from the team
