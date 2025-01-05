PLEASE CHECK THE DISCORD THREAD FOR UPDATE NOTICES, AND RE-DOWNLOAD THE MOD WHENEVER THERE'S AN UPDATE.

This mod requires the following mods by me:
https://github.com/jh1993/Bugfixes
https://github.com/jh1993/BugfixesExtended
https://github.com/jh1993/NoMoreScams

To install this mod, click on the green "Code" button on this page, then "Download ZIP". Please rename the "UnderusedOptions-main" folder to "UnderusedOptions" before putting it into your mods folder.

This mod makes changes to a number of spells and skills that I believe to be underwhelming or not interesting enough compared to other options. A secondary goal is to add new upgrades to certain spells that are severely lacking in meaningful, interesting upgrades.

Changelog:

Death Bolt:
- Can now target empty tiles.
- Damage upgrade cost reduced to 1 SP. This should make it more attractive as a quick power boost in early game, and useful for Cantrip Cascade builds.
- Withering upgrade replaced by Soul Feedback (5 SP): Death Bolt deals additional damage equal to 4 times the number of undead, demon, holy, and arcane minions you have. Mutually exclusive with Soul Battery.
- Soul Battery now also counts living units killed before you gain the upgrade, but the bonus damage is no longer counted by percentage shrine bonuses.

Fireball:
- Damage type upgrades now only affect enemies, and have been changed to redeal a percentage of fire damage as both of their respective damage types. The percentage is 25% plus 1/4 of each enemy's fire resistance.
- Ash Ball now only blinds enemies.

Lightning Bolt:
- Damage type upgrades now only deal extra damage to enemies.

Magic Missile:
- The bolt upgrades are no longer mutually exclusive. All of them will apply simultaneously if the target has the appropriate tags.
- Slaughter Bolt now also works on nature units, and now deals full arcane damage plus 2/3 dark, poison, and physical damage.
- Disruption Bolt now still deals arcane damage in addition to the new damage types.

Poison Sting:
- Now applies poison before dealing damage. If poison immunity is removed by the acidify upgrade, the target will still be poisoned.
- Torment (5 SP): Deal 1 extra damage per 10 turns of poison on the target, and 1 extra damage per turn of every other debuff on the target. Deal 1 extra damage per debuff on the target. Multiple stacks of the same type of debuff are counted as different debuffs.

Wolf:
- Wolf Pack cost reduced to 7, because I don't think anything should cost more than 7 SP; 7 SP should be enough for this upgrade anyways. It also counts as casting the spell twice, to make you not lose out on Thorn Garden and Icy Spriggan shrine procs. Number of wolves summoned now benefits from num summons bonuses.

Annihilate:
- Cascade upgrade removed, because the way it ignores line of sight while the spell itself requires line of sight is confusing, and it goes against the spell's identity as single-target damage.
- Max charges upgrade now costs 6 SP and gives +16 charges.
- Arcane Annihilation and Dark Annihilation merged into one upgrade that costs 2 SP, so you can save SP at a circle.
- Micro Annihilate (2 SP): Annihilate will deal 1 fire, 1 lightning, and 1 physical damage before its other hits. This damage is fixed, and cannot be increased using shrines, skills, or buffs. If you have the Nightmare Annihilation upgrade, this will deal dark and arcane damage as well.
- Chain Cast (5 SP): Each cast of Annihilate has a 75% chance to cast itself again at a random valid enemy target, as long as Annihilate has enough charges. This does not work if the spell is copied by a minion.

Blazerip:
- Fractal Rip (6 SP): Each hit of Blazerip now has a 10% chance of triggering another Blazerip on that tile. This can still happen even if an empty tile is hit. Each rip can trigger at most one additional rip.

Boiling Blood:
- Overhauled. Is now a global buff that grants bloodrage to minions when they deal fire/physical damage. This results in cleaner code, and has more synergy with other bloodrage support in my mods.

Chaos Barrage:
- Chaos Siege (5 SP): Chaos Barrage becomes a channeled spell. Each turn you channel this spell, you randomly take 4 fire, 4 lightning, or 4 physical damage per siege stack you have, and gain a siege stack, which causes Chaos Barrage to fire 2 more shards. Siege stacks are lost when you stop channeling. Not compatible with Chaos Calibration.
- Chaos Calibration (4 SP): The bolts of Chaos Barrage now deal damage in beams. Each turn, you gain a stack of calibration, which increases the range of Chaos Barrage by 1 and reduces the angle of its cone by 10 degrees, up to 6 stacks; the cone is initially 60 degrees wide. Casting Chaos Barrage causes you to lose all calibration stacks at the end of your turn and not gain a stack that turn. Not compatible with Chaos Siege.

Disperse:
- Phantom Zone (6 SP): Summon a void ghost in the former location of each unit teleported away. These void ghosts cannot be affected by this spell.

Eye of Fire:
- Eye of Blasting (3 SP): On hit, Eye of Fire also deals damage to all enemies adjacent to the target.

Eye of Ice:
- Eye of Freezing (3 SP): On hit, the target is frozen for 1 turn.

Eye of Lightning:
- Eye of Arcing (3 SP): On hit, Eye of Lightning also deals damage to a random enemy in line of sight of the target.

Eye of Rage:
- Lycanthropy upgrade replaced by Psychosis (5 SP): When an already berserk enemy is targeted by Eye of Rage, it now chooses a random valid target for one of its abilities. If the new target is another enemy, the first enemy is forced to use that ability on the new target. Otherwise the first enemy is stunned for 1 turn.

Fan of Flames:
- Previously, if you're somehow moved into the target square while channeling, you'll hit all tiles in range except yourself. Now, if this happens, you'll only hit all tiles in a radius of 5 plus bonuses, but there's now a Wheel of Flames upgrade (4 SP) that lets you simply target yourself with the spell to reproduce the effect.

Freeze:
- Absolute Zero (6 SP): When targeting an enemy, the target now permanently loses 100 ice resistance before being frozen.
- Permafrost (5 SP): When targeting an already frozen enemy, increase the duration of freeze on it by one third of this spell's duration if the result is greater than this spell's duration. Then deal ice damage equal to twice the target's freeze duration.

Healing Light:
- Completely overhauled, because the original is too situational. Now a level 3 spell that channels to heal 3 of your most damaged minions each turn, without requiring line of sight; best used with a small number of strong minions. Now has upgrades to cleanse debuffs, increase affected minions' max HP, and release holy bursts around affected minions.

Heavenly Blast:
- Spirit Bind cost reduced to 4 SP, and now inflicts a Spirit Binding debuff that raises the target as a spirit on death, which is removed at the beginning of your next turn.

Hollow Flesh:
- Instead of affecting a contiguous group of units, now affects all units in a 4-tile radius.
- No longer removes living tag from affected units.
- Max charges reduced to 6. Range increased to 9, and no longer requires line of sight.
- Max charges upgrade replaced by a +3 radius upgrade for 3 SP.
- Max HP loss upgrade increased to 3 SP due to affecting enemies more easily.
- Mockery of Life (2 SP): Affected units no longer gain dark resistance.
- Vigor Mortis (4 SP): When your minions are affected, their max HP are instead buffed by the same percentage. They do not suffer healing reduction, and instead gain 100 poison resistance. If you have the Fire Vulnerability upgrade, they instead gain 50 ice resistance. If you have the Mockery of Life upgrade, they still gain dark resistance and do not lose holy resistance.
- Flesh Rot (4 SP): When affecting a unit already affected by Hollow Flesh, this spell also deals poison damage equal to 25% of the max HP that unit lost from Hollow Flesh. If you have the Vigor Mortis upgrade, this will instead heal affected allies.

Hungry Maw:
- Range upgrade folded into base spell (from 7 to 11).
- Maw now has a melee bite that attacks 3 times.
- Pull Strength (3 SP): +2 tiles pulled.
- Shield Eater (3 SP): The maw gains 1 SH on kill and when removing SH with damage, up to the SH amount of this spell.

Invoke Savagery:
- As per my No More Scams mod, no longer tries to attack physical-immune targets unless the minion doing the attack has physical redeals.
- Blood Savagery (3 SP): Now also affects nature and demon units.
- Stampede (5 SP): If no melee targets are available, each ally will instead try to perform a charge attack with a range of 6 tiles. This attack does not stun.

Magnetize:
- Base radius and radius upgrade increased by 1 each.
- Pull strength and duration upgrades reduced to 2 SP.
- Universal Magnetism upgrade reduced to 3 SP.
- Planar Magnetism (4 SP): Each turn, after pulling all enemies in its radius, a magnetized target teleports a random enemy outside of its radius into a random tile in its radius.

Melt:
- As per my No More Scams mod, debuffs are now permanent.
- Now also an enchantment spell.
- Since the Absolute Zero upgrade for Freeze now exists, the ice resistance reduction upgrade is changed to fire resistance reduction instead, and increases cost to 4 SP.
- Can now target empty tiles, and now reduces resistances before dealing damage.

Petrify:
- Max charges increased to 20. Max charges upgrade changed to +10 charges for 2 SP.
- Duration (3 SP): +10 duration.
- Stone Mirror (4 SP): When targeting an enemy, the target is also permanently inflicted with Stone Mirror. When a petrified or glassified enemy with Stone Mirror dies, one of that enemy's allies in its line of sight will also be inflicted with Stone Mirror and the dead enemy's remaining duration of petrify and glassify. Targets without Stone Mirror are prioritized.

Regeneration Aura:
- Now has the holy tag, like Minion Regeneration.
- Global upgrade replaced by a +3 radius upgrade for 2 SP.
- Shielding Aura (5 SP): Minions in the radius have a chance to gain 1 SH per turn, to a max of 3 SH. The chance is equal to the minion's current HP percentage.

Soul Swap:
- Infernal Swap (3 SP): Soul Swap can target demon units as well.
- Soul Relay (3 SP): The minion that you swapped with will immediately take an action without costing a turn. If you have the Forced Transfer upgrade and swap with an enemy, that enemy is stunned for 1 turn.

Touch of Death:
- All the damage type upgrades now do the same amount of damage as dark damage done, but are increased to 2 SP. Now also has a lightning damage upgrade.
- Damage (4 SP): +200 damage.
- Touch of the Raven and Touch of the Vampire removed. Touch of the Reaper now has the reapers use your Touch of Death as well and no longer randomly teleport, and it's no longer limited to living units, but the reaper dies if it raises another reaper. Raising a unit as reaper no longer prevents it from also being raised as a skeleton.

Toxic Spores:
- Grey Mushbooms upgrade replaced by Toxic Mushbooms (4 SP), which is mutually exclusive with other mushboom type upgrades and gives 3-radiu 1-damage poison auras to mushbooms; the aura instantly activates 3 times on death. Stunning is redundant with Paralyzing Venom anyways, not to mention losing poison synergy.

Toxin Burst:
- Now applies poison before dealing damage.

Aether Swap:
- Restriction of not working on arcane-immune targets removed.
- If targeting an ally, give the target 1 SH instead of dealing damage.
- Patsy Swap (5 SP): You can now target yourself with this spell to give yourself a stack of Swapper's Scheme, which consumes another charge of the spell and counts as casting the spell twice. Whenever you are about to take damage, you automatically consume a stack of Swapper's Scheme to swap with a random valid enemy target of this spell, then negate that damage, while the target takes damage from both Aether Swap and the damage that you took. Damage negation applies before SH.
- Glitch Swap (5 SP): You can now target an empty tile with this spell to swap with a unit that does not exist, which consumes another charge of the spell and counts as casting the spell twice. This summons a glitch phantom at your old location, which is an arcane minion with 1 SH and the same max HP as you that can cast Aether Swap with the same upgrades, skills, and shrine as your own. The glitch phantom has a fixed lifetime of 1 turn.

Basilisk Armor:
- Max Charges upgrade removed.
- Petrify Duration (2 SP): +3 petrify duration.
- Thorns (4 SP): Enemies targeting you with spells also take 16 poison damage. If you have the Stunning Armor upgrade, also deal lightning damage. If you have the Freezing Armor upgrade, also deal ice damage. If you have the Glassifying Armor upgrade, also deal physical damage.
- Stunning Armor (2 SP): Basilisk Armor inflicts stun instead of petrify. Only one armor upgrade allowed.
- Freezing Armor (2 SP): Basilisk Armor inflicts freeze instead of petrify. Only one armor upgrade allowed.
- Glassifying Armor (2 SP): Basilisk Armor inflicts glassify instead of petrify. Only one armor upgrade allowed.

Blinding Light:
- Dark Units and damage upgrades were superfluous and thus folded into the base spell.
- Safety (3 SP): No longer affects friendly units.
- Searing Light (4 SP): Blinding Light now deals 1/7 of its normal damage to affected units that are not undead, demon, or dark, rounded up.

Blink:
- The damage upgrades now deal damage equal to the spell's range, and the bursts can pass through walls if the spell has blindcasting.

Choir of Angels:
- For consistency with other aura-type effects, the angels' song are no longer affected by damage bonuses, instead dealing fixed 2 fire and 2 holy damage. To compensate, they no longer damage allies or heal enemies.
- The angels' default resistances changed to 100% fire, 100% holy, and 0% dark.
- Fallen Choir (7 SP): The angels become demon units and gain 100 dark resistance. They gain a wailing attack with a cooldown of 7 turns that deals 7 dark damage to enemies in the same radius as their song, and an attack with 4 range that deals 4 fire damage. Unlike their song, these attacks benefit from bonuses to minion damage.
- The angels now sing passively each turn instead of requiring to act, so the singing won't interfere with the new abilities they can get from Fallen Choir. Even if an angel has no active abilities, its AI will still approach enemies that can be harmed by its song.

Combust Poison:
- Afterburn (4 SP): Instead of removing poison, this spell now sets remaining poison duration to 10 turns.
- Spontaneous Combustion (3 SP): Each turn, you have a chance to cast Combust Poison automatically if possible, consuming charges as usual. The chance is equal to the average poison duration of all enemies divided by 100, up to 100%.

Darkness:
- Max Charges upgrade removed.
- Clinging Darkness (4 SP): When affecting an enemy, this spell now inflicts blind for 2 turns, which stacks in duration with pre-existing blind it has.
- Holy Night (4 SP): While Darkness is active and you are blind, demon and undead enemies take 2 holy damage each turn. This damage is fixed, and cannot be increased using shrines, skills, or buffs. Mutually exclusive with other night upgrades.
- Concealing Night (6 SP): While Darkness is active and you are blind, whenever you or one of your demon or undead minions is about to be dealt damage, it has a 50% chance to negate that damage. Damage negation activates before SH.
- Fractal Night (7 SP): While Darkness is active and you are blind, half of all dark damage dealt to enemies is redealt as dark damage. This uses damage values before resistances, and triggers itself, but rounds down, stopping at 1 damage. Mutually exclusive with other night upgrades.

Death Chill:
- Soothing Chill (2 SP): Death Chill now lasts indefinitely and is considered a buff if applied to one of your minions, instead healing it each turn by an amount equal to this spell's damage stat. This still allows the minion to release a freezing explosion on death.

Devour Mind:
- All of the HP threshold effects are now calculated after redeals, to make the spell more forgiving.
- Now also works on nature units by default.
- Spirit Eater upgrade now also lets it work on holy and undead units.
- Mind Gouge (3 SP): If the target is over 50% HP after taking arcane damage, instead deal half dark damage to it.
- Mindless Eater (3 SP): Can now target all units. When targeting a unit outside of this spell's previously valid target groups, only the initial arcane damage is dealt.
- Mind Rot (4 SP): If the target takes arcane damage from this spell and dies, summon a void imp and an insanity imp near it. If the target takes dark damage from this spell and dies, summon a rot imp near it.

Dominate:
- HP threshold is now based on the damage stat, and the HP threshold upgrade is changed to a damage upgrade.
- Dominating an enemy now procs on-summon effects, and it now counts as a minion summoned by Dominate.
- Can now be used to remove berserk from allies.
- Mass Dominate (6 SP): When cast, Dominate now also affects all eligible units with the same name as the target within 3 tiles.
- Recruitment Bonus (3 SP): The target enemy is now healed to full HP after being dominated, and all of its debuffs are dispelled.

Earthquake:
- Added a 3 SP +25% strikechance upgrade.

Flame Burst:
- Melting Flame upgrade now passes through walls and melts all walls in the affected area.
- Bright Flame upgrade replaced by Phoenix Flame, which costs 4 SP and heals allies (except the wizard) instead of damaging them, and does not change the damage type. This makes it a natural extension of the base spell while providing additional healing with Pyrophilia, instead of changing the damage type to holy and losing out on all fire synergies.
- Spreading Flame now counts as casting the spell once per charge consumed.

Flame Gate:
- Gate Remnant (3 SP): When Flame Gate expires, or if you cast this spell again when it's active, you summon a fire elemental gate next to yourself, which automatically summons a fire elemental from this spell every 7 to 10 turns.

Frostfire Hydra:
- Now only has a single beam that alternates between fire and ice each turn. It counts as a breath weapon.
- Is now a permanent minion; minion duration upgrade removed.
- Dragon Mage (6 SP): The hydra will cast Melt on the target of its fire beam, and Freeze on the target of its ice beam. These spells gains all of your upgrades and bonuses.
- Splitting (4 SP): Upon reaching 0 HP, the hydra splits into a frost hydra and a fire hydra. Each hydra inherits one of the frostfire hydra's elements and resistances. Its beam only deals damage of that element, and has a 2 turns cooldown.

Ghostball:
- Possession (6 SP): Units in the area of Ghostball are now possessed for a duration equal to this spell's minion duration, which can stack. If the effect is removed prematurely, such as when the possessed unit dies, summon a ghost near it with duration equal to the remaining duration of possession. A possessed enemy takes dark damage each turn equal to this spell's minion damage. A possessed ally instead has melee retaliation dealing the same amount of dark damage to enemies.
- If you have the Ghost King or Mass upgrade, Possession has special passive effects that mimic their abilities. Details are in the Ghost King/Mass upgrade descriptions.

Giant Bear:
- Max charges upgrade removed and its benefits folded into the base spell.
- Armored Bear upgrade removed.
- Minion health and minion damage upgrades replaced by True Giant (7 SP): The bear grows to gargantuan size. Its HP is multiplied by 6, and its melee damage multiplied by 2.
- Venom bear healing nerfed to 1 HP whenever a unit takes poison damage, but its melee attack now inflicts 10 turns of poison that benefits from duration bonuses and stacks poison duration on the target.

Holy Armor:
- Divine Riposte (4 SP): While Holy Armor is active, if you pass your turn, you will retaliate for 18 holy damage whenever an enemy damages you, until the beginning of your next turn.

Holy Fire:
- No longer damages the caster.
- Damage is halved but now deals both fire and holy damage.
- Duration upgrade SP cost reduced to 2.
- Blindcasting (2 SP): Holy Fire no longer requires line of sight to cast.
- Fractal Cross (6 SP): Each tile in an affected horizontal line has a 10% chance to create a vertical line, and each tile in an affected vertical line has a 10% chance to create a horizontal line. Each line can create at most one additional line.

Iceball:
- Ice Crush upgrade reduced to 4 SP and now only affects enemies.

Ironize:
- No longer a conjuration spell.
- Retroactive (4 SP): You now gain Iron Aura when you cast this spell, during which all minions you summon will automatically gain Ironize for the remaining duration.

Lightning Halo:
- Now only damages enemies, and has a chance to damage all enemies in the radius equal to the distance between the enemy and the caster divided by the halo's radius.
- Max Charges upgrade removed.
- Base radius changed to 4. Radius upgrade changed to +2 radius for 2 SP.
- Damage upgrade cost increased to 3 SP.
- Duration upgrade changed to +6 duration for 3 SP.
- Divine Halo (5 SP): Lightning Halo also deals holy damage.
- Repelling Halo (4 SP): Enemies inside the halo are pushed away by 1 tile each turn until they are at the edge, before calculating whether they take damage.

Mercurize:
- Mercurial Vengeance no longer affects allies.
- Noxious Fumes now gains bonus radius equal to the square root of 10% of the geist's initial max HP, rounded up.
- Corrosion upgrade replaced with Mercurial Fortitude (2 SP): Mercurize now lasts indefinitely and is considered a buff if applied to one of your minions, instead healing it each turn by an amount equal to this spell's damage stat. This still allows the minion to spawn a geist on death.

Mystic Vision:
- Vision Aura upgrade cost increased to 7 SP, but is now retroactive, automatically applying to all newly summoned minions.

Nightmare Aura:
- The dream upgrades are changed to only summon old witches, aelves, and flame rifts. Each dream upgrade summons a minion for 9 turns for every 25 damage dealt, which should result in roughly the same amount as before.
- Dream Master (4 SP): Nightmare Aura now begins with 100 damage already stored in its damage pool, for the purpose of its Dream upgrades. This amount benefits 10 times from the damage bonuses of this spell.

Pain Mirror:
- Max Charges upgrade removed.
- False Pain (6 SP): Pain Mirror now counts incoming damage twice. The first time counts the raw incoming damage before resistances and SH, and the second time counts actual damage taken. The first count will trigger even if all of the incoming damage is resisted or blocked.
- Masochism (3 SP): Damage inflicted by allies will cause Pain Mirror to deal double damage.
- Deep Pain (5 SP): Pain Mirror penetrates enemy dark resistances by a percentage equal to your percentage of missing HP.

Plague of Filth:
- Is now a level 4 spell.
- Max channel upgrade rolled into the base spell.
- Summoned toads now have 18 HP, the same as enemy toads.
- Serpent Plague replaced by Fiery Vermin, Void Vermin, and Giant Vermin, all of which cost 7 SP and are incompatible with each other, making the spell summon flame toads and fire fly swarms, void toads and brain fly swarms, or 50% chance to summon towering toadbeasts and bags of bugs respectively. Brain fly swarms' attacks are changed to increasing one of the target's ability cooldowns by 1 if possible (doesn't work on units that can gain clarity), and otherwise deal damage again.

Prison of Thorns:
- Ice thorns upgrade no longer removes the thorns' melee attacks, which will be used against ice-immune enemies.

Seal Fate:
- The curse now uses a timer that ticks down as a per-turn effect instead of remaining duration, to interact better with reworked Permanence and Time Dilation from my Missing Synergies mod.
- Spreading Curse upgrade cost increased to 4 SP, but now if a cursed enemy dies to anything else, the curse jumps to a new enemy with its remaining duration.
- Hasten Doom (2 SP): When applying the curse to a target that already has Sealed Fate, the existing curse's timer is reduced by 1 turn.

Shrapnel Blast:
- The initial fire explosion now hits all units in the radius.
- The Puncturing Shards upgrade, which actually lets the shards pass through walls, is rolled into the base spell.
- The Magnetized Shards upgrade now makes it so that if there are no enemies in the area, no more shards will be fired. If it's smart enough to seek enemies, it should be smart enough to not hit allies. Also makes the initial explosion not hurt allies. Not compatible with the new Shrapnel Golem upgrade below.
- Shrapnel Golem (7 SP): Shrapnel Blast instead summons a shrapnel golem on the target tile, which is a fire metallic construct minion with 50 HP. The golem can fire shards that deal physical damage, which counts as damage dealt by this spell and inherits all of this spell's stats. It can fire the same number of shards as this spell otherwise can before dying, which will then deal fire damage from this spell to all enemies in the radius of the initial explosion of Shrapnel Blast. The golem has a 75% chance to immediately act again after firing a shard. Not compatible with Magnetized Shards.
- Unearth (4 SP): This spell can now be cast on chasms.

Silver Spear:
- The holy AoE no longer damages allies.
- Radius upgrade reduced to 3 SP.
- Blessed Silver (4 SP): The holy area damage of Silver Spear now also applies to undead and demon enemies.

Suspend Mortality:
- Now a level 5 spell with global range. Now applies reincarnation as a passive effect, with no duration limit and cannot be dispelled.
- Can no longer be cast on units that already have reincarnations, unless you have the Additive upgrade (see below).
- Max Charges (2 SP): +8 max charges.
- Additive (4 SP): If the target already has reincarnations, you can now cast this spell on the target to add its number of lives to said reincarnations.
- Automatic (5 SP): The first time you summon a minion each turn, you automatically cast Suspend Mortality on it, if possible. This consumes charges as usual.

Underworld Passage:
- Underworld Seeker (3 SP): You can now spend 1 extra charge to cast this spell even if you are not next to a chasm.
- Underworld Fauna (3 SP): After teleporting, summon a spirit strider, ghost mantis, ghost toad, large ghost worm ball, or ghostly goatia near you, chosen at random.

Void Beam:
- Void Sniper (4 SP): Void Beam deals additional damage to targets equal to twice their distances from the caster, rounded down.

Void Orb:
- Weakness changed to lightning damage.
- Now melts walls on all affected tiles. Red Dwarf upgrade removed.
- Red Giant (5 SP): Void Orb gains +1 radius. Void Orb also deals fire damage.
- Black Hole (5 SP): Each turn, Void Orb pulls all enemies in a double radius burst toward itself by 1 tile before dealing damage. The pull starts at the outermost edges of the burst, so an enemy may be pulled multiple times. Void Orb also deals dark damage.
- Void Walk upgrade affects twice the radius, and no longer turns chasms into floors; the teleport fails if the orb is on a chasm but the explosion still happens. Now has a chance to refund a charge of the spell, equal to remaining duration divided by max duration. Cost increased to 3 SP.

Blizzard:
- Hailstorm (6 SP): If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt ice damage equal to twice the damage of this spell, and frozen for 1 turn.

Bone Barrage:
- Now no longer requires line of sight.
- All original upgrades except Shambler Assembly removed. This spell is meant to give a strong single-target option to most conjuration builds, so its upgrades should support that niche instead of pull the spell toward conflicting directions in ways where the barrier to entry isn't worth the payoff.
- Range (3 SP): +50 range.
- Bone Regrowth (5 SP): Each ally damaged by Bone Barrage gains regeneration for 4 turns, each turn recovering HP equal to 25% of the HP lost.
- Ghost Bones (5 SP): Each ally also deals 4 dark damage to the target, regardless of the amount of damage the ally took; this damage benefits from bonuses to damage. Allies not in line of sight of the target will now also deal this additional dark damage to the target.
- Shambler Assembly now gives the shambler regen equal to 1/8 of its initial max HP if you have Bone Regrowth, and its attack deals additional dark damage equal to your number of minions at the time of casting plus minion damage bonus if you have Ghost Bones.

Chimera Familiar:
- Overhauled. Instead of copying spells when you cast them, the chimera now automatically copies an eligible spell every turn with its action, choosing the spell with the highest max charges and draining a charge of that spell. This counts as you casting the spell.
- Max Charges upgrade removed and folded into the base spell.
- The chimera's base HP is increased to 26, the same as those of enemy chaos chimeras. Its default attacks have 5 damage and 5 range.
- The chimera now starts with 75% fire and lightning resistance, and the Minion Resists upgrade is replaced by a 3 SP upgrade that gives +25% fire, +25% lightning, and +100% physical resistances (fire lion and lightning snake get +50% of the resistance they don't have instead of +25% to both).
- Dark/Nature/Arcane mimicry removed.
- Doublecast (7 SP): The chimera now copies two of your spells per turn. The fire lion and lightning snake that the chimera transforms into upon reaching 0 HP can now also copy your spells. The fire lion can only copy your fire and chaos spells. The lightning snake can only copy your lightning and chaos spells. Each of them can only cast one spell per turn.
- Wild Metamorphosis (1 SP): Chimera Familiar randomly gains 7 minion health, 3 minion damage, or 1 minion range. This upgrade can be purchased an unlimited number of times.

Conductance:
- Instead of copying lightning spells cast at the target, the debuff will have a 50% chance to cause any lightning damage dealt to the target, before resistances, to also be redealt to a target in line of sight up to 4 tiles away, and apply Conductance with duration equal to the current remaining duration to it after dealing damage.
- Multicopy and max charges upgrades removed.
- Cascade Range (4 SP): + 4 cascade range.
- Duration (3 SP): +10 duration.
- Strikechance (6 SP): +25% strikechance.

Conjure Memories:
- Completely reworked due to redundancy with Mystic Memory. It now memorizes allies you summon for 10 turns, and re-summons up to 2 dead memorized allies when it expires. Casting it again will replace the previous instance and inherit all memorized allies. Cannot be used to carry minions between levels, or duplicate unique minions in my mods.
- Now also an enchantment spell.
- Max charges increased to 3.
- Duration (3 SP): +10 duration.
- Max Charges (3 SP): +3 max charges.
- Num Summons (5 SP): 2 more dead allies are re-summoned when the effect expires.

Death Gaze:
- Now also an eye spell.

Death Shock:
- Base num targets is now 4.
- Same Target Cascades (3 SP): If a target survives the initial hit, the remaining cascades will hit the same target until it dies. Not compatible with Infinite Cascades.

Dispersion Field:
- Channeling Guard (3 SP): If you are channeling a spell, Dispersion Field will stun each affected enemy for 1 turn before teleporting it away. The stun duration is fixed and unaffected by bonuses.

Essence Flux:
- Level reduced to 3.
- Instead of affecting a contiguous group of units, now affects all units in a 4-tile radius.
- Max charges reduced to 6. Range increased to 9, and no longer requires line of sight.
- Max charges upgrade replaced by a +3 radius upgrade for 3 SP.
- Imbalanced Flux (5 SP): After affecting an enemy, the higher resistance of each pair will instead be set to the average of the pair. After affecting an ally, the lower resistance of each pair will instead be set to the average of the pair.

Fiery Tormentor:
- Relentless Torment (3 SP): The tormentor gains a teleport attack that deals the same damage as its soul suck, with range equal to its soul suck range plus torment radius.
- Tormentor's Remorse (2 SP): The tormentor's soul suck now also heals the wizard, but the total amount healed cannot exceed the total damage that the wizard has taken from tormentors summoned by this spell, before counting healing penalty.

Ice Drake:
- Dragon Mage changed to cast your Icicle every 3 turns.

Lightning Form:
- Is now also a translocation spell.
- Lightning Swap (3 SP): Lightning Form will now cause you to swap places with the target unit if possible, when targeting an occupied tile.
- Lightning Rod (4 SP): While Lightning Form is active and your lightning resistance is at least 100, any attempt to deal lightning damage to you will cause this spell to deal the same damage to a random enemy in line of sight. This upgrade cannot trigger itself.

Lightning Storm:
- Strike Twice (5 SP): If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt lightning damage equal to the damage of this spell. If you have the Strikechance upgrade, there is a 50% chance to deal damage again.

Orb Control:
- Max Charges (4 SP): +9 max charges.
- Range (2 SP): +5 range.
- Anti-Particle Beam (5 SP): When casting this spell, every allied orb will shoot a beam at the target tile. Each beam deals damage of each damage type the orb is not immune to, multiplied by 100% minus the orb's resistance to that damage type. The base damage is equal to 4 times the orb's level, and does not harm allies. A beam melts through walls if its corresponding orb can melt through walls; otherwise it is stopped by the first wall it encounters.

Permanence:
- Minion Permanence (5 SP): Each turn, each of your temporary minions that has only 1 turn remaining has a 25% chance to become permanent. Does not work on orb minions.
- Max Charges (3 SP): +4 max charges.

Purity:
- Pure Aura (2 SP): Each turn, remove a random debuff from a random ally.

Pyrostatic Pulse:
- Damage is halved but now deals both fire and lightning damage.
- Max charges upgrade replaced by Wallbreaker (4 SP): Pyrostatic Pulse no longer requires line of sight, and now destroys all walls on affected tiles.
- Channeled Pulse (5 SP): Pyrostatic Pulse becomes a channeled spell, and gains 2 damage:damage per turn channeled. Not compatible with Annihilation Pulse.
- Annihilation Pulse (7 SP): Pyrostatic Pulse also deals physical, arcane, and dark damage. Each cast of Pyrostatic Pulse consumes an additional charge and counts as casting the spell twice. Not compatible with Channeled Pulse.

Searing Seal:
- Life Fuel (4 SP): Each turn, Searing Seal now deals fire damage to you equal to 25% of your current HP, then heals you for the damage dealt.
- Purefire Seal (6 SP): Holy and arcane damage can now also fuel Searing Seal, but with half the efficiency of fire damage.

Siege Golems:
- Cannons now benefit from minion health bonuses. Golems' repair ability changed to heal for the cannon's max HP divided by 9, rounded up, which makes it unchanged without any minion health bonuses.
- Phoenix Ashes (6 SP): Each inferno cannon's attack and self-destruct will now heal allies instead of damaging them. The wizard and inferno cannons will not be healed, but will also not take damage.
- Wall Demolition (4 SP): Each inferno cannon's attack and self-destruct will now destroy walls.
- Phase Operator (2 SP): Siege golems gain the ability to teleport next to nearby inferno cannons.

Sight of Blood:
- Completely overhauled, because the original is thematically redundant with Eye of Rage while being too situational. Is now also an eye and conjuration spell. Every 3 turns, summon a blood vulture (same stats as thunderbird) near the target. Uses shot cooldown, but is not an eye buff. Lasts 15 turns.
- Shot Cooldown (4 SP): -1 shot cooldown.
- Bloodrage Bonus (3 SP): +1 bloodrage bonus.
- Feeding Frenzy (2 SP): On each activation, each allied unit in line of sight of the target that has bloodrage has a chance to gain another stack of bloodrage for 10 turns. The chance is equal to the percentage of the target's missing HP. The strength of this bloodrage stack is equal to the strength of the strongest bloodrage stack on the unit.
- Duration (3 SP): +15 duration.
- Unending Bloodrage (5 SP): When the target dies, the curse is applied to another random enemy in line of sight for its remaining duration.

Siphon Shields:
- Shield Burn upgrade replaced by Shield Shatter (4 SP), which deals physical damage (to benefit from Purestrike). Cost increased to 4 SP, but it now makes a separate hit for each SH siphoned, meaning it can remove up to twice the SH. Damage of each hit also benefits from damage bonuses.
- Shield Battery (3 SP): If you already have 20 SH then every additional SH stolen will instead give you a stack of shield battery. Each stack of shield battery is consumed at the end of your turn to give you 1 SH if you have less than 20 SH.

Storm Burst:
- Damage is halved but now deals both ice and lightning damage.
- Cloud Nova now chooses cloud type randomly. The clouds now benefit from damage and duration bonuses; thunderstorm clouds benefit doubly from damage.
- Cloud Nova increased to 4 SP, and now deals lightning damage to tiles containing blizzard clouds, and ice damage to tiles containing thunderstorm clouds.

Storm Drake:
- Drake Swap and Cloudform upgrades removed.
- Strikechance (2 SP): +25% strikechance.
- Cloud Surge (3 SP): If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt lightning damage equal to the storm drake's breath damage. If you have the Strikechance upgrade, there is a 50% chance to deal damage again.

Void Drake:
- Shields upgrade replaced by Shield Regen (3 SP): The Void Drake gains 1 SH every 3 turns, to a max of 2 SH.
- Essence Drake upgrade replaced by Essence Breath (4 SP): The Void Drake's breath no longer damages allies, and instead increases temporary allies' remaining durations by 1 turn.

Wall of Ice:
- Ice Mirror (4 SP): When an ice elemental is damaged by an enemy, that enemy has a chance to be frozen for 1 turn, equal to the ice elemental's percentage of missing HP.
- Forceful Construction (4 SP): "Wall of Ice no longer requires line of sight to cast. Wall and chasm tiles in the affected area are converted to floor tiles before summoning the ice elementals. Units in the affected area take 22 ice damage and are frozen for 3 turns. If a unit is killed then an ice elemental is summoned in its tile.

Watcher Form:
- Now also an eye spell.
- The resist buffs are rolled into the beam-shooting buff, so you can't get the resists separately via Purity anymore.
- Void Watcher (5 SP): Watcher Form also grants 100 arcane resist. Watcher Form now instead targets the furthest unit from the caster regardless of line of sight, melts through walls, and also deals half arcane damage.
- Watcher's Instinct (6 SP): While in Watcher Form, each turn you will automatically cast a random one of your lightning sorcery spells at a random valid enemy target, consuming charges as usual. If you have the Void Watcher upgrade, you will also cast an arcane sorcery spell each turn.

Wheel of Death:
- Royal Flush (7 SP): Wheel of Death now deals an additional hit of fire, lightning, physical, and arcane damage, each targeting a random enemy. The same enemy can be hit more than once. Not compatible with Death Roulette.

Ball Lightning:
- Weakness changed to arcane damage.
- Magnetic Pulse upgrade replaced by Lightning Barrage (6 SP): Targeting an existing lightning orb causes it to shoot a number of beams equal to twice its num targets, each targeting a random enemy in line of sight. An enemy can be hit by more than one beam.

Blue Lion:
- Holy bolt upgrade is now given in addition to the lion's melee attack, instead of replacing the latter.

Cantrip Cascade:
- Focused Cascade (4 SP): Each cantrip has a chance to be cast an additional time, equal to 1 divided by the number of units in the affected area at the time of casting this spell.
- Cantrip Specialization (4 SP): Each cantrip has a chance to be cast an additional time, equal to 1 divided by your number of cantrips.
- Cantrip Cleanup (4 SP): If Cantrip Cascade is out of charges at the beginning of your turn, the first cantrip you cast each turn will cast all of your other cantrips at the same target, consuming charges as normal, if possible. If you have the Focused Cascade upgrade, all of your cantrips will be cast a second time, if possible.

Chill Wind:
- Chill Vortex (4 SP): Each tile containing a thunderstorm or blizzard cloud that is affected by the wind current has a 50% chance to create a 2 tile burst that deals the same damage and applies the same duration of freeze.

Death Cleave:
- Level reduced to 4.
- Instead of working in sometimes unintuitive ways dependent on the game's internal spell queue that isn't visible to the player, a spell will now try to cleave as long as it kills its main target before the start of your next turn. This still works with channeling.
- Hungering Reach (4 SP): Each time your spell kills its primary target while Death Cleave is active, that spell gains a stacking range bonus of 2 tiles until the beginning of your next turn.
- Indiscriminate Slaughter (6 SP): Now whenever your spell's target dies for any reason before the start of your next turn, that spell will cleave from that target. If you targeted the dead unit with the same spell multiple times in one turn, the spell will only cleave once. If you targeted the dead unit with multiple different spells in one turn, all of them will cleave.

Fae Court:
- Glass Faery cost reduced to 6. It's anti-synergistic with Cracklevoid so the cost shouldn't be that high.

Floating Eye:
- Independent Eye (3 SP): The floating eye now has an attack with unlimited range that deals 2 arcane damage.
- Eternal Gaze (2 SP): When the floating eye loses a non-stacking eye buff, that buff will be reapplied with unlimited duration.

Flock of Eagles:
- Dive Attack upgrade folded into the base spell.
- White Ravens (5 SP): Summon white ravens instead of eagles. White ravens resist dark damage, and their melee attacks inflict 3 turns of blind. Not compatible with Thunderbirds.

Ice Phoenix:
- Max charges increased to 2.
- Quillmaker (6 SP): On death, the ice phoenix now summons a cerulean quill for 18 turns. The cerulean quill can summon living scrolls of Icicle and Heavenly Blast, which gain all of your upgrades and bonuses.
- Freeze Chance (4 SP): All of the ice phoenix's ice damage will freeze enemies for 3 turns.
- Icy Judgment (5 SP): Half of all of the ice phoenix's ice damage will be redealt as holy damage.

Mega Annihilate:
- Cascade upgrade removed, for the same reason as Annihilate.
- Overwhelm (3 SP): Each of the target's SH and buffs now has a chance to be removed before Mega Annihilate deals damage. The chance is equal to this spell's damage stat divided by the sum of its damage stat and the target's current HP.
- Sunder (5 SP): Each hit of Mega Annihilate now also permanently reduces the target's resistance to its damage type by 100. This stacks.

Pyrostatic Curse:
- Base radius increased to 5 and base duration increased to 6.
- No longer requires line of sight, and can now target your own tile.
- Linear Conductance no longer damages allies.
- Num Targets (4 SP): +2 num targets.
- Hex Ignition (5 SP): Targets that are already inflicted with Pyrostatic Hex will also take fire damage when you cast this spell. This damage is equal to the target's remaining Pyrostatic Hex duration plus this spell's bonuses to damage.

Ring of Spiders:
- No longer stuns or poisons allies.
- Damage upgrade SP cost reduced to 2, and no longer damages allies.
- Minion Health upgrade SP cost increased to 3.
- Steel Spiders (6 SP): Summon steel spiders instead of regular spiders. Not compatible with Aether Spiders.
- Tunneling (4 SP): Walls and chasms in the affected area will now be turned into floors before summoning.

Slime Form:
- As per my No More Scams mod, slimes now have a chance to gain max HP if their max HP divided by 10 isn't a whole number.
- The slime type upgrades now replace all of your slimes with the chosen variant, and are incompatible with each other. Fire and Ice Slime cost 3 SP, Void Slime costs 4 SP.
- Natural Slimes (4 SP): Summoned green slimes become nature minions. Summoned green slimes gain 10 HP and 7 damage. Incompatible with other slime color upgrades.
- Minion Health (3 SP): +10 minion health.
- Empowered Slimes (5 SP): Green slimes will acidify targets with their melee attacks, reducing poison resistance by 100. The attacks of red slimes gain 1 radius. The attacks of ice slimes will freeze targets for 1 turn. The attacks of void slimes gain 3 range.

Spider Queen:
- Now has a minion health upgrade in line with Ring of Spiders.
- Corpse Hatchery (4 SP): The spider queen now spawns an arachnid abomination on death, which will spawn a number of fully grown spiders on death equal to twice the queen's normal spawning amount.

Teleport:
- Void Teleport reduced to 3 SP.

Dragon Roar:
- Retroactive (4 SP): You now gain Dragon Aura when you cast this spell, during which all dragon minions you summon will automatically gain Dragon Roar for the remaining duration.

Gold Drake:
- Dragon Mage spell changed to Heavenly Blast with 3 turns cooldown. Cost increased to 5 SP.
- Breath Damage upgrade replaced by True Gold (4 SP): The gold drake becomes a metallic unit, gaining 100 lightning, 100 ice, 50 fire, and 50 physical resistances.

Imp Swarm:
- Dark Swarm removed. Fae Court does that better anyways.
- Fire Swarm (6 SP): Imp swarm summons firestorm imps, chaos imps, and ash imps instead of fire, spark, and iron imps. Not compatible with other swarm upgrades.

Mystic Memory:
- Now prioritizes your highest level spell that has no charges remaining.
- Mystic Residue: Whenever you use a mana potion, gain a stack of Mystic Residue. If this spell has no charges remaining, Mystic Residue stacks can be consumed to cast it instead.

Searing Orb:
- Damage is now fixed instead of benefitting from minion damage bonuses, since it was balanced around the assumption that the only minion damage bonuses it could get are Arch Conjurer and Claw shrine, which may no longer be true with mods.
- Safety (2 SP): Searing Orb no longer damages your minions.
- Radioactive Orb (6 SP): Searing Orb also deals poison damage.

Knightly Oath:
- Instead of damaging the caster on death, a knight now deals 40 damage to the caster when about to take fatal damage to fully heal self, restore SH, and remove all debuffs.
- Court upgrades now summon additional knights if you have bonuses to num summons. Not possible in the base game, but possible with mods.
- Promotion (6 SP): Each non-champion knight will be promoted to a champion after 20 turns.
- Undying Oath (7 SP): Knightly Oath can now save one knight from death per turn for free, without dealing damage to the caster. This is refreshed before the beginning of each of your turns.

Meteor Shower:
- Max charges increased to 2. Max channel increased to 10.
- Stun Duration upgrade folded into the base spell.
- Radius (4 SP): +1 radius.
- Rock Size upgrade replaced by Large Meteors (4 SP): The physical damage and stun radius of each meteor now gains a radius equal to half of this spell's radius stat, with a 50% chance to round up or down per meteor.

Multicast:
- Now only copies the first sorcery spell you cast per turn, to make it interact more intuitively with other spell-copying mechanics and less abusive with a few things in my other mods. Resets before the beginning of your turn.
- Adaptive Copy (6 SP): Level 5 and 4 spells are now copied 1 additional time. Level 3 and 2 spells are now copied 2 additional times. Level 1 spells are now copied 3 additional times.

Spikeball Factory:
- Forceful Construction (4 SP): Wall and chasm tiles in the affected area are converted to floor tiles, and units tossed up to 3 tiles away, before summoning the spikeball gates.

Word of Ice:
- HP threshold is now based on the damage stat.
- Damage (5 SP): +30 damage.

Arcane Accounting:
- Arcane Credit is no longer removed when you cast a spell, instead lasting for the whole turn. All spells that consume multiple charges on cast have been changed to trigger on-cast effects an equal number of times, meaning the extra charges consumed will be fully refunded.

Arcane Shield:
- SH limit increased to 2.

Crystal Power:
- Now makes glassify no longer increase ice resistance on enemies.
- Now instead inflicts an ice resonance debuff equal to the duration of the freeze inflicted, which persists after unfreezing. Damage buff is based on the number of units with glassify and ice resonance. If freeze duration is refreshed or extended, ice resonance duration will be adjusted to match if shorter. If ice resonance is removed prematurely and the enemy is still frozen, it will automatically reapply itself.

Faestone:
- Now counts as a unique minion for the purpose of Conjure Memories.
- Using a mana potion now resurrects the faestone if it's dead.
- Now has 100% arcane and poison resistance and is flying.
- The arcane and nature spell effects have been combined into one that triggers for either tag, and now also makes the faestone immediately act once.
- Can now swap places with your other minions when teleporting, if the triggering spell is not a conjuration spell.

Ghostfire:
- Fire ghosts now have 100% dark resistance, to not anti-synergize with ghostfire tormentors.

Hibernation:
- Now also works on nature and ice minions.
- Now works even if a minion is immune or shielded.
- Now instead a separate regen buff for the same duration as freeze. This regen is removed on dealing fire or physical damage to the unit.
- If the unit is immune to ice and is not frozen, applying and removing the regen counts as applying and removing freeze.

Holy Water:
- Affected allies also deal 2 holy or ice damage once to all enemies in a radius equal to the number of SH they have, even if their SH are maxed out. Holy damage from this skill cannot trigger itself. Cost increased to 5 SP.

Minion Regeneration:
- Now also heals a minion for 2 HP whenever it is about to be healed by any other source.

Unholy Alliance:
- Now retroactively applies to already summoned minions, including when a minion's tags change.
- Demon and undead minions gain 100% holy resistance.
- SP cost increased to 5.

White Flame:
- Is now level 5, only affects enemies, and reduces the target's fire resistance by 100% until the beginning of your next turn.

Acid Fumes:
- Now prioritizes the closest unacidified enemy.

Frozen Fragility:
- Now instead inflicts a fragility debuff equal to the duration of the freeze inflicted, which persists after unfreezing. If freeze duration is refreshed or extended, fragility duration will be adjusted to match if shorter. If fragility is removed prematurely and the enemy is still frozen, it will automatically reapply itself.

Glittering Dance:
- Now has the nature tag.

Houndlord:
- Using a mana potion now tries to replenish the number of hounds to the maximum.

Hypocrisy:
- Completely overhauled. Now applies duration-stacking holy hypocrisy equal to spell level when dealing damage with holy spells, and dark hypocrisy similarly with dark spells. When both types of hypocrisy are applied, consume them to deal holy and dark damage equal to each's respective duration, and apply duration-stacking blind equal to combined duration.

Righteous March:
- Each enemy in LoS of the target now also has a 50% chance to take 1 fixed holy damage.

Storm Caller:
- Thunderstorm clouds now benefit doubly from damage bonuses.

Bone Guard:
- Now also summons a bone archer, and all summoned units have +1 reincarnation.
- Using a mana potion now replenishes the summons.
- Now drain max HP from all enemies. The drain can now kill but is blockable by SH.

Frostbite:
- Now instead inflicts a frostbite debuff equal to the duration of the freeze inflicted, which persists after unfreezing. If freeze duration is refreshed or extended, frostbite duration will be adjusted to match if shorter. If frostbite is removed prematurely and the enemy is still frozen, it will automatically reapply itself.
- SP cost reduced to 5.

Ice Tap: 
- Now instead inflicts an ice tap debuff equal to the duration of the freeze inflicted, which persists after unfreezing. If freeze duration is refreshed or extended, ice tap duration will be adjusted to match if shorter. If frostbite is removed prematurely and the enemy is still frozen, it will automatically reapply itself.
- Now casts the triggering spell on every valid enemy target with ice tap (based on the spell's own range, and can ignore line of sight if the spell can), removing ice tap and freeze in the process.
- Now only copies the first arcane spell you cast each turn, for consistency.

Inferno Engines:
- Level increased to 7, but the effect is now fully retroactive, automatically applying to all newly summoned metallic minions and minions that become metallic.

Lightning Warp:
- Now inflicts a Warp Lightning debuff on affected enemies, then deals damage to all enemies with Warp Lightning. This means that if Lightning Warp is triggered more than once in a turn, the initially affected enemies will be damaged every time the skill triggers, no matter where they're teleported to.
- Damage now occurs even if the target is not teleported.
- Max teleport range increased to 12 but no longer has a minimum teleport range. This means the teleport no longer fails if there are no empty tiles within minimum range.

Scalespinner:
- Now gives a minion additional resistance to bring it up to 100 if a minion has weakness to the triggering element.
- Now also gives you the same effect, but that effect is removed at the end of the dragon's turn, so it only protects you from friendly fire.

Metal Lord:
- Now also gives +20 minion health.

Orb Lord:
- Now also gives +4 minion damage and +1 radius.