from Spells import *
from Level import *
from Monsters import *
from Upgrades import *
from Variants import *
from RareMonsters import *

import mods.BugsAndScams.Bugfixes
import mods.BugsAndScams.NoMoreScams
from mods.BugsAndScams.NoMoreScams import is_immune, FloatingEyeBuff
from mods.BugsAndScams.Bugfixes import RemoveBuffOnPreAdvance

import sys, math, random

curr_module = sys.modules[__name__]

class AbsoluteZeroBuff(Buff):
    def on_init(self):
        self.name = "Absolute Zero"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Ice.color
        self.resists[Tags.Ice] = -100

class ShieldEaterBuff(Buff):

    def __init__(self, spell):
        self.max = spell.get_stat("shields")
        Buff.__init__(self)
        self.color = Tags.Shield.color

    def on_init(self):
        self.description = "On kill and when attacking a shielded target, gain 1 SH, up to a max of %i." % self.max
        self.global_triggers[EventOnDeath] = self.on_death
        self.global_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def on_death(self, evt):
        if evt.damage_event and isinstance(evt.damage_event.source, Spell) and evt.damage_event.source.caster is self.owner:
            if self.owner.shields < self.max:
                self.owner.add_shields(1)
    
    def on_pre_damaged(self, evt):
        if evt.damage > 0 and isinstance(evt.source, Spell) and evt.source.caster is self.owner and evt.unit.shields and evt.unit.resists[evt.damage_type] < 100:
            if self.owner.shields < self.max:
                self.owner.add_shields(1)

class StoneCurseBuff(Buff):

    def on_init(self):
        self.name = "Stone Curse"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Dark.color
        for tag in [Tags.Holy, Tags.Dark, Tags.Arcane, Tags.Poison]:
            self.resists[tag] = -50

class StoneCurseUpgrade(Upgrade):

    def on_init(self):
        self.name = "Stone Curse"
        self.level = 6
        self.description = "Whenever an enemy is inflicted with [petrify] or [glassify], inflict Stone Curse to it, which reduces [holy], [dark], [arcane], and [poison] resistances by [50:damage].\nThis has a 50% chance to consume a charge from Petrify, and Stone Curse will not be inflicted if it tries but fails to consume a charge."
        self.global_triggers[EventOnBuffApply] = self.on_buff_apply
    
    def on_buff_apply(self, evt):
        if not are_hostile(self.owner, evt.unit) or (not isinstance(evt.buff, PetrifyBuff) and not isinstance(evt.buff, GlassPetrifyBuff)):
            return
        if evt.unit.has_buff(StoneCurseBuff):
            return
        if random.random() >= 0.5:
            if self.prereq.cur_charges > 0:
                self.prereq.cur_charges -= 1
            else:
                return
        evt.unit.apply_buff(StoneCurseBuff())

class RedMushboomBuff(Buff):

    def __init__(self, bonus=0):
        self.damage = 9 + bonus
        Buff.__init__(self)

    def on_init(self):
        self.name = "Fire Spores"
        self.owner_triggers[EventOnDeath] = self.on_death
        self.description = "On death, deals %i fire damage to adjacent units" % self.damage
        self.color = Tags.Fire.color

    def on_death(self, evt):
        self.owner.level.queue_spell(self.explode())

    def explode(self):
        for p in self.owner.level.get_adjacent_points(self.owner):
            self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Fire, self)
        yield

class BasiliskArmorBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Basilisk Armor"
        self.color = Tags.Nature.color
        self.petrify_duration = self.spell.get_stat("petrify_duration")
        self.thorns = self.spell.get_stat("thorns")
        self.damage = self.spell.get_stat("damage", base=16)
        if self.spell.get_stat("stun"):
            self.debuff = Stun
        elif self.spell.get_stat("freeze"):
            self.debuff = FrozenBuff
        elif self.spell.get_stat("glassify"):
            self.debuff = GlassPetrifyBuff
        else:
            self.debuff = PetrifyBuff
        self.global_triggers[EventOnSpellCast] = self.on_spell_cast
    
    def on_spell_cast(self, evt):
        if are_hostile(evt.caster, self.owner) and evt.x == self.owner.x and evt.y == self.owner.y:
            evt.caster.apply_buff(self.debuff(), self.petrify_duration)
            if self.thorns:
                evt.caster.deal_damage(self.damage, Tags.Poison, self.spell)
                if self.debuff is Stun:
                    evt.caster.deal_damage(self.damage, Tags.Lightning, self.spell)
                elif self.debuff is FrozenBuff:
                    evt.caster.deal_damage(self.damage, Tags.Ice, self.spell)
                elif self.debuff is GlassPetrifyBuff:
                    evt.caster.deal_damage(self.damage, Tags.Physical, self.spell)

class DarknessBuff(Spells.DarknessBuff):

    def __init__(self, spell):
        self.spell = spell
        Spells.DarknessBuff.__init__(self)
        self.horizon = spell.get_stat("horizon")
        if spell.get_stat("echo"):
            self.global_triggers[EventOnPreDamaged] = self.on_pre_damaged

    def effect_unit(self, unit):
        if Tags.Undead in unit.tags or Tags.Demon in unit.tags:
            if not self.horizon or not are_hostile(unit, self.owner) or random.random() >= distance(unit, self.owner)*0.05:
                return
        existing = unit.get_buff(BlindBuff)
        if existing and existing.turns_left == 1:
            unit.remove_buff(existing, trigger_buff_remove_event=False)
            unit.apply_buff(BlindBuff(), 1, trigger_buff_apply_event=False)
        else:
            unit.apply_buff(BlindBuff(), 1)
    
    def on_pre_damaged(self, evt):
        if evt.damage <= 0 or not are_hostile(evt.unit, self.owner) or not self.owner.is_blind():
            return
        if evt.source.owner and (Tags.Undead in evt.source.owner.tags or Tags.Demon in evt.source.owner.tags) and not are_hostile(evt.source.owner, self.owner):
            evt.unit.deal_damage(evt.damage//2, evt.damage_type, self.spell)

class SpiritBindingBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Spirit Binding"
        self.color = Tags.Holy.color
        self.buff_type = BUFF_TYPE_CURSE
        self.owner_triggers[EventOnDeath] = self.on_death
    
    def on_death(self, evt):
        spirit = Unit()
        spirit.name = "Spirit"
        spirit.asset_name = "holy_ghost" # temp
        spirit.max_hp = 4
        spirit.spells.append(SimpleRangedAttack(damage=2, damage_type=Tags.Holy, range=3))
        spirit.turns_to_death = 7
        spirit.tags = [Tags.Holy, Tags.Undead]
        spirit.buffs.append(TeleportyBuff())
        apply_minion_bonuses(self.spell, spirit)
        spirit.resists[Tags.Holy] = 100
        spirit.resists[Tags.Dark] = -100
        spirit.resists[Tags.Physical] = 100
        self.spell.summon(spirit, target=self.owner)

class FrostfireHydraDragonMage(Upgrade):

    def on_init(self):
        self.name = "Dragon Mage"
        self.level = 6
        self.description = "The hydra will cast Melt on the target of its fire beam, and Freeze on the target of its ice beam.\nThese spells gains all of your upgrades and bonuses."
        self.global_triggers[EventOnSpellCast] = self.on_spell_cast
    
    def on_applied(self, owner):
        self.melt = MeltSpell()
        self.freeze = Freeze()
        for spell in [self.melt, self.freeze]:
            spell.range = RANGE_GLOBAL
            spell.max_charges = 0
            spell.cur_charges = 0
            spell.statholder = self.owner

    def on_spell_cast(self, evt):
        if evt.caster.source is not self.prereq:
            return
        if evt.spell.name != "Hydra Beam":
            return
        spell = None
        if evt.spell.damage_type == Tags.Ice:
            spell = self.freeze
        elif evt.spell.damage_type == Tags.Fire:
            spell = self.melt
        if not spell:
            return
        spell.caster = evt.caster
        spell.owner = evt.caster
        if not spell.can_cast(evt.x, evt.y):
            return
        self.owner.level.act_cast(evt.caster, spell, evt.x, evt.y, pay_costs=False)
    
    # For my No More Scams mod
    def can_redeal(self, target, source, damage_type):
        if source.owner and source.owner.source is not self.prereq:
            return False
        if source.name != "Hydra Beam":
            return False
        if damage_type == Tags.Ice:
            if self.freeze.get_stat("absolute_zero") and not target.has_buff(AbsoluteZeroBuff) and target.resists[Tags.Ice] < 200:
                return True
        if damage_type == Tags.Fire:
            if self.melt.get_stat("fire_resist") and not target.has_buff(MeltBuff) and target.resists[Tags.Fire] < 200:
                return True
        return False

class PolarBearFreeze(Hibernate):
    def on_init(self):
        Hibernate.on_init(self)
        self.name = "Mass Freeze"
        self.description = "Freezes all units in a 4 tile radius except the wizard for 4 turns."
    def cast_instant(self, x, y):
        for unit in self.caster.level.get_units_in_ball(self.caster, 4):
            if unit.is_player_controlled:
                continue
            unit.apply_buff(FrozenBuff(), 4)

class PolarBearAura(DamageAuraBuff):

    def __init__(self):
        DamageAuraBuff.__init__(self, 1, Tags.Ice, 4)
        self.heal = 10
        self.description = "While frozen, heals for %i HP per turn and deals %i ice damage to all enemies in a %i radius." % (self.heal, self.damage, self.radius)
        self.name = "Icy Body"
        self.color = Tags.Ice.color
    
    def on_advance(self):
        if self.owner.has_buff(FrozenBuff):
            self.owner.deal_damage(-self.heal, Tags.Heal, self)
            DamageAuraBuff.on_advance(self)
        elif self.owner.resists[Tags.Ice] > 100:
            amount = self.owner.resists[Tags.Ice] - 100
            while amount > 100:
                self.owner.deal_damage(-self.heal, Tags.Heal, self)
                DamageAuraBuff.on_advance(self)
                amount -= 100
            if random.random() < amount/100:
                self.owner.deal_damage(-self.heal, Tags.Heal, self)
                DamageAuraBuff.on_advance(self)
    
    def get_tooltip(self):
        return self.description

class GiantBearRoar(BreathWeapon):

    BEAR_TYPE_DEFAULT = 0
    BEAR_TYPE_VENOM = 1
    BEAR_TYPE_BLOOD = 2
    BEAR_TYPE_POLAR = 3

    def __init__(self, bear_type=BEAR_TYPE_DEFAULT):
        self.bear_type = bear_type
        BreathWeapon.__init__(self)
    
    def on_init(self):
        self.name = "Roar"
        self.description = "Enemies are "
        if self.bear_type == GiantBearRoar.BEAR_TYPE_VENOM:
            self.description += "stunned for 3 turns and poisoned for 5 turns.\nAllies regenerate 1 HP per turn for 5 turns."
            self.effect = Tags.Poison
        elif self.bear_type == GiantBearRoar.BEAR_TYPE_BLOOD:
            self.description += "berserked for 3 turns.\nAllies gain bloodlust for 10 turns."
            self.effect = Tags.Dark
        elif self.bear_type == GiantBearRoar.BEAR_TYPE_POLAR:
            self.description += "frozen for 3 turns.\nAllies are healed for 10 HP."
            self.effect = Tags.Ice
        else:
            self.description += "stunned for 3 turns."
            self.effect = Tags.Physical
    
    def per_square_effect(self, x, y):
        self.caster.level.show_effect(x, y, self.effect, minor=True)
        unit = self.caster.level.get_unit_at(x, y)
        if not unit or unit.is_player_controlled:
            return
        if self.bear_type == GiantBearRoar.BEAR_TYPE_VENOM:
            if are_hostile(unit, self.caster):
                unit.apply_buff(Stun(), 3)
                unit.apply_buff(Poison(), 5)
            else:
                unit.apply_buff(RegenBuff(1), 5)
        elif self.bear_type == GiantBearRoar.BEAR_TYPE_BLOOD:
            if are_hostile(unit, self.caster):
                unit.apply_buff(BerserkBuff(), 3)
            else:
                unit.apply_buff(BloodrageBuff(3), 10)
        elif self.bear_type == GiantBearRoar.BEAR_TYPE_POLAR:
            if are_hostile(unit, self.caster):
                unit.apply_buff(FrozenBuff(), 3)
            else:
                unit.deal_damage(-10, Tags.Heal, self)
        else:
            if are_hostile(unit, self.caster):
                unit.apply_buff(Stun(), 3)

class CursedBones(Upgrade):

    def on_init(self):
        self.name = "Cursed Bones"
        self.level = 5
        self.description = "Bone Barrage also deals [dark] damage."
        self.global_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def qualifies(self, target, source, damage_type):
        if not are_hostile(target, self.owner):
            return False
        if damage_type != Tags.Physical:
            return False
        if source is self.prereq:
            return True
        if source.owner and source.owner.source is self.prereq:
            return True
        return False

    def on_pre_damaged(self, evt):
        if self.qualifies(evt.unit, evt.source, evt.damage_type):
            evt.unit.deal_damage(evt.damage, Tags.Dark, evt.source)
    
    # For my No More Scams mod
    def can_redeal(self, target, source, damage_type):
        return self.qualifies(target, source, damage_type) and target.resists[Tags.Dark] < 100

class ChimeraFamiliarSpellConduit(Spell):

    def __init__(self, fire=True, lightning=True, casts=1):
        self.fire = fire
        self.lightning = lightning
        self.casts = casts
        Spell.__init__(self)

    def on_init(self):
        self.name = "Spell Conduit"
        self.range = 0
        self.description = "Casts %i of the wizard's %s%s%s%s or chaos sorcery spells with the highest max charges that can be cast from this tile, consuming a charge from them and also counting as the wizard casting them." % (self.casts, "fire" if self.fire else "", ", " if self.fire and self.lightning else "", "lightning" if self.lightning else "", "," if self.fire and self.lightning else "")
    
    def copy_spell(self, spell):
        spell_copy = type(spell)()
        spell_copy.statholder = self.owner.source.caster
        spell_copy.owner = self.owner
        spell_copy.caster = self.caster
        spell_copy.max_charges = 0
        spell_copy.cur_charges = 0
        return spell_copy

    def get_wizard_spells(self):
        tags = [Tags.Chaos]
        if self.fire:
            tags.append(Tags.Fire)
        if self.lightning:
            tags.append(Tags.Lightning)
        spells = [spell for spell in self.owner.source.caster.spells if Tags.Sorcery in spell.tags and [tag for tag in tags if tag in spell.tags] and spell.cur_charges > 0]
        spells.sort(reverse=True, key=lambda spell: spell.get_stat("max_charges"))
        return spells
    
    def can_cast(self, x, y):
        for spell in self.get_wizard_spells():
            if self.copy_spell(spell).get_ai_target():
                return True
        return False
    
    def cast_instant(self, x, y):
        casts_left = self.casts
        for spell in self.get_wizard_spells():
            spell_copy = self.copy_spell(spell)
            target = spell_copy.get_ai_target()
            if not target:
                continue
            spell.cur_charges -= 1
            self.caster.level.act_cast(self.caster, spell_copy, target.x, target.y, pay_costs=False)
            self.caster.level.event_manager.raise_event(EventOnSpellCast(spell, self.owner.source.caster, target.x, target.y), self.owner.source.caster)
            casts_left -= 1
            if not casts_left:
                return

class ChimeraFamiliarSelfSufficiency(Upgrade):
    def on_init(self):
        self.name = "Self Sufficiency"
        self.level = 4
        self.spell_bonuses[ChimeraFarmiliar]["minion_damage"] = 5
        self.spell_bonuses[ChimeraFarmiliar]["minion_range"] = 3

class AntiConductanceBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE

class ConductanceBuff(Buff):
	
    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)

    def on_init(self):
        self.name = "Conductance"
        self.color = Tags.Lightning.color
        self.resists[Tags.Lightning] = -self.spell.get_stat("resistance_debuff")
        self.cascade_range = self.spell.get_stat("cascade_range")
        self.buff_type = BUFF_TYPE_CURSE
        self.asset = ['status', 'conductance']
        self.owner_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def on_pre_damaged(self, evt):
        if evt.damage_type != Tags.Lightning:
            return
        targets = [unit for unit in self.owner.level.get_units_in_ball(self.owner, self.cascade_range) if are_hostile(self.spell.caster, unit) and self.owner.level.can_see(self.owner.x, self.owner.y, unit.x, unit.y) and not unit.has_buff(AntiConductanceBuff)]
        if not targets:
            return
        conductive_targets = [target for target in targets if target.has_buff(curr_module.ConductanceBuff)]
        if conductive_targets:
            target = random.choice(conductive_targets)
        else:
            target = random.choice(targets)
        target.apply_buff(AntiConductanceBuff(), 1)
        self.owner.level.queue_spell(self.bolt(target, evt.damage))
    
    def bolt(self, target, damage):
        for point in Bolt(self.owner.level, self.owner, target):
            self.owner.level.show_effect(point.x, point.y, Tags.Lightning, minor=True)
            yield
        target.deal_damage(damage, Tags.Lightning, self.spell)
        duration = self.turns_left//2
        if duration:
            target.apply_buff(curr_module.ConductanceBuff(self.spell), duration)

class FieryTormentorRemorse(Upgrade):

    def on_init(self):
        self.name = "Tormentor's Remorse"
        self.level = 4
        self.description = "The range of the tormentor's soul suck becomes the same as the radius of its torment, if the latter is higher.\nIts soul suck now also heals the wizard, but the total amount healed cannot exceed the total damage that the wizard has taken from tormentors summoned by this spell, before counting [heal] resistance."
        self.global_triggers[EventOnUnitAdded] = self.on_unit_added
        self.global_triggers[EventOnDamaged] = self.on_damaged
        self.healing_pool = 0
    
    def on_unit_added(self, evt):
        if evt.unit.source is not self.prereq:
            return
        evt.unit.apply_buff(FieryTormentorRemorseIndicator(self))
        for spell in evt.unit.spells:
            if spell.name == "Soul Suck":
                spell.range = max(self.prereq.get_stat("minion_range"), self.prereq.get_stat("radius"))
                return
    
    def on_damaged(self, evt):
        if not evt.source.owner or evt.source.owner.source is not self.prereq:
            return
        if evt.source.name == "Soul Suck" and evt.unit is not self.owner:
            heal = min(evt.damage, self.owner.max_hp - self.owner.cur_hp, self.healing_pool)
            if not heal:
                return
            self.healing_pool -= heal
            self.owner.deal_damage(-heal, Tags.Heal, evt.source)
        elif evt.unit is self.owner:
            self.healing_pool += evt.damage

class FieryTormentorRemorseIndicator(Buff):
    def __init__(self, upgrade):
        self.upgrade = upgrade
        Buff.__init__(self)
        self.color = Tags.Heal.color
        self.buff_type = BUFF_TYPE_PASSIVE
        self.description = "Soul Suck heals the wizard for an amount equal to the damage done. Can apply no more than 0 healing."
    def on_advance(self):
        self.description = "Soul Suck heals the wizard for an amount equal to the damage done. Can apply no more than %i healing." % self.upgrade.healing_pool

class LightningFormBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        self.ice = spell.get_stat("ice")
        self.cloud = spell.get_stat("cloud")
        Buff.__init__(self)
        self.transform_asset_name = "player_lightning_form"
        self.name = "Lightning Form"
        self.buff_type = BUFF_TYPE_BLESS
        self.asset = ['status', 'lightning_form']
        self.color = Tags.Lightning.color
        self.description = "Whenever you cast a lightning%s spell, if the target square is empty, teleport to the target square.\n\nThis enchantment ends if you move or cast a non lightning%s spell%s." % (" or ice" if self.ice else "", " or ice" if self.ice else "", (" on a tile without a storm%s cloud" % (" or blizzard" if self.ice else "")) if self.cloud else "")
        self.cast = True
        self.stack_type = STACK_TYPE_TRANSFORM

    def on_advance(self):
        remove = not self.cast
        if self.cloud:
            cloud = self.owner.level.tiles[self.owner.x][self.owner.y].cloud
            targets = [p for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.spell.get_stat("radius", base=3)) if not self.owner.level.tiles[p.x][p.y].is_wall() and not self.owner.level.tiles[p.x][p.y].cloud]
            if targets:
                target = random.choice(targets)
            else:
                target = None
            if isinstance(cloud, StormCloud):
                remove = False
                if target:
                    new_cloud = StormCloud(self.owner)
                    new_cloud.source = self.spell
                    new_cloud.duration = self.spell.get_stat("duration", base=5)
                    self.owner.level.add_obj(new_cloud, target.x, target.y)
            elif self.ice and isinstance(cloud, BlizzardCloud):
                remove = False
                if target:
                    new_cloud = BlizzardCloud(self.owner)
                    new_cloud.source = self.spell
                    new_cloud.duration = self.spell.get_stat("duration", base=5)
                    self.owner.level.add_obj(new_cloud, target.x, target.y)
        if remove:
            self.owner.remove_buff(self)
        self.cast = False

    def on_init(self):
        self.resists[Tags.Lightning] = 100
        self.resists[Tags.Physical] = 100
        if self.ice:
            self.resists[Tags.Ice] = 100
        self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
        self.owner_triggers[EventOnPass] = self.on_pass

    def on_spell_cast(self, spell_cast_event):
        if Tags.Lightning in spell_cast_event.spell.tags or (self.ice and Tags.Ice in spell_cast_event.spell.tags):
            self.cast = True
            if self.owner.level.can_move(self.owner, spell_cast_event.x, spell_cast_event.y, teleport=True):
                self.owner.level.queue_spell(self.do_teleport(spell_cast_event.x, spell_cast_event.y))
                    
    def on_pass(self, evt):
        if self.owner.has_buff(ChannelBuff):
            self.cast = True

    def do_teleport(self, x, y):
        if self.owner.level.can_move(self.owner, x, y, teleport=True):
            yield self.owner.level.act_move(self.owner, x, y, teleport=True)

class PyrostaticSurgeBuff(Buff):
    def on_init(self):
        self.name = "Pyrostatic Surge"
        self.color = Tags.Fire.color
        self.spell_bonuses[PyrostaticPulse]["damage"] = 1
        self.stack_type = STACK_INTENSITY
    def on_advance(self):
        if not self.owner.has_buff(ChannelBuff):
            self.owner.remove_buff(self)

class SightOfBloodBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Sight of Blood"
        self.asset = ["UnderusedOptions", "Statuses", "sight_of_blood"]
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Demon.color
        self.freq = max(1, self.spell.get_stat("shot_cooldown"))
        self.cooldown = self.freq
        self.minion_health = self.spell.get_stat("minion_health")
        self.minion_damage = self.spell.get_stat("minion_damage")
        self.minion_range = self.spell.get_stat("minion_range")
        self.bloodlust_bonus = self.spell.get_stat("bloodlust_bonus")
        self.feeding_frenzy = self.spell.get_stat("feeding_frenzy")
        if self.spell.get_stat("unending"):
            self.owner_triggers[EventOnDeath] = self.on_death

    def on_advance(self):
        self.cooldown -= 1
        if self.cooldown == 0:
            self.cooldown = self.freq

            unit = Unit()
            unit.name = "Blood Vulture"
            unit.asset_name = "blood_hawk"
            unit.max_hp = self.minion_health
            unit.flying = True
            claw = SimpleMeleeAttack(damage=self.minion_damage, onhit=bloodrage(self.bloodlust_bonus))
            claw.name = "Frenzy Talons"
            claw.description = "Gain +%i damage for 10 turns with each attack" % self.bloodlust_bonus
            dive = LeapAttack(damage=self.minion_damage, range=self.minion_range)
            dive.cool_down = 3
            dive.name = "Dive"
            unit.spells = [dive, claw]
            unit.resists[Tags.Dark] = 75
            unit.tags = [Tags.Nature, Tags.Demon]
            self.spell.summon(unit, target=self.owner, radius=5, sort_dist=False)

            if self.feeding_frenzy:
                for unit in [unit for unit in self.owner.level.get_units_in_los(self.owner) if not are_hostile(self.spell.caster, unit)]:
                    existing = unit.get_buff(BloodrageBuff)
                    if existing and random.random() >= self.owner.cur_hp/self.owner.max_hp:
                        unit.apply_buff(BloodrageBuff(existing.bonus), 10)

    def on_death(self, evt):
        targets = [unit for unit in self.owner.level.get_units_in_los(self.owner) if are_hostile(self.spell.caster, unit)]
        if targets:
            random.choice(targets).apply_buff(SightOfBloodBuff(self.spell), self.turns_left)

class SummonedStormDrakeBreath(StormBreath):
    def __init__(self, spell):
        self.damage = spell.get_stat("breath_damage")
        self.range = spell.get_stat("minion_range")
        self.strikechance = spell.get_stat("strikechance")/100
        self.surge = spell.get_stat("surge")
        StormBreath.__init__(self)
    def per_square_effect(self, x, y):
        if self.surge:
            existing = self.caster.level.tiles[x][y].cloud
            if isinstance(existing, StormCloud):
                self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Lightning, self)
                if self.strikechance > 0.5 and random.random() < 0.5:
                    self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Lightning, self)
        cloud = StormCloud(self.caster, self.damage)
        cloud.strikechance = self.strikechance
        self.caster.level.add_obj(cloud, x, y)

class IcePhoenixBuff(Buff):
	
    def __init__(self, spell):
        self.damage = spell.get_stat("minion_damage", base=25)
        self.radius = spell.get_stat("radius")
        Buff.__init__(self)

    def on_init(self):
        self.color = Tags.Ice.color
        self.owner_triggers[EventOnDeath] = self.on_death
        self.name = "Phoenix Freeze"

    def get_tooltip(self):
        return "On death, deal %i ice damage to enemies and applies 2 SH to allies in a %i radius." % (self.damage, self.radius)

    def on_death(self, evt):
        for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius):
            unit = self.owner.level.get_unit_at(*p)
            if unit and not are_hostile(unit, self.owner):
                unit.add_shields(2)
            else:
                self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Ice, self)

class IcePhoenixFreeze(Upgrade):
    def on_init(self):
        self.name = "Freeze Chance"
        self.level = 4
        self.description = "All of the ice phoenix's [ice] damage will [freeze] enemies for [3_turns:duration]."
        self.global_triggers[EventOnDamaged] = self.on_damaged
    def on_damaged(self, evt):
        if not are_hostile(evt.unit, self.owner):
            return
        if evt.damage_type != Tags.Ice:
            return
        if evt.source.owner and evt.source.owner.source is self.prereq:
            evt.unit.apply_buff(FrozenBuff(), 3)

class IcePhoenixIcyJudgment(Upgrade):
    def on_init(self):
        self.name = "Icy Judgment"
        self.level = 5
        self.description = "Half of all of the ice phoenix's [ice] damage will be redealt as [holy] damage."
        self.global_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def qualifies(self, target, source, damage_type):
        if not are_hostile(target, self.owner):
            return False
        if damage_type != Tags.Ice:
            return False
        if source.owner and source.owner.source is self.prereq:
            return True
        return False
    
    def on_pre_damaged(self, evt):
        if self.qualifies(evt.unit, evt.source, evt.damage_type):
            evt.unit.deal_damage(evt.damage//2, Tags.Holy, evt.source)
    
    # For my No More Scams mod
    def can_redeal(self, target, source, damage_type):
        return self.qualifies(target, source, damage_type) and target.resists[Tags.Holy] < 100

class SlimeFormBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)

    def on_init(self):
        self.name = "Slime Form"
        self.transform_asset_name = "slime_form"
        self.stack_type = STACK_TYPE_TRANSFORM
        self.resists[Tags.Poison] = 100
        self.resists[Tags.Physical] = 50
        self.color = Tags.Slime.color
        self.natural = self.spell.get_stat("natural_slimes")
        if self.spell.get_stat("fire_slimes"):
            self.slime_type = RedSlime
        elif self.spell.get_stat("ice_slimes"):
            self.slime_type = IceSlime
        elif self.spell.get_stat("void_slimes"):
            self.slime_type = VoidSlime
        else:
            self.slime_type = GreenSlime
        self.minion_health = self.spell.get_stat('minion_health')
        self.minion_damage = self.spell.get_stat('minion_damage')

    def make_slime(self):

        unit = self.slime_type()
        unit.max_hp = self.minion_health + (10 if self.natural else 0)
        if self.natural:
            unit.tags.append(Tags.Nature)

        unit.spells[0].damage = self.minion_damage + (7 if self.natural else 0)
        if not unit.spells[0].melee:
            unit.spells[0].range = self.spell.get_stat('minion_range', base=unit.spells[0].range)

        if self.spell.get_stat("advanced"):
            spell = unit.spells[0]
            if self.slime_type is RedSlime:
                spell.radius += 1
            elif self.slime_type is IceSlime:
                spell.buff = FrozenBuff
                spell.buff_duration = 1
                spell.description = "Freezes for 1 turn."
            elif self.slime_type is VoidSlime:
                spell.range += 3
            else:
                spell.buff = Acidified
                spell.description = "Acidifies the target."

        # Make sure bonuses propogate
        unit.buffs[0].spawner = self.make_slime
        unit.source = self.spell
        return unit

    def on_advance(self):
        self.spell.summon(self.make_slime(), radius=5)

class SlimeFormAdvancedSlimes(Upgrade):

    def on_init(self):
        self.name = "Advanced Slimes"
        self.level = 5
        self.description = "Green slimes will acidify targets with their melee attacks, reducing [poison] resistance by 100.\nThe attacks of red slimes gain [1_radius:radius].\nThe attacks of ice slimes will [freeze] targets for [1_turn:duration].\nThe attacks of void slimes gain [3_range:minion_range]."
        self.spell_bonuses[SlimeformSpell]["advanced"] = 1
    
    # For my No More Scams mod
    # Make sure it works for slimes summoned by Slime Form + Boon shrine
    def can_redeal(self, target, source, damage_type):
        if source.owner and isinstance(source.owner.source, SlimeformSpell):
            return hasattr(source, "buff") and source.buff is Acidified and damage_type == Tags.Poison and target.resists[Tags.Poison] < 200 and not target.has_buff(Acidified)
        return False

class UnholyAllianceHolyBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.global_bonuses["damage"] = 7

class UnholyAllianceUnholyBuff(Buff):
    def on_init(self):
        self.buff_type = BUFF_TYPE_PASSIVE
        self.global_bonuses["damage"] = 7
        self.resists[Tags.Holy] = 100

class WhiteFlameDebuff(Buff):
    def on_init(self):
        self.name = "White Flame"
        self.color = Tags.Fire.color
        self.buff_type = BUFF_TYPE_CURSE
        self.resists[Tags.Fire] = -100

class PureGraceBuff(Buff):
    def on_init(self):
        self.show_effect = False
    def on_applied(self, owner):
        if self.owner.team == TEAM_PLAYER:
            self.name = "Pure Grace"
        else:
            self.name = "Pure Penance"
            self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Holy.color
        self.description = "All physical damage to the wizard's enemies will be redealt as half holy and half arcane."

class FrostbiteBuff(Buff):

    def __init__(self, upgrade):
        self.upgrade = upgrade
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Frostbite"
        self.asset = ["UnderusedOptions", "Statuses", "frostbite"]
        self.color = Tags.Dark.color
        self.buff_type = BUFF_TYPE_CURSE
        self.damage = self.upgrade.get_stat("damage")
    
    def on_pre_advance(self):
        freeze = self.owner.get_buff(FrozenBuff)
        if freeze:
            self.turns_left = max(self.turns_left, freeze.turns_left)

    def on_advance(self):
        self.owner.deal_damage(self.damage, Tags.Dark, self.upgrade)

class DivineRiposteBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        self.damage = spell.get_stat("damage", base=18)
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Divine Riposte"
        self.color = Tags.Holy.color
        self.owner_triggers[EventOnDamaged] = self.on_damaged
    
    def on_damaged(self, evt):
        if not evt.source.owner or not are_hostile(evt.source.owner, self.owner):
            return
        self.owner.level.queue_spell(self.riposte(evt.source.owner))
    
    def riposte(self, target):
        for point in Bolt(self.owner.level, self.owner, target, find_clear=False):
            self.owner.level.show_effect(point.x, point.y, Tags.Holy, minor=True)
            yield
        target.deal_damage(self.damage, Tags.Holy, self.spell)

class ConjureMemoriesBuff(Buff):

    def __init__(self, spell):
        self.num_summons = spell.get_stat("num_summons")
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Memorize Allies"
        self.color = Tags.Conjuration.color
        self.allies = []
        self.global_triggers[EventOnUnitAdded] = self.on_unit_added

    def on_unit_added(self, evt):
        if are_hostile(self.owner, evt.unit) or evt.unit.is_player_controlled or evt.unit in self.allies:
            return
        self.owner.level.queue_spell(self.memorize_unit(evt.unit))

    def memorize_unit(self, unit):
        self.allies.append(unit)
        unit.memorized_max_hp = unit.max_hp
        unit.memorized_shields = unit.shields
        unit.memorized_turns_to_death = unit.turns_to_death
        yield

    def on_advance(self):
        if all(unit.team == TEAM_PLAYER for unit in self.owner.level.units):
            self.allies = []

    def on_unapplied(self):
        random.shuffle(self.allies)
        count = 0
        for unit in [unit for unit in self.allies if not unit.is_alive()]:
            if count >= self.num_summons:
                return
            target = self.owner.level.get_summon_point(self.owner.x, self.owner.y, sort_dist=False, flying=unit.flying)
            if not target:
                continue
            if hasattr(unit, "unique") and [u for u in self.owner.level.units if u.name == unit.name]:
                continue
            count += 1
            unit.max_hp = unit.memorized_max_hp
            unit.cur_hp = unit.max_hp
            unit.shields = unit.memorized_shields
            unit.turns_to_death = unit.memorized_turns_to_death
            for buff in list(unit.buffs):
                if buff.buff_type != BUFF_TYPE_PASSIVE:
                    unit.buffs.remove(buff)
            unit.killed = False
            self.owner.level.show_effect(target.x, target.y, Tags.Translocation)
            self.owner.level.add_obj(unit, target.x, target.y, trigger_summon_event=False)

class RecentMemory(Upgrade):
    def on_init(self):
        self.name = "Recent Memory"
        self.level = 3
        self.description = "Mystic Memory will now prioritize the spell you cast last turn, if that spell has no charges remaining."
        self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
        self.recent_spell = None
    def on_spell_cast(self, evt):
        if evt.spell in self.owner.spells and evt.spell is not self.prereq:
            self.recent_spell = evt.spell

class MinionBuffAura(Buff):

    def __init__(self, buff_class, qualifies, name, minion_desc):
        Buff.__init__(self)
        self.buff_class = buff_class
        self.qualifies = qualifies
        self.name = name
        example = self.buff_class()
        self.description = "All %s you summon gain %s for a duration equal to this buff's remaining duration." % (minion_desc, example.name)
        self.color = example.color
        self.global_triggers[EventOnUnitAdded] = self.on_unit_added
        self.buff_dict = defaultdict(lambda: None)

    def modify_unit(self, unit, duration):

        if are_hostile(self.owner, unit) or (unit is self.owner):
            return
        if not self.qualifies(unit):
            return
        
        if not unit.is_alive() and unit in self.buff_dict.keys():
            self.buff_dict.pop(unit)
            return

        if unit not in self.buff_dict.keys() or not self.buff_dict[unit] or not self.buff_dict[unit].applied:
            buff = self.buff_class()
            unit.apply_buff(buff, duration)
            self.buff_dict[unit] = buff

    def on_unit_added(self, evt):
        self.modify_unit(evt.unit, self.turns_left - 1)
    
    def on_advance(self):
        for unit in list(self.buff_dict.keys()):
            if not unit.is_alive():
                self.buff_dict.pop(unit)
        for unit in list(self.owner.level.units):
            self.modify_unit(unit, self.turns_left)

class InfernoEngineBuff(DamageAuraBuff):

    def __init__(self, radius):
        DamageAuraBuff.__init__(self, damage=2, damage_type=Tags.Fire, radius=radius)
        self.name = "Inferno Engine"
        self.stack_type = STACK_REPLACE
    
    def on_attempt_apply(self, owner):
        existing = owner.get_buff(InfernoEngineBuff)
        if existing:
            return existing.radius <= self.radius
        return True

class InfernoEngineAura(MinionBuffAura):

    def __init__(self, radius):
        self.radius = radius
        MinionBuffAura.__init__(self, lambda: InfernoEngineBuff(self.radius), lambda unit: Tags.Metallic in unit.tags, "Engine Aura", "metallic minions")
        self.stack_type = STACK_REPLACE
    
    def on_attempt_apply(self, owner):
        existing = owner.get_buff(InfernoEngineAura)
        if existing:
            return existing.radius <= self.radius
        return True

class IceWallForcefulConstruction(Upgrade):
    def on_init(self):
        self.name = "Forceful Construction"
        self.level = 4
        self.spell_bonuses[IceWall]["requires_los"] = -1
        self.spell_bonuses[IceWall]["forceful"] = 1
        self.description = "Wall of Ice no longer requires line of sight to cast.\nWall and chasm tiles in the affected area are converted to floor tiles before summoning the ice elementals.\nUnits in the affected area take [22_ice:ice] damage and are [frozen] for [3_turns:duration], which benefit from stat bonuses. If a unit is killed then an ice elemental is summoned in its tile."

class InfernoCannonBlast(SimpleRangedAttack):

    def __init__(self, damage, range, radius, heal, demo):
        SimpleRangedAttack.__init__(self, name="Fire Blast", damage=damage, damage_type=Tags.Fire, range=range, radius=radius)
        self.description = "Must be at full HP to fire.\nLoses half max HP on firing."
        self.heal = heal
        if heal:
            self.description += "\nHeals allies."
        self.demo = demo
        if demo:
            self.description += "\nDestroys walls."
    
    def cast(self, x, y):
        self.caster.cur_hp -= self.caster.max_hp//2
        for point in Bolt(self.caster.level, self.caster, Point(x, y), find_clear=False):
            self.caster.level.show_effect(point.x, point.y, self.damage_type, minor=True)
        for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius'), ignore_walls=self.demo):
            for point in stage:
                self.hit(point.x, point.y)
            yield

    def hit(self, x, y):
        damage = self.get_stat("damage")
        unit = self.caster.level.get_unit_at(x, y)
        if self.heal and unit and not are_hostile(unit, self.caster):
            if not unit.is_player_controlled and unit.name != "Inferno Cannon":
                unit.deal_damage(-damage, Tags.Heal, self)
            self.caster.level.show_effect(x, y, self.damage_type)
        else:
            self.caster.level.deal_damage(x, y, damage, self.damage_type, self)
        if self.demo and self.caster.level.tiles[x][y].is_wall():
            self.caster.level.make_floor(x, y)

class InfernoCannonExplosion(DeathExplosion):

    def __init__(self, damage, radius, heal, demo):
        DeathExplosion.__init__(self, damage, radius, Tags.Fire)
        self.description += "."
        self.heal = heal
        if heal:
            self.description += " Allies are healed instead."
        self.demo = demo
        if demo:
            self.description += " Walls are destroyed."

    def explode(self, level, x, y):
        for stage in Burst(self.owner.level, Point(self.owner.x, self.owner.y), self.radius, ignore_walls=self.demo):
            for point in stage:
                unit = self.owner.level.get_unit_at(point.x, point.y)
                if self.heal and unit and not are_hostile(unit, self.owner):
                    if not unit.is_player_controlled and unit.name != "Inferno Cannon":
                        unit.deal_damage(-self.damage, Tags.Heal, self)
                    self.owner.level.show_effect(point.x, point.y, self.damage_type)
                else:
                    self.owner.level.deal_damage(point.x, point.y, self.damage, self.damage_type, self)
                if self.demo and self.owner.level.tiles[point.x][point.y].is_wall():
                    self.owner.level.make_floor(point.x, point.y)
            yield

class SiegeGolemTeleport(Spell):

    def __init__(self, range):
        Spell.__init__(self)
        self.range = range
        self.name = "Teleport"
        self.description = "Teleport next to an inferno cannon."
        self.requires_los = False
    
    def get_dest_points(self, x, y):
        return list(self.caster.level.get_adjacent_points(Point(x, y), check_unit=True))

    def can_cast(self, x, y):
        return Spell.can_cast(self, x, y) and bool(self.get_dest_points(x, y))

    def get_ai_target(self):
        potentials = [u for u in self.caster.level.units if not are_hostile(u, self.caster) and u.name == "Inferno Cannon"]
        # Filter LOS, range
        potentials = [u for u in potentials if self.can_cast(u.x, u.y)]
        if not potentials:
            return None
        return random.choice(potentials)

    def cast_instant(self, x, y):
        points = self.get_dest_points(x, y)
        if not points:
            return
        target = random.choice(points)
        self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Translocation)
        self.caster.level.act_move(self.caster, target.x, target.y, teleport=True)

def modify_class(cls):

    if cls is DeathBolt:

        def on_init(self):
            self.name = "Death Bolt"
            self.tags = [Tags.Dark, Tags.Sorcery, Tags.Conjuration]
            self.level = 1
            self.damage = 9
            self.element = Tags.Dark
            self.range = 8
            self.max_charges = 18

            self.upgrades['damage'] = (12, 1)
            self.upgrades['max_charges'] = (10, 2)
            self.upgrades['minion_damage'] = (9, 3)

            self.upgrades['wither'] = (1, 5, "Withering", "Death Bolt also deals [physical] damage to non-living units, and reduces their max HP by an amount equal to damage dealt.")
            self.upgrades['soulbattery'] = (1, 7, "Soul Battery", "Deathbolt permenantly gains 1 damage whenever it slays a living target.")

            self.can_target_empty = False
            self.minion_damage = 5

        def cast_instant(self, x, y):		
            unit = self.caster.level.get_unit_at(x, y)
            if unit and Tags.Living in unit.tags:
                # Queue the skeleton raise as the first spell to happen after the damage so that it will pre-empt stuff like ghostfire
                self.caster.level.queue_spell(self.try_raise(self.caster, unit))
            damage = self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Dark, self)
            if unit and self.get_stat('wither') and Tags.Living not in unit.tags:
                damage += unit.deal_damage(self.get_stat("damage"), Tags.Physical, self)
                unit.max_hp -= damage
                unit.max_hp = max(unit.max_hp, 1)
            if unit and not unit.is_alive() and Tags.Living in unit.tags and self.get_stat('soulbattery'):
                self.damage += 1

    if cls is FireballSpell:

        def on_init(self):
            self.radius = 2
            self.damage = 9
            self.name = "Fireball"
            self.max_charges = 18
            self.range = 8
            self.element = Tags.Fire

            self.damage_type = Tags.Fire

            self.whiteflame_bonus = 0
            self.blueflame_bonus = 0

            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 1

            self.upgrades['radius'] = (1, 3)
            self.upgrades['damage'] = (8, 2)
            self.upgrades['max_charges'] = (8, 2)
            self.upgrades['range'] = (3, 1)

            self.upgrades['chaos'] = (1, 3, "Chaos Ball", "Fireball redeals [fire] damage that is resisted or blocked by [SH:shields] as a split between [lightning] and [physical] damage.", "damage type")
            self.upgrades['energy'] = (1, 4, "Energy Ball", "Fireball redeals [fire] damage that is resisted or blocked by [SH:shields] as a split between [arcane] and [holy] damage.", "damage type")
            self.upgrades['ash'] = (1, 5, "Ash Ball", "Fireball redeals [fire] damage that is resisted or blocked by [SH:shields] as a split between [dark] and [poison] damage.\nFireball blinds for 1 turn.", "damage type")

        def cast(self, x, y):
            target = Point(x, y)
            for stage in Burst(self.caster.level, target, self.get_stat('radius')):
                for point in stage:
                    damage = self.get_stat('damage')
                    unit = self.caster.level.get_unit_at(point.x, point.y)
                    if unit:
                        if unit.shields > 0:
                            resisted = damage
                        else:
                            resisted = math.floor(damage*unit.resists[Tags.Fire]/100)
                    self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)

                    redeals = []
                    if self.get_stat("chaos"):
                        redeals = [Tags.Lightning, Tags.Physical]
                    elif self.get_stat("energy"):
                        redeals = [Tags.Arcane, Tags.Holy]
                    elif self.get_stat("ash"):
                        redeals = [Tags.Dark, Tags.Poison]
                    if not redeals or not unit:
                        continue
                    
                    if are_hostile(unit, self.caster):
                        for dtype in redeals:
                            unit.deal_damage(resisted//2, dtype, self)
                    if self.get_stat('ash'):
                        unit.apply_buff(BlindBuff(), 1)
                yield
    
    if cls is PoisonSting:

        def on_init(self):
            self.name = "Poison Sting"
            self.tags = [Tags.Sorcery, Tags.Nature]
            self.max_charges = 20
            self.duration = 30
            self.damage = 9
            self.range = 12
            self.level = 1

            self.upgrades['range'] = (4, 1)
            self.upgrades['max_charges'] = (10, 3)
            self.upgrades['duration'] = (60, 2)
            self.upgrades['antigen'] = (1, 2, "Acidity", "Damaged targets lose all poison resist")
            self.upgrades["torment"] = (1, 5, "Torment", "Deal 1 extra damage per 10 turns of [poison] on the target, and 1 extra damage per turn of every other debuff on the target.")

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)

            damage = self.get_stat("damage")
            if unit and self.get_stat("torment"):
                for debuff in [buff for buff in unit.buffs if buff.buff_type == BUFF_TYPE_CURSE]:
                    if isinstance(debuff, Poison):
                        damage += math.ceil(debuff.turns_left/10)
                    else:
                        damage += debuff.turns_left
            damage = self.caster.level.deal_damage(x, y, damage, Tags.Physical, self)

            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y), find_clear=True)[1:-1]:
                self.caster.level.show_effect(p.x, p.y, Tags.Poison, minor=True)

            if unit:
                if damage and self.get_stat('antigen'):
                    unit.apply_buff(Acidified())
                unit.apply_buff(Poison(), self.get_stat('duration'))

    if cls is SummonWolfSpell:

        def on_init(self):
            self.max_charges = 12
            self.name = "Wolf"
            self.minion_health = 11
            self.minion_damage = 5
            self.upgrades['leap_range'] = (4, 3, "Pounce", "Summoned wolves gain a leap attack")
            self.upgrades['minion_damage'] = 4
            self.upgrades['minion_health'] = (12, 3)

            self.upgrades['blood_hound'] = (1, 3, "Blood Hound", "Summon blood hounds instead of wolves.", "hound")
            self.upgrades['ice_hound'] = (1, 3, "Ice Hound", "Summon ice hounds instead of wolves.", "hound")
            self.upgrades['clay_hound'] = (1, 6, "Clay Hound", "Summon clay hounds instead of wolves.", "hound")
            self.upgrades['wolf_pack'] = (1, 7, "Wolf Pack", "Each cast of wolf consumes 2 charges and summons 4 wolves.\nThis counts as casting the spell twice.")


            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 1

            self.must_target_walkable = True
            self.must_target_empty = True

        def make_wolf(self):
            wolf = Unit()
            wolf.name = "Wolf"
            wolf.max_hp = self.get_stat('minion_health')
            wolf.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))
            wolf.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('leap_range'):
                wolf.spells.append(LeapAttack(damage=self.get_stat('minion_damage'), damage_type=Tags.Physical, range=self.get_stat('leap_range')))

            if self.get_stat('blood_hound'):
                wolf.name = "Blood Hound"
                wolf.asset_name = "blood_wolf"

                wolf.spells[0].onhit = bloodrage(2)
                wolf.spells[0].name = "Frenzy Bite"
                wolf.spells[0].description = "Gain +2 damage for 10 turns with each attack"
                
                wolf.tags = [Tags.Demon, Tags.Nature]
                wolf.resists[Tags.Dark] = 75

            elif self.get_stat('ice_hound'):
                for s in wolf.spells:
                    s.damage_type = Tags.Ice
                wolf.resists[Tags.Ice] = 100
                wolf.resists[Tags.Fire] = -50
                wolf.resists[Tags.Dark] = 50
                wolf.name = "Ice Hound"
                wolf.tags = [Tags.Demon, Tags.Ice, Tags.Nature]
                wolf.buffs.append(Thorns(4, Tags.Ice))

            elif self.get_stat('clay_hound'):
                wolf.name = "Clay Hound"
                wolf.asset_name = "earth_hound"

                wolf.resists[Tags.Physical] = 50
                wolf.resists[Tags.Fire] = 50
                wolf.resists[Tags.Lightning] = 50
                wolf.buffs.append(RegenBuff(3))
                
            return wolf

        def cast(self, x, y):
            num_wolves = 1
            if self.get_stat('wolf_pack'):
                num_wolves = 4
                self.cur_charges -= 1
                self.cur_charges = max(self.cur_charges, 0)
                self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)
            for i in range(num_wolves):
                wolf = self.make_wolf()
                self.summon(wolf, Point(x, y))
                yield

    if cls is AnnihilateSpell:

        def on_init(self):
            self.range = 6
            self.name = "Annihilate"
            self.max_charges = 8
            self.damage = 16
            self.tags = [Tags.Chaos, Tags.Sorcery]
            self.level = 2
            self.cascade_range = 0  # Should be cascade range
            self.arcane = 0
            self.dark = 0

            self.upgrades['cascade_range'] =  (4, 3, 'Cascade', 'Hits from Annihilate will jump to nearby targets if the main target is killed or if targeting an empty tile.\nThis ignores line of sight.')
            self.upgrades['dark'] =  (1, 1, 'Dark Annihilation', 'Annihilate deals an additional [dark] damage hit')
            self.upgrades['arcane'] =  (1, 1, 'Arcane Annihilation', 'Annihilate deals an additional [arcane] damage hit')
            self.upgrades['max_charges'] = (4, 2)

    if cls is Blazerip:

        def on_init(self):
            self.name = "Blazerip"
            self.tags = [Tags.Arcane, Tags.Fire, Tags.Sorcery]
            self.level = 2
            self.max_charges = 8
            self.damage = 12
            self.range = 6
            self.requires_los = False
            self.radius = 3

            self.upgrades['damage'] = (5, 2)
            self.upgrades['radius'] = (2, 2)
            self.upgrades["fractal"] = (1, 6, "Fractal Rip", "Each hit of Blazerip now has a 10% chance of triggering another Blazerip on that tile. This can still happen even if an empty tile is hit.\nEach rip can trigger at most one additional rip.")

        def cast(self, x, y):
            damage = self.get_stat("damage")
            chance = 0.1 if self.get_stat("fractal") else 0
            points = self.get_impacted_tiles(x, y)
            branched = False
            for p in points:
                self.owner.level.deal_damage(p.x, p.y, damage, Tags.Arcane, self)
                if self.owner.level.tiles[p.x][p.y].is_wall():
                    self.owner.level.make_floor(p.x, p.y)
                if not branched and random.random() < chance:
                    branched = True
                    self.caster.level.queue_spell(self.cast(p.x, p.y))
                yield
            for p in reversed(points):
                self.owner.level.deal_damage(p.x, p.y, damage, Tags.Fire, self)
                if not branched and random.random() < chance:
                    branched = True
                    self.caster.level.queue_spell(self.cast(p.x, p.y))
                yield

    if cls is BloodlustSpell:

        def on_init(self):
            self.name = "Boiling Blood"
            self.max_charges = 9
            self.duration = 7
            self.extra_damage = 6
            self.range = 0

            self.tags = [Tags.Nature, Tags.Enchantment, Tags.Fire]
            self.level = 2

            self.upgrades['extra_damage'] = (6, 3)
            self.upgrades['duration'] = (7, 2)
            self.upgrades['holy_fury'] = (1, 3, "Holy Fury", "Boiling Blood also impacts holy abilities")
            self.upgrades['dark_fury'] = (1, 3, "Dark Fury", "Boiling Blood also impacts dark abilities")
            self.upgrades["retroactive"] = (1, 4, "Retroactive", "You now gain Bloodlust Aura when you cast this spell, during which all minions you summon will automatically gain Boiling Blood for the remaining duration.")

        def cast(self, x, y):

            def buff_func():
                buff = BloodlustBuff(self)
                buff.extra_damage = extra_damage
                return buff

            duration = self.get_stat("duration")
            extra_damage = self.get_stat("extra_damage")
            
            if self.get_stat("retroactive"):
                buff = MinionBuffAura(buff_func, lambda unit: True, "Bloodlust Aura", "minions")
                buff.stack_type = STACK_INTENSITY
                self.caster.apply_buff(buff, duration)
                return
            
            for unit in self.caster.level.units:
                if not self.caster.level.are_hostile(self.caster, unit) and unit is not self.caster:
                    buff = buff_func()
                    unit.apply_buff(buff, duration)
            
            yield

    if cls is DispersalSpell:

        def on_init(self):
            self.range = 6
            self.max_charges = 15
            self.name = "Disperse"
            self.tags = [Tags.Arcane, Tags.Sorcery, Tags.Translocation]
            self.can_target_self = False
            self.radius = 3
            self.level = 2

            self.upgrades['radius'] = (2, 2)
            self.upgrades['max_charges'] = (10, 2)
            self.upgrades["shadow"] = (1, 4, "Quantum Shadow", "Summon a void ghost in the former location of each unit teleported away.\nThese void ghosts cannot be affected by this spell.")

        def cast(self, x, y):
            shadow = self.get_stat("shadow")
            for p in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat('radius')):
                target = self.caster.level.get_unit_at(p.x, p.y)

                if target is self.caster or target.source is self:
                    continue
                
                possible_points = []
                for i in range(len(self.caster.level.tiles)):
                    for j in range(len(self.caster.level.tiles[i])):
                        if self.caster.level.can_stand(i, j, target):
                            possible_points.append(Point(i, j))

                if not possible_points:
                    return

                old = Point(target.x, target.y)
                target_point = random.choice(possible_points)

                self.caster.level.show_effect(target.x, target.y, Tags.Translocation)
                yield 
                self.caster.level.act_move(target, target_point.x, target_point.y, teleport=True)
                yield
                self.caster.level.show_effect(target.x, target.y, Tags.Translocation)
                if shadow and not self.caster.level.get_unit_at(old.x, old.y):
                    ghost = GhostVoid()
                    apply_minion_bonuses(self, ghost)
                    self.summon(ghost, target=old)

    if cls is FireEyeBuff:

        def on_shoot(self, target):
            if not self.spell.get_stat("blast"):
                return
            points = list(self.owner.level.get_adjacent_points(target, filter_walkable=False))
            for point in points:
                unit = self.owner.level.get_unit_at(point.x, point.y)
                if not unit or not are_hostile(unit, self.owner):
                    self.owner.level.show_effect(point.x, point.y, self.element)
                else:
                    unit.deal_damage(self.damage, self.element, self.spell)

    if cls is EyeOfFireSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Eye of Fire"
            self.damage = 15
            self.element = Tags.Fire
            self.duration = 30
            self.shot_cooldown = 3
            
            self.upgrades['shot_cooldown'] = (-1, 1)
            self.upgrades['duration'] = 15
            self.upgrades['damage'] = (7, 2)
            self.upgrades["blast"] = (1, 3, "Eye of Blasting", "On hit, Eye of Fire also deals damage to all enemies adjacent to the target.")

            self.tags = [Tags.Fire, Tags.Enchantment, Tags.Eye]
            self.level = 2

    if cls is IceEyeBuff:

        def on_shoot(self, target):
            if not self.spell.get_stat("freeze"):
                return
            target_unit = self.owner.level.get_unit_at(target.x, target.y)
            if not target_unit:
                return
            target_unit.apply_buff(FrozenBuff(), 1)

    if cls is EyeOfIceSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Eye of Ice"
            self.damage = 15
            self.element = Tags.Ice
            self.duration = 30
            self.shot_cooldown = 3

            self.upgrades['shot_cooldown'] = (-1, 1)
            self.upgrades['duration'] = 15
            self.upgrades['damage'] = (7, 2)
            self.upgrades["freeze"] = (1, 3, "Eye of Freezing", "On hit, the target is [frozen] for [1_turn:duration].")

            self.tags = [Tags.Ice, Tags.Enchantment, Tags.Eye]
            self.level = 2

    if cls is LightningEyeBuff:

        def arc(self, origin, target):
            for point in Bolt(self.owner.level, origin, target):
                self.owner.level.show_effect(point.x, point.y, self.element, minor=True)
                yield
            self.owner.level.deal_damage(target.x, target.y, self.damage, self.element, self.spell)

        def on_shoot(self, target):
            if not self.spell.get_stat("arc"):
                return
            target_unit = self.owner.level.get_unit_at(target.x, target.y)
            new_targets = [unit for unit in self.owner.level.get_units_in_los(target) if are_hostile(self.owner, unit) and unit is not target_unit]
            if not new_targets:
                return
            self.owner.level.queue_spell(arc(self, target, random.choice(new_targets)))

    if cls is EyeOfLightningSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Eye of Lightning"
            self.damage = 15
            self.element = Tags.Lightning
            self.duration = 30
            self.shot_cooldown = 3

            self.upgrades['shot_cooldown'] = (-1, 1)
            self.upgrades['duration'] = 15
            self.upgrades['damage'] = (7, 2)
            self.upgrades["arc"] = (1, 3, "Eye of Arcing", "On hit, Eye of Lightning also deals damage to a random enemy in line of sight of the target.")

            self.tags = [Tags.Lightning, Tags.Enchantment, Tags.Eye]
            self.level = 2

    if cls is RageEyeBuff:

        def on_shoot(self, target):
            unit = self.owner.level.get_unit_at(target.x, target.y)
            if unit:
                if self.spell.get_stat('lycanthropy') and (Tags.Living in unit.tags or Tags.Nature in unit.tags or Tags.Demon in unit.tags) and unit.cur_hp <= 25:
                    unit.kill(trigger_death_event=False)
                    newunit = Werewolf()
                    apply_minion_bonuses(self.spell, newunit)
                    self.spell.summon(newunit, target=unit)
                else:
                    unit.apply_buff(BerserkBuff(), self.berserk_duration)

    if cls is EyeOfRageSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Eye of Rage"
            self.duration = 20
            self.shot_cooldown = 3

            self.berserk_duration = 2

            self.upgrades['shot_cooldown'] = (-1, 1)
            self.upgrades['duration'] = 15
            self.upgrades['berserk_duration'] = 2
            self.upgrades['lycanthropy'] = (1, 4, "Lycanthropy", "When Eye of Rage targets a [living], [nature], or [demon] unit with 25 or less HP, that unit is transformed into a friendly Werewolf.")

            self.tags = [Tags.Nature, Tags.Enchantment, Tags.Eye]
            self.level = 2

    if cls is Flameblast:

        def on_init(self):
            self.name = "Fan of Flames"
            self.tags = [Tags.Sorcery, Tags.Fire]
            self.max_charges = 18
            self.damage = 9
            self.element = Tags.Fire
            self.range = 5
            self.radius = 5
            self.angle = math.pi / 6.0
            self.level = 2
            self.can_target_self = 0
            self.requires_los = False
            self.melt_walls = 0
            self.max_channel = 10

            self.upgrades['damage'] = (7, 3)
            self.upgrades['range'] = (2, 3)
            self.upgrades['max_charges'] = (10, 3)
            self.upgrades["can_target_self"] = (1, 4, "Wheel of Flames", "You can now intentionally target yourself with Fan of Flames, dealing damage in a radius.")
            #self.upgrades['channel'] = (1, 2, "Channeling", "Fan of Flames can be channeled for up to 10 turns")
            self.channel = 1

        def can_cast(self, x, y):
            if x == self.caster.x and y == self.caster.y:
                return self.get_stat("can_target_self")
            return Spell.can_cast(self, x, y)

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage to all units in a cone.\n"
                    "If you are somehow moved into the target tile while channeling, instead deal damage a [{radius}_tile:radius] radius.\n"
                    "This spell can be channeled for up to [{max_channel}_turns:duration].  The effect is repeated each turn the spell is channeled.").format(**self.fmt_dict())
    
        def aoe(self, x, y):
            radius = self.get_stat("radius") if x == self.caster.x and y == self.caster.y else self.get_stat("range")
            target = Point(x, y)
            return Burst(self.caster.level, 
                        Point(self.caster.x, self.caster.y), 
                        radius, 
                        burst_cone_params=BurstConeParams(target, self.angle), 
                        ignore_walls=self.get_stat('melt_walls'))

    if cls is Freeze:

        def on_init(self):
            self.tags = [Tags.Enchantment, Tags.Ice]
            self.level = 2
            self.name = "Freeze"
        
            self.duration = 5
            
            self.max_charges = 20

            self.range = 8

            self.upgrades['duration'] = (4, 3)
            self.upgrades["absolute_zero"] = (1, 6, "Absolute Zero", "The target now permanently loses [100_ice:ice] resistance before being frozen.")
            self.upgrades["permafrost"] = (1, 5, "Permafrost", "When targeting an already frozen unit, increase the duration of freeze on it by one third of this spell's duration if the result is greater than this spell's duration.\nThen deal [ice] damage equal to twice the target's freeze duration.")

        def cast_instant(self, x, y):
            duration = self.get_stat("duration")
            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return
            if self.get_stat("absolute_zero"):
                target.apply_buff(AbsoluteZeroBuff())
            existing = target.get_buff(FrozenBuff)
            if existing:
                existing.turns_left = max(duration, existing.turns_left + duration//3)
                target.deal_damage(existing.turns_left*2, Tags.Ice, self)
            else:
                target.apply_buff(FrozenBuff(), duration)

    if cls is HealMinionsSpell:

        def on_init(self):
            self.name = "Healing Light"
            self.heal = 25

            self.max_charges = 10
            self.range = 0

            self.upgrades['heal'] = (20, 1)
            self.upgrades['max_charges'] = (8, 2)
            self.upgrades['shields'] = (1, 2, "Shielding Light", "Allies in line of sight gain [1_SH:shields]")
            self.upgrades["cleanse"] = (1, 3, "Cleansing Light", "Healing Light will now remove all debuffs from affected allies before healing them.")

            self.tags = [Tags.Holy, Tags.Sorcery]
            self.level = 2

        def cast(self, x, y):

            heal = self.get_stat("heal")
            shields = self.get_stat('shields')
            cleanse = self.get_stat("cleanse")

            for unit in self.caster.level.get_units_in_los(self.caster):
                if not self.caster.level.are_hostile(self.caster, unit) and unit != self.caster:

                    # Dont heal the player if a gold drake is casting
                    if unit.is_player_controlled:
                        continue

                    if cleanse:
                        for buff in unit.buffs:
                            if buff.buff_type == BUFF_TYPE_CURSE:
                                unit.remove_buff(buff)

                    if unit.cur_hp < unit.max_hp:
                        unit.deal_damage(-heal, Tags.Heal, self)
                    
                    if shields:
                        unit.add_shields(1)
                    yield

    if cls is HolyBlast:

        def on_init(self):

            self.name = "Heavenly Blast"
            self.range = 7
            self.radius = 1
            self.damage = 7

            self.damage_type = Tags.Holy
            
            self.max_charges = 14

            self.level = 2

            self.tags = [Tags.Holy, Tags.Sorcery] 

            self.upgrades['range'] = (3, 2)
            self.upgrades['radius'] = (1, 2)
            self.upgrades['damage'] = (9, 3)
            self.upgrades['max_charges'] = (7, 2)
            self.upgrades['spiritbind'] = (1, 4, "Spirit Bind", "Enemies hit are inflicted with Spirit Binding.\nWhen an enemy with Spirit Binding dies, summon a spirit near it for [7_turns:minion_duration].\nSpirit are [holy] [undead] minions with [4_HP:minion_health] and attacks with [3_range:minion_range] that deal [2_holy:holy] damage.\nSpirit Binding is removed from all units at the beginning of your next turn.")
            self.upgrades['shield'] = (1, 3, "Shield", "Affected ally units gain [2_SH:shields], to a maximum of [5_SH:shields].")
            self.upgrades['echo_heal'] = (1, 4, "Echo Heal", "Affected ally units are re-healed for half the initial amount each turn for [5_turns:duration].")

        def cast(self, x, y):
            target = Point(x, y)
            damage = self.get_stat("damage")
            shield = self.get_stat("shield")
            echo_heal = self.get_stat("echo_heal")
            duration = self.get_stat("duration", base=5)
            bind = self.get_stat("spiritbind")

            if bind:
                self.caster.apply_buff(RemoveBuffOnPreAdvance(SpiritBindingBuff))

            def deal_damage(point):
                no_damage = True
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit and not are_hostile(unit, self.caster) and unit is not self.caster and unit is not self.statholder:
                    unit.deal_damage(-damage, Tags.Heal, self)
                    if shield:
                        if unit.shields < 4:
                            unit.add_shields(2)
                        elif unit.shields == 4:
                            unit.add_shields(1)
                    if echo_heal:
                        unit.apply_buff(RegenBuff(damage//2), duration)
                elif unit is self.caster:
                    pass
                elif unit and unit.is_player_controlled and not are_hostile(self.caster, unit):
                    pass
                else:
                    if unit and bind:
                        unit.apply_buff(SpiritBindingBuff(self))
                    self.caster.level.deal_damage(point.x, point.y, damage, Tags.Holy, self)
                    no_damage = False
                if no_damage:
                    self.caster.level.show_effect(point.x, point.y, Tags.Holy)

            points_hit = set()
            for point in Bolt(self.caster.level, self.caster, target):
                deal_damage(point)
                points_hit.add(point)
                yield
            
            stagenum = 0
            for stage in Burst(self.caster.level, target, self.get_stat('radius')):
                for point in stage:
                    if point in points_hit:
                        continue
                    deal_damage(point)

                stagenum += 1
                yield

    if cls is HallowFlesh:

        def on_init(self):
            self.name = "Hollow Flesh"
            self.tags = [Tags.Dark, Tags.Enchantment]
            self.level = 2
            self.max_charges = 9
            self.range = 6

            self.holy_vulnerability = 100
            self.fire_vulnerability = 0
            self.max_health_loss = 25

            self.upgrades['max_health_loss'] = (25, 2) 
            self.upgrades['max_charges'] = (7, 2)
            self.upgrades['fire_vulnerability'] = (50, 2, "Fire Vulnerability")
            self.upgrades["friendly"] = (1, 4, "Vigor Mortis", "When your minions are affected, their max HP are instead buffed by the same percentage.\nThey do not lose resistances or gain heal immunity, and instead gain [100_poison:poison] resistance.\nIf you have the Fire Vulnerability upgrade, they instead gain [50_ice:ice] resistance.")

        def cast(self, x, y):
            points = self.get_impacted_tiles(x, y)
            for p in points:
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit:
                    buff = mods.BugsAndScams.Bugfixes.RotBuff(self)
                    if self.get_stat("friendly") and not are_hostile(unit, self.caster):
                        buff.buff_type = BUFF_TYPE_BLESS
                    else:
                        buff.buff_type = BUFF_TYPE_CURSE
                    unit.apply_buff(buff)
                    yield

    if cls is mods.BugsAndScams.Bugfixes.RotBuff:

        def on_init(self):
            self.color = Tags.Undead.color
            self.name = "Hollow Flesh"
            self.asset = ['status', 'rot']
            self.resists[Tags.Dark] = 100
            self.frac = 1
            self.originally_living = False
            self.originally_undead = False
            self.stack_type = STACK_REPLACE

        def on_applied(self, owner):

            if self.spell.get_stat("friendly") and not are_hostile(self.owner, self.spell.caster):
                self.frac = 1 + self.spell.get_stat('max_health_loss')/100
                self.resists[Tags.Poison] = 100
                self.resists[Tags.Ice] = self.spell.get_stat('fire_vulnerability')
            else:
                self.frac = 1 - self.spell.get_stat('max_health_loss')/100
                self.resists[Tags.Holy] = -100
                self.resists[Tags.Fire] = -self.spell.get_stat('fire_vulnerability')
                self.resists[Tags.Heal] = 100

            old_max_hp = self.owner.max_hp
            self.owner.max_hp = math.floor(self.owner.max_hp*self.frac)
            self.owner.max_hp = max(self.owner.max_hp, 1)
            max_hp_diff = self.owner.max_hp - old_max_hp
            if max_hp_diff > 0:
                self.owner.cur_hp += max_hp_diff
            self.owner.cur_hp = min(self.owner.cur_hp, self.owner.max_hp)
            if Tags.Living in self.owner.tags:
                self.owner.tags.remove(Tags.Living)
                self.originally_living = True
            if Tags.Undead in self.owner.tags:
                self.originally_undead = True
            else:
                self.owner.tags.append(Tags.Undead)

    if cls is VoidMaw:

        def on_init(self):
            self.name = "Hungry Maw"

            self.max_charges = 6
            self.level = 2
            self.tags = [Tags.Arcane, Tags.Conjuration]
            self.range = 11

            self.minion_range = 7
            self.minion_damage = 9
            self.minion_health = 8
            self.minion_duration = 15
            self.shields = 1
            self.pull_strength = 1

            self.upgrades['shields'] = (5, 3)
            self.upgrades['minion_range'] = (7, 2)
            self.upgrades['minion_damage'] = (12, 5)
            self.upgrades["pull_strength"] = (2, 2)
            self.upgrades["shield_eater"] = (1, 3, "Shield Eater", "The maw gains [1_SH:shields] on kill and when attacking a shielded target, up to its original [SH:shields] amount.")

            self.must_target_empty = True

        def get_description(self):
            return ("Summons a hungry maw.\n"
                    "The maw has [{minion_health}_HP:minion_health], [{shields}_SH:shields], floats, and is stationary.\n"
                    "The maw has a [{minion_damage}_physical:physical] damage tongue attack, which pulls the target [{pull_strength}_tiles:range] towards it, with a range of [{minion_range}_tiles:minion_range].\n"
                    "The maw has a melee bite attack that deals [3_times:minion_damage] the damage of its pull attack.\n"
                    "The maw vanishes after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())
        
        def cast_instant(self, x, y):

            u = Unit()
            u.tags = [Tags.Arcane, Tags.Demon]
            u.name = "Hungry Maw"
            u.max_hp = self.get_stat('minion_health')
            u.shields = self.get_stat('shields')
            u.asset_name = 'floating_mouth'

            damage = self.get_stat("minion_damage")
            pull = PullAttack(damage=damage, range=self.get_stat('minion_range'), pull_squares=self.get_stat("pull_strength"), color=Tags.Tongue.color)
            melee = SimpleMeleeAttack(damage=damage*3)
            melee.name = "Bite"
            u.spells = [melee, pull]
            if self.get_stat("shield_eater"):
                u.buffs.append(ShieldEaterBuff(self))

            u.flying = True
            u.stationary = True

            u.turns_to_death = self.get_stat('minion_duration')

            u.resists[Tags.Arcane] = 75
            u.resists[Tags.Dark] = 50
            u.resists[Tags.Lightning] = -50

            self.summon(u, Point(x, y))

    if cls is InvokeSavagerySpell:

        def on_init(self):
            self.name = "Invoke Savagery"
            self.range = 0
            self.tags = [Tags.Nature, Tags.Sorcery]
            self.level = 2
            self.max_charges = 11
            self.damage = 14
            self.duration = 2

            self.upgrades['damage'] = (9, 2)
            self.upgrades['duration'] = (1, 2)
            self.upgrades["blood"] = (1, 3, "Blood Savagery", "Now also affects [nature] and [demon] units.")
            self.upgrades["stampede"] = (1, 5, "Stampede", "If no melee targets are available, each ally will instead try to perform a charge attack with a range of [6_tiles:range].\nThis attack benefits from bonuses to [minion_range:minion_range], and does not stun.")

        def get_impacted_tiles(self, x, y):
            return [u for u in self.caster.level.units if u is not self.caster and not are_hostile(u, self.caster) and (Tags.Living in u.tags or (self.get_stat("blood") and (Tags.Nature in u.tags or Tags.Demon in u.tags)))]

        def cast(self, x, y):

            damage = self.get_stat("damage")
            duration = self.get_stat("duration")
            stampede = self.get_stat("stampede")
            minion_range = self.get_stat("minion_range", base=6)

            eligible = [Tags.Living, Tags.Nature, Tags.Demon] if self.get_stat("blood") else [Tags.Living]

            units = list(self.caster.level.units)
            for unit in units:
                if unit is self.caster or are_hostile(self.caster, unit):
                    continue
                if not [tag for tag in eligible if tag in unit.tags]:
                    continue

                melee = SimpleMeleeAttack(damage=damage, buff=Stun, buff_duration=duration)
                charge = LeapAttack(damage=damage, range=minion_range, is_leap=False) if stampede else None

                melee.statholder = unit
                melee.caster = unit
                melee.owner = unit
                melee_targets = [u for u in self.caster.level.get_units_in_ball(unit, radius=1, diag=True) if are_hostile(u, self.caster) and not is_immune(u, melee, melee.damage_type)]
                if melee_targets:
                    target = random.choice(melee_targets)
                    self.caster.level.act_cast(unit, melee, target.x, target.y, pay_costs=False)
                    yield
                elif charge:
                    charge.statholder = unit
                    charge.caster = unit
                    charge.owner = unit
                    charge_targets = [u for u in units if are_hostile(u, self.caster) and charge.can_cast(u.x, u.y) and not is_immune(u, charge, charge.damage_type)]
                    if not charge_targets:
                        continue
                    target = random.choice(charge_targets)
                    self.caster.level.act_cast(unit, charge, target.x, target.y, pay_costs=False)
                    yield

    if cls is MeltSpell:

        def on_init(self):
            self.tags = [Tags.Fire, Tags.Sorcery, Tags.Enchantment]
            self.level = 2
            self.max_charges = 15
            self.name = "Melt"
            self.damage = 22
            self.range = 6

            self.upgrades['damage'] = (16, 2)
            self.upgrades['max_charges'] = 10
            self.upgrades['fire_resist'] = (1, 4, "Fire Penetration", "Melt also reduces [fire] resist by 100")

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(MeltBuff(self), self.get_stat('duration'))
            self.caster.level.deal_damage(x, y, self.get_stat('damage'), Tags.Fire, self)

        def get_description(self):
            return "Target unit loses [100_physical:physical] resist and takes [{damage}_fire:fire] damage.".format(**self.fmt_dict())

    if cls is MeltBuff:

        def on_init(self):
            self.resists[Tags.Physical] = -100
            if self.spell.get_stat('fire_resist'):
                self.resists[Tags.Fire] = -100
            self.color = Color(255, 100, 100)
            self.name = "Melted"
            self.buff_type = BUFF_TYPE_CURSE
            self.stack_type = STACK_REPLACE

    if cls is PetrifySpell:

        def on_init(self):
            self.range = 8
            self.max_charges = 10
            self.name = "Petrify"

            self.tags = [Tags.Arcane, Tags.Enchantment]

            self.duration = 10

            self.upgrades['max_charges'] = (5, 1)
            self.upgrades['glassify'] = (1, 3, 'Glassify', 'Turn the target to glass instead of stone.  Glass targets have -100 physical resist.')
            self.add_upgrade(StoneCurseUpgrade())
            self.level = 2

    if cls is SoulSwap:

        def on_init(self):
            self.requires_los = False
            self.range = RANGE_GLOBAL

            self.name = "Soul Swap"
            
            self.max_charges = 9

            self.level = 2
            self.tags = [Tags.Dark, Tags.Sorcery, Tags.Translocation]

            self.upgrades['forced_transfer'] = (1, 2, 'Forced Transfer', 'Soul Swap can target enemy units as well.')
            self.upgrades["dark"] = (1, 2, "Shadow Swap", "Soul Swap can target [dark] units as well.")
            self.upgrades["demon"] = (1, 3, "Infernal Swap", "Soul Swap can target [demon] units as well.")
            self.upgrades['max_charges'] = (9, 2)

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return False
            if are_hostile(self.caster, unit) and not self.get_stat('forced_transfer'):
                return False
            if not self.caster.level.can_move(self.caster, x, y, teleport=True, force_swap=True):
                return False
            if Tags.Undead in unit.tags:
                return True
            if Tags.Dark in unit.tags and self.get_stat("dark"):
                return True
            if Tags.Demon in unit.tags and self.get_stat("demon"):
                return True
            return False

    if cls is TouchOfDeath:

        def on_init(self):
            self.damage = 200
            self.element = Tags.Dark
            self.range = 1
            self.melee = True
            self.can_target_self = False
            self.max_charges = 9
            self.name = "Touch of Death"
            self.tags = [Tags.Dark, Tags.Sorcery]
            self.level = 2

            self.can_target_empty = False
            self.upgrades["damage"] = (200, 4)
            self.upgrades['arcane'] = (1, 2, "Voidtouch", "Touch of Death also deals [arcane] damage.")
            self.upgrades['fire'] = (1, 2, "Flametouch", "Touch of Death also deals [fire] damage.")
            self.upgrades["lightning"] = (1, 2, "Thundertouch", "Touch of Death also deals [lightning] damage.")
            self.upgrades['physical'] = (1, 2, "Wrathtouch", "Touch of Death also deals [physical] damage.")
            self.upgrades['raise']= (1, 6, 'Touch of the Reaper', 'When a target dies to touch of death, it is raise as a friendly Reaper for [6_turns:duration], which benefits from [minion_duration:minion_duration] bonuses.\nThe Reaper can cast Touch of Death with the same upgrades and bonuses as your own.')

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            dtypes = [Tags.Dark]
            if self.get_stat("arcane"):
                dtypes.append(Tags.Arcane)
            if self.get_stat("fire"):
                dtypes.append(Tags.Fire)
            if self.get_stat("lightning"):
                dtypes.append(Tags.Lightning)
            if self.get_stat("physical"):
                dtypes.append(Tags.Physical)
            for dtype in dtypes:
                self.caster.level.deal_damage(x, y, self.get_stat('damage'), dtype, self)

            if unit and not unit.is_alive() and self.get_stat("raise"):
                reaper = Reaper()
                reaper.turns_to_death = self.get_stat('minion_duration', base=6)
                spell = TouchOfDeath()
                spell.max_charges = 0
                spell.cur_charges = 0
                spell.statholder = self.caster
                spell.caster = reaper
                spell.owner = reaper
                reaper.spells[0] = spell
                self.summon(reaper, Point(unit.x, unit.y))
                unit.has_been_raised = True

    if cls is ToxicSpore:

        def on_init(self):
            self.name = "Toxic Spores"

            self.level = 2
            self.tags = [Tags.Conjuration, Tags.Nature]
            self.range = 8
            self.max_charges = 16	

            example = GreenMushboom()
            self.minion_health = example.max_hp
            self.minion_damage = example.spells[0].damage

            self.num_summons = 2
            self.minion_range = 2
            self.upgrades['num_summons'] = (2, 3)
            self.upgrades['toxic_mushboom'] = (1, 4, "Toxic Mushbooms", "Summon toxic mushbooms instead, which are like green mushbooms but also have auras that deal [1_poison:poison] damage in a [3_tile:radius] radius.", "color")
            self.upgrades['red_mushboom'] = (1, 5, "Red Mushbooms", "Summon red mushbooms instead, which do not apply [poison] but deal [fire] damage.", "color")
            self.upgrades['glass_mushboom'] = (1, 6, "Glass Mushbooms", "Summon glass mushbooms instead, which apply [glassify] instead of [poison].", "color")


        def get_description(self):
            return ("Summons [{num_summons}:num_summons] Mushbooms.\n"
                    "Mushbooms have [{minion_health}_HP:minion_health].\n"
                    "Mushbooms have a ranged attack dealing [{minion_damage}_poison:poison] damage and inflicting [4_turns:duration] of [poison].\n"
                    "Mushbooms inflict [12_turns:duration] of [poison] on units in melee range when they die.\n"
                    "The debuffs inflicted by mushbooms benefit from this spell's bonuses to [duration].").format(**self.fmt_dict())

        def cast(self, x, y):
            green = 0
            toxic = self.get_stat('toxic_mushboom')
            red = self.get_stat('red_mushboom')
            glass = self.get_stat('glass_mushboom')
            for _ in range(self.get_stat('num_summons')):
                if red:
                    mushboom = RedMushboom()
                elif glass:
                    mushboom = GlassMushboom()
                    duration = self.get_stat("duration", base=2)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = GlassPetrifyBuff
                    spell.buff_duration = duration
                    spell.description = "Applies %i turns of glassify" % duration
                else:
                    mushboom = GreenMushboom()
                    green = 1
                    duration = self.get_stat("duration", base=4)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = Poison
                    spell.buff_duration = duration
                    spell.description = "Applies %i turns of poison" % duration
                if green or glass:
                    mushboom.buffs[0].apply_duration = self.get_stat("duration", base=mushboom.buffs[0].apply_duration)
                    # Update description
                    mushboom.buffs[0].on_init()
                else:
                    mushboom.buffs[0] = curr_module.RedMushboomBuff(self.get_stat("minion_damage") - self.minion_damage)
                if toxic:
                    mushboom.name = "Toxic Mushboom"
                    mushboom.asset = ["UnderusedOptions", "Units", "toxic_mushboom"]
                    mushboom.buffs.append(DamageAuraBuff(damage=1, damage_type=Tags.Poison, radius=3))
                    mushboom.tags.append(Tags.Poison)
                apply_minion_bonuses(self, mushboom)
                self.summon(mushboom, target=Point(x, y))
                yield

    if cls is VoidRip:

        def on_init(self):
            self.name = "Aether Swap"
            self.range = 7

            self.max_charges = 8
            self.damage = 16
            self.level = 3

            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Aether Swap can be cast without line of sight")
            self.upgrades['range'] = (3, 1)
            self.upgrades['max_charges'] = (10, 3)
            self.upgrades["physical"] = (1, 4, "Tele-Frag", "Aether Swap also deals [physical] damage.")

            self.tags = [Tags.Arcane, Tags.Translocation, Tags.Sorcery]

        def get_description(self):
            return ("Swap places with target unit.\n"
                    "That unit takes [{damage}_arcane:arcane] damage.").format(**self.fmt_dict())

        def can_cast(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return False
            if unit == self.caster:
                return False
            if not self.caster.level.tiles[x][y].can_walk:
                return False
            return Spell.can_cast(self, x, y)

        def cast_instant(self, x, y):
            target = self.caster.level.get_unit_at(x, y)
            
            # Fizzle if attempting to cast on non walkable tile
            if self.caster.level.tiles[x][y].can_walk:
                self.caster.level.act_move(self.caster, x, y, teleport=True, force_swap=True)	
                
            if target:
                target.deal_damage(self.get_stat('damage'), Tags.Arcane, self)
                if self.get_stat("physical"):
                    target.deal_damage(self.get_stat('damage'), Tags.Physical, self)

    if cls is CockatriceSkinSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Basilisk Armor"
            self.duration = 10
            self.petrify_duration = 2

            self.upgrades['duration'] = 5
            self.upgrades["petrify_duration"] = (3, 2)
            self.upgrades["thorns"] = (1, 4, "Thorns", "Enemies targeting you with spells also take [16_poison:poison] damage.\nIf you have the Stunning Armor upgrade, also deal [lightning] damage.\nIf you have the Freezing Armor upgrade, also deal [ice] damage.\nIf you have the Glassifying Armor upgrade, also deal [physical] damage.")
            self.upgrades["stun"] = (1, 2, "Stunning Armor", "Basilisk Armor inflicts [stun] instead of [petrify].", "armor")
            self.upgrades["freeze"] = (1, 2, "Freezing Armor", "Basilisk Armor inflicts [freeze] instead of [petrify].", "armor")
            self.upgrades["glassify"] = (1, 2, "Glassifying Armor", "Basilisk Armor inflicts [glassify] instead of [petrify].", "armor")

            self.tags = [Tags.Enchantment, Tags.Nature, Tags.Arcane]
            self.level = 3

        def cast_instant(self, x, y):
            self.caster.apply_buff(BasiliskArmorBuff(self), self.get_stat("duration"))

        def get_description(self):
            return ("Whenever an enemy unit targets you with a spell or attack, that unit is [petrified] for [{petrify_duration}_turns:duration].\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is AngelSong:

        def on_init(self):
            self.name = "Sing"
            self.description = "Living and holy units are healed, undead, demons, and dark units take holy and fire damage."
            self.radius = 5
            self.damage = 2
            self.heal = 1
            self.range = 0
            self.pragmatic = False

        def cast_instant(self, x, y):
            heal = self.get_stat('heal')
            damage = self.get_stat('damage')
            for unit in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat('radius')):
                if unit.is_player_controlled:
                    continue
                if (Tags.Living in unit.tags or Tags.Holy in unit.tags) and unit.cur_hp < unit.max_hp:
                    if self.pragmatic and are_hostile(unit, self.caster):
                        continue
                    unit.deal_damage(-heal, Tags.Heal, self)
                if Tags.Dark in unit.tags or Tags.Undead in unit.tags or Tags.Demon in unit.tags:
                    if self.pragmatic and not are_hostile(unit, self.caster):
                        continue
                    unit.deal_damage(damage, Tags.Fire, self)
                    unit.deal_damage(damage, Tags.Holy, self)

        def get_ai_target(self):
            units = self.caster.level.get_units_in_ball(self.caster, self.get_stat('radius'))
            for unit in units:
                if unit.is_player_controlled:
                    continue
                if (Tags.Living in unit.tags or Tags.Holy in unit.tags) and unit.cur_hp < unit.max_hp:
                    if self.pragmatic and are_hostile(unit, self.caster):
                        continue
                    return self.caster
                if Tags.Undead in unit.tags or Tags.Demon in unit.tags or Tags.Dark in unit.tags:
                    if self.pragmatic and not are_hostile(unit, self.caster):
                        continue
                    return self.caster
            return None

    if cls is AngelicChorus:

        def on_init(self):
            self.name = "Choir of Angels"

            self.minion_health = 10
            self.shields = 1
            self.minion_duration = 10
            self.num_summons = 3
            self.heal = 1
            self.minion_damage = 2
            self.radius = 5

            self.range = 7

            self.tags = [Tags.Holy, Tags.Conjuration]
            self.level = 3

            self.max_charges = 5

            self.upgrades['shields'] = (2, 2)
            self.upgrades['num_summons'] = (3, 4)
            self.upgrades['minion_duration'] = (10, 2)
            self.upgrades['heal'] = (2, 3)
            self.upgrades["pragmatic"] = (1, 3, "Pragmatic Faith", "The angels will no longer damage [undead] and [demon] allies, or heal [living] and [holy] enemies.")

        def cast(self, x, y):

            for _ in range(self.get_stat('num_summons')):
                angel = Unit()
                angel.name = "Angelic Singer"
                angel.max_hp = self.get_stat('minion_health')
                angel.shields = self.get_stat('shields')
                
                song = AngelSong()
                song.damage = self.get_stat('minion_damage')
                song.heal = self.get_stat('heal')
                song.radius = self.get_stat('radius')
                song.pragmatic = self.get_stat("pragmatic")
                
                angel.spells.append(song)

                angel.flying = True
                angel.tags = [Tags.Holy]
                angel.resists[Tags.Holy] = 50
                angel.resists[Tags.Fire] = 50
                angel.resists[Tags.Dark] = 100

                angel.turns_to_death = self.get_stat('minion_duration')

                self.summon(angel, Point(x, y))
                yield

    if cls is Darkness:

        def on_init(self):
            self.name = "Darkness"
            self.duration = 5
            self.max_charges = 3
            self.level = 3
            self.tags = [Tags.Dark, Tags.Enchantment]
            self.range = 0

            self.upgrades['duration'] = (3, 2)
            self.upgrades["horizon"] = (1, 3, "Dark Horizon", "Hostile [demon] and [undead] units have a 5% chance to be [blinded:blind] per tile away from you.")
            self.upgrades["echo"] = (1, 6, "Dark Echoes", "While Darkness is active, if you are [blind], your [demon] and [undead] minions redeal half of all their damage as the original damage type.")

        def cast_instant(self, x, y):
            self.caster.apply_buff(curr_module.DarknessBuff(self), self.get_stat('duration'))

    if cls is MindDevour:

        def on_init(self):
            self.name = "Devour Mind"
            self.range = 4
            self.tags = [Tags.Arcane, Tags.Dark, Tags.Sorcery]
            self.max_charges = 7
            self.level = 3

            self.damage = 25
            self.threshold = .5

            self.requires_los = False

            self.upgrades['damage'] = (18, 3)
            self.upgrades['spiriteater'] = (1, 4, "Spirit Eater", "Can now target [holy], [demon], [undead], and [arcane] units.")
            self.upgrades["gouge"] = (1, 3, "Mind Gouge", "If the target is over 50% HP after taking [arcane] damage, instead deal half [dark] damage to it.")
            self.upgrades["mindless"] = (1, 3, "Mindless Eater", "Can now target all enemies.\nWhen targeting a unit outside of this spell's previously valid target groups, only the initial [arcane] damage is dealt.")
            self.upgrades['gluttony'] = (1, 2, "Gluttony", "If Devour Mind kills the target, the charge cost is refunded.")
            self.upgrades["rot"] = (1, 4, "Mind Rot", "If the target dies to [arcane] damage, summon a void imp and an insanity imp near it.\nIf the target dies to [dark] damage, summon a rot imp near it.")

        def get_description(self):
            return ("Deal [{damage}_arcane:arcane] to an enemy unit.\n"
                    "Then, if the target is under 50% HP, deal it an additional [{damage}_dark:dark] damage.\n"
                    "Can only target [living] and [nature] units.").format(**self.fmt_dict())

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return False
            if not are_hostile(self.caster, unit):
                return False
            if self.get_stat("mindless"):
                return True
            if Tags.Living in unit.tags or Tags.Nature in unit.tags:
                return True
            if self.get_stat('spiriteater') and (Tags.Holy in unit.tags or Tags.Demon in unit.tags or Tags.Undead in unit.tags or Tags.Arcane in unit.tags):
                return True        
            return False

        def cast(self, x, y):

            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return

            # Queue all these effects to make them check for HP thresholds after redeals
            arcane_dealt = unit.deal_damage(self.get_stat("damage"), Tags.Arcane, self)
            if self.get_stat("rot") and arcane_dealt:
                self.caster.level.queue_spell(arcane_summon(self, unit))
            
            self.caster.level.queue_spell(dark_damage(self, unit))

            yield

        def arcane_summon(self, unit):
            if unit.is_alive():
                return
            void_imp = VoidImp()
            apply_minion_bonuses(self, void_imp)
            self.summon(void_imp, target=unit, radius=5)
            insanity_imp = InsanityImp()
            apply_minion_bonuses(self, insanity_imp)
            self.summon(insanity_imp, target=unit, radius=5)
            yield

        def dark_damage(self, unit):

            eligible = [Tags.Living, Tags.Nature]
            if self.get_stat("spiriteater"):
                eligible.extend([Tags.Holy, Tags.Demon, Tags.Undead, Tags.Arcane])

            dark_dealt = 0
            if [tag for tag in eligible if tag in unit.tags]:
                if unit.cur_hp/unit.max_hp < .5:
                    dark_dealt = unit.deal_damage(self.get_stat("damage"), Tags.Dark, self)
                elif self.get_stat("gouge"):
                    dark_dealt = unit.deal_damage(self.get_stat("damage")//2, Tags.Dark, self)

            if self.get_stat("rot") and dark_dealt:
                self.caster.level.queue_spell(dark_summon(self, unit))

            if self.get_stat('gluttony'):
                self.caster.level.queue_spell(recover_charge(self, unit))

            yield

        def dark_summon(self, unit):
            if unit.is_alive():
                return
            rot_imp = RotImp()
            apply_minion_bonuses(self, rot_imp)
            self.summon(rot_imp, target=unit, radius=5)
            yield

        def recover_charge(self, unit):
            if unit.is_alive():
                return
            self.cur_charges += 1
            self.cur_charges = min(self.cur_charges, self.get_stat('max_charges'))
            yield

    if cls is Dominate:

        def on_init(self):
            self.name = "Dominate"
            self.range = 5
            self.max_charges = 4
        
            self.tags = [Tags.Arcane, Tags.Enchantment]
            self.level = 3

            self.hp_threshold = 40

            self.upgrades['max_charges'] = (2, 2)
            self.upgrades['hp_threshold'] = (40, 3, 'HP Threshold', 'Increase the maximum HP units which can be targeted.')
            self.upgrades['check_cur_hp'] = (1, 4, 'Brute Force', 'Dominate targets based on current HP instead of maximum HP.')
            self.upgrades["mass"] = (1, 6, "Mass Dominate", "When cast, Dominate now also affects all eligible enemies with the same name as the target within [3_tiles:radius].")
            self.upgrades["heal"] = (1, 3, "Recruitment Bonus", "The target is now healed to full HP after being dominated, and all of its debuffs are dispelled.")

        def get_impacted_tiles(self, x, y):
            points = [Point(x, y)]
            hp_threshold = self.get_stat("hp_threshold")
            check_cur_hp = self.get_stat("check_cur_hp")
            origin = self.caster.level.get_unit_at(x, y)
            if origin and self.get_stat("mass"):
                for unit in self.caster.level.get_units_in_ball(origin, self.get_stat("radius", base=3)):
                    if unit is origin:
                        continue
                    hp = unit.cur_hp if check_cur_hp else unit.max_hp
                    if are_hostile(self.caster, unit) and hp <= hp_threshold and unit.name == origin.name:
                        points.append(Point(unit.x, unit.y))
            return points

        def cast(self, x, y):
            heal = self.get_stat("heal")
            for point in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if not unit:
                    continue
                unit.team = self.caster.team
                unit.source = self
                unit.level.event_manager.raise_event(EventOnUnitAdded(unit), unit)
                if heal:
                    unit.deal_damage(-unit.max_hp, Tags.Heal, self)
                    for buff in unit.buffs:
                        if buff.buff_type == BUFF_TYPE_CURSE:
                            unit.remove_buff(buff)
                yield

    if cls is EarthquakeSpell:

        def on_init(self):
            self.name = "Earthquake"

            self.radius = 7
            self.max_charges = 4
            self.range = 0

            self.damage = 21
            self.strikechance = 50
            self.level = 3
            self.tags = [Tags.Sorcery, Tags.Nature]

            self.upgrades['radius'] = (2, 3)
            self.upgrades['damage'] = (17, 3)
            self.upgrades["strikechance"] = (25, 3)
            self.upgrades['safety'] = (1, 2, "Safety", "Earthquake will not damage friendly units.")

        def get_description(self):
            return ("Invoke an earthquake with a [{radius}_tile:radius] radius.\n"
                    "Each tile in the area has a [{strikechance}%:strikechance] chance to be affected.\n"
                    "Units on affected tiles take [{damage}_physical:physical] physical damage.\n"
                    "Affected tiles are turned into floor tiles.").format(**self.fmt_dict())

        def cast(self, x, y):
            points = list(self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, radius=self.get_stat('radius')))
            random.shuffle(points)
            safety = self.get_stat("safety")
            damage = self.get_stat('damage')
            strikechance = self.get_stat("strikechance")/100
            for p in points:

                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit is self.caster:
                    continue

                if safety and unit and not are_hostile(self.caster, unit):
                    continue

                if random.random() >= strikechance:
                    continue

                self.caster.level.show_effect(p.x, p.y, Tags.Physical)

                if random.random() < .3:
                    yield

                if unit:
                    unit.deal_damage(damage, Tags.Physical, self)
                    continue

                tile = self.caster.level.tiles[p.x][p.y]
                if not tile.can_walk:
                    self.caster.level.make_floor(p.x, p.y)

    if cls is FlameBurstSpell:

        def on_init(self):
            self.name = "Flame Burst"
            self.range = 0
            self.max_charges = 6
            self.damage = 35
            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 3
            self.radius = 6

            self.upgrades['radius'] = (3, 2)
            self.upgrades['damage'] = (15, 3)
            self.upgrades['max_charges'] = (3, 2)

            self.upgrades['meltflame'] = (1, 4, "Melting Flame", "Melt walls adjacent to the blast", "flame")
            self.upgrades['healflame'] = (1, 4, "Phoenix Flame", "Flame Burst heals allied units instead of damaging them.\nThe wizard cannot be healed this way.", "flame")
            self.upgrades['spreadflame'] = (1, 7, "Spreading Flame", "Each cast of flame burst consumes all remaining charges.\nFor each charge consumed, flame burst gets +1 radius and +1 damage.\nSlain enemies create additional explosions with half radius and damage.", "flame")

        def cast(self, x, y, secondary=False, last_radius=None, last_damage=None):

            if secondary:
                radius = last_radius // 2
                damage = last_damage // 2

                if radius < 2:
                    return
                if damage < 0:
                    return

            else:
                radius = self.get_stat('radius')
                damage = self.get_stat('damage')

            if not secondary and self.get_stat('spreadflame'):
                radius += self.cur_charges
                damage += self.cur_charges
                self.cur_charges = 0

            to_melt = set([Point(self.caster.x, self.caster.y)])
            slain = []

            heal = self.get_stat("healflame")
            melt = self.get_stat("meltflame")

            stagenum = 0
            for stage in Burst(self.caster.level, Point(x, y), radius):
                stagenum += 1

                for p in stage:
                    if p.x == self.caster.x and p.y == self.caster.y:
                        continue

                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if heal and unit and not are_hostile(unit, self.caster):
                        self.caster.level.show_effect(p.x, p.y, Tags.Fire)
                        if not unit.is_player_controlled:
                            unit.deal_damage(-damage, Tags.Heal, self)
                    else:
                        self.caster.level.deal_damage(p.x, p.y, damage, Tags.Fire, self)
                        if unit and are_hostile(unit, self.caster) and not unit.is_alive():
                            slain.append(unit)

                    if melt:
                        for q in self.caster.level.get_points_in_ball(p.x, p.y, 1):
                            if self.caster.level.tiles[q.x][q.y].is_wall():
                                to_melt.add(q)
                        
                yield

            if self.get_stat('spreadflame'):
                for unit in slain:
                    self.owner.level.queue_spell(self.cast(unit.x, unit.y, secondary=True, last_damage=damage, last_radius=radius))

            if self.get_stat('meltflame'):
                for p in to_melt:
                    self.caster.level.make_floor(p.x, p.y)
                    self.caster.level.show_effect(p.x, p.y, Tags.Fire)

    if cls is SummonFrostfireHydra:

        HYDRA_FROSTFIRE = 0
        HYDRA_FROST = 1
        HYDRA_FIRE = 2

        def on_init(self):
            self.name = "Frostfire Hydra"
            
            self.tags = [Tags.Ice, Tags.Fire, Tags.Dragon, Tags.Conjuration]
            self.level = 3
            self.max_charges = 7

            self.minion_range = 9
            self.minion_damage = 7
            self.minion_health = 16

            self.upgrades['minion_range'] = (6, 3)
            self.upgrades['minion_damage'] = (7, 4)
            self.upgrades["splitting"] = (1, 4, "Splitting", "Upon reaching 0 HP, the hydra splits into a frost hydra and a fire hydra.\nEach hydra inherits one of the frostfire hydra's beams and resistances.")
            self.add_upgrade(FrostfireHydraDragonMage())

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["beam_damage"] = self.get_stat("minion_damage") + self.get_stat("breath_damage", base=0)
            return stats

        def get_description(self):
            return ("Summon a frostfire hydra.\n"
                    "The hydra has [{minion_health}_HP:minion_health], and is stationary.\n"
                    "The hydra has a beam attack which deals [{beam_damage}_fire:fire] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "The hydra has a beam attack which deals [{beam_damage}_ice:ice] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "The hydra's beams are not considered breath weapons, but they benefit from bonuses to both [minion_damage:minion_damage] and [breath_damage:dragon].").format(**self.fmt_dict())

        def get_frost_hydra(self):
            unit = Unit()
            unit.source = self
            set_hydra_stats(self, unit, hydra_type=HYDRA_FROST)
            return unit

        def get_fire_hydra(self):
            unit = Unit()
            unit.source = self
            set_hydra_stats(self, unit, hydra_type=HYDRA_FIRE)
            return unit

        def set_hydra_stats(self, unit, hydra_type=HYDRA_FROSTFIRE):

            unit.max_hp = self.get_stat('minion_health')

            if hydra_type == HYDRA_FROST:
                unit.name = "Frost Hydra"
                unit.asset = ["UnderusedOptions", "Units", "frost_hydra"]
            elif hydra_type == HYDRA_FIRE:
                unit.name = "Fire Hydra"
                unit.asset = ["UnderusedOptions", "Units", "fire_hydra"]
            else:
                unit.name = "Frostfire Hydra"
                unit.asset_name = 'fire_and_ice_hydra'

            fire = SimpleRangedAttack(damage=self.get_stat('minion_damage') + self.get_stat("breath_damage", base=0), range=self.get_stat('minion_range'), damage_type=Tags.Fire, beam=True)
            fire.name = "Hydra Beam"
            fire.cool_down = 2

            ice = SimpleRangedAttack(damage=self.get_stat('minion_damage') + self.get_stat("breath_damage", base=0), range=self.get_stat('minion_range'), damage_type=Tags.Ice, beam=True)
            ice.name = "Hydra Beam"
            ice.cool_down = 2

            unit.stationary = True
            unit.tags = [Tags.Dragon]
            
            if hydra_type == HYDRA_FROSTFIRE or hydra_type == HYDRA_FROST:
                unit.spells.append(ice)
                unit.tags.append(Tags.Ice)
                unit.resists[Tags.Ice] = 100
            
            if hydra_type == HYDRA_FROSTFIRE or hydra_type == HYDRA_FIRE:
                unit.spells.append(fire)
                unit.tags.append(Tags.Fire)
                unit.resists[Tags.Fire] = 100

        def cast_instant(self, x, y):
            unit = Unit()
            set_hydra_stats(self, unit)
            if self.get_stat("splitting"):
                unit.buffs = [RespawnAs(lambda: get_frost_hydra(self)), RespawnAs(lambda: get_fire_hydra(self))]
            self.summon(unit, Point(x, y))

    if cls is SummonGiantBear:

        def on_init(self):
            self.max_charges = 5
            self.name = "Giant Bear"
            self.minion_health = 65
            self.minion_damage = 10
            
            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 3

            self.minion_attacks = 1
            self.upgrades['minion_health'] = (30, 2)
            self.upgrades['minion_damage'] = (15, 4)
            self.upgrades['minion_attacks'] = (1, 3)
            self.upgrades['venom'] = (1, 4, "Venom Bear", "Summons a venom bear instead of a giant bear.\nVenom Bears have a poison bite, and heal whenever an enemy takes poison damage.", "species")
            self.upgrades['blood'] = (1, 5, "Blood Bear", "Summons a blood bear instead of a giant bear.\nBlood bears are resistant to dark damage, and deal increasing damage with each attack.", "species")
            self.upgrades["polar"] = (1, 5, "Polar Bear", "Summons a polar bear instead of a giant bear.\nPolar bears are resistant to ice damage, can freeze units around itself, and gains regeneration and an ice aura while frozen.\nFor every [100_ice:ice] resistance the polar bear has above 100, the self-healing and ice aura activate once per turn. An excess of less than 100 instead has a chance to activate these effects.", "species")
            self.upgrades["roar"] = (1, 4, "Roar", "The bear gains a roar with a cooldown of 3 turns that stuns enemies in a [7_range:range] cone for [3_turns:duration].\nThe venom bear's roar will also [poison] enemies for [5_turns:duration] and give regeneration to allies for the same duration.\nThe blood bear's roar will instead [berserk] enemies and give allies a stack of bloodlust for [10_turns:duration].\nThe polar bear's roar will instead [freeze] enemies and heal allies for an amount equal to its regeneration when frozen.")

            self.must_target_walkable = True
            self.must_target_empty = True

        def cast(self, x, y):

            bear = Unit()
            bear.max_hp = self.get_stat('minion_health')
            
            bear.name = "Giant Bear"
            bear.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))

            bear.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('venom'):
                bear.name = "Venom Beast"
                bear.asset_name = "giant_bear_venom"
                bear.resists[Tags.Poison] = 100
                bear.tags = [Tags.Living, Tags.Poison, Tags.Nature]
                bite = SimpleMeleeAttack(damage=self.get_stat('minion_damage'), buff=Poison, buff_duration=5)
                bite.name = "Poison Bite"
                bear.spells = [bite]
                bear.buffs = [VenomBeastHealing()]

            elif self.get_stat('polar'):
                bear.name = "Polar Bear"
                bear.asset_name = "polar_bear"
                bear.resists[Tags.Ice] = 50
                bear.resists[Tags.Fire] = -50
                bear.tags = [Tags.Ice, Tags.Living, Tags.Nature]
                bear.buffs = [PolarBearAura()]

            elif self.get_stat('blood'):
                bear = BloodBear()
                apply_minion_bonuses(self, bear)
            
            bear.spells[0].attacks = self.get_stat('minion_attacks')
            if self.get_stat('minion_attacks') > 1:
                bear.spells[0].description += "\nAttacks %d times." % self.get_stat('minion_attacks')
            
            if self.get_stat("polar"):
                bear.spells.insert(0, PolarBearFreeze())
            
            if self.get_stat("roar"):
                if self.get_stat("venom"):
                    bear_type = GiantBearRoar.BEAR_TYPE_VENOM
                elif self.get_stat("blood"):
                    bear_type = GiantBearRoar.BEAR_TYPE_BLOOD
                elif self.get_stat("polar"):
                    bear_type = GiantBearRoar.BEAR_TYPE_POLAR
                else:
                    bear_type = GiantBearRoar.BEAR_TYPE_DEFAULT
                bear.spells.insert(0, GiantBearRoar(bear_type=bear_type))

            self.summon(bear, Point(x, y))
            yield

    if cls is HolyFlame:

        def on_init(self):
            self.name = "Holy Fire"

            self.tags = [Tags.Fire, Tags.Holy, Tags.Sorcery]

            self.max_charges = 7

            self.damage = 11
            self.duration = 3
            self.radius = 2

            self.range = 7

            self.upgrades['duration'] = (3, 2)
            self.upgrades['damage'] = (7, 3)
            self.upgrades['radius'] = (2, 2)
            self.upgrades["requires_los"] = (-1, 2, "Blindcasting", "Holy Fire no longer requires line of sight to cast.")
            self.upgrades["nightbane"] = (1, 2, "Nightbane", "[Dark] and [ice] units will also be stunned.")

            self.level = 3

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["length"] = self.get_stat("radius")*2 + 1
            return stats

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage and [{damage}_holy:holy] damage in a vertical line and in a horizontal line, each [{length}_tiles:radius] long.\n"
                    "The lines intersect at the target point, which is hit by both lines.\n"
                    "[Stun] [demon] and [undead] units in the affected area for [{duration}_turns:duration].").format(**self.fmt_dict())

        def get_impacted_tiles(self, x, y):
            rad = self.get_stat('radius')
            for i in range(-rad, rad + 1):
                yield Point(x+i, y)
                if i != 0:
                    yield Point(x, y+i)

        def cast(self, x, y):
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            dtypes = [Tags.Holy, Tags.Fire]
            stun_types = [Tags.Demon, Tags.Undead]
            if self.get_stat("nightbane"):
                stun_types.extend([Tags.Dark, Tags.Ice])

            rad = self.get_stat('radius')
            for i in range(y - rad, y + rad + 1):
                if not self.caster.level.is_point_in_bounds(Point(x, i)):
                    continue

                for dtype in dtypes:
                    self.caster.level.deal_damage(x, i, damage, dtype, self)
                unit = self.caster.level.get_unit_at(x, i)
                if unit and [tag for tag in stun_types if tag in unit.tags]:
                    unit.apply_buff(Stun(), duration)
                yield

            for i in range(2):
                yield

            for i in range(x - rad, x + rad + 1):
                if not self.caster.level.is_point_in_bounds(Point(i, y)):
                    continue

                for dtype in dtypes:
                    self.caster.level.deal_damage(i, y, damage, dtype, self)
                unit = self.caster.level.get_unit_at(i, y)
                if unit and [tag for tag in stun_types if tag in unit.tags]:
                    unit.apply_buff(Stun(), duration)
                yield

    if cls is HolyShieldSpell:

        def on_init(self):
            self.name = "Holy Armor"

            self.tags = [Tags.Holy, Tags.Enchantment]
            self.level = 3
            self.duration = 9
            self.resist = 50
            self.max_charges = 6

            self.upgrades['duration'] = (7, 3)
            self.upgrades['resist'] = 25
            self.upgrades["riposte"] = (1, 4, "Divine Riposte", "While Holy Armor is active, if you pass your turn, you will gain Divine Riposte until the end of your next turn.\nWhen you have Divine Riposte, you retaliate for [18_holy:holy] damage whenever an enemy damages you. This damage benefits from bonuses.\nThe duration of Divine Riposte is fixed and unaffected by bonuses.")

            self.range = 0

        def cast_instant(self, x, y):
            buff = HolyShieldBuff(self.get_stat('resist'))
            if self.get_stat("riposte"):
                buff.owner_triggers[EventOnPass] = lambda evt: self.owner.apply_buff(DivineRiposteBuff(self), 2)
            self.caster.apply_buff(buff, self.get_stat('duration'))

    if cls is ProtectMinions:

        def on_init(self):
            self.name = "Ironize"
            self.resist = 50
            self.duration = 10
            self.max_charges = 5
            self.level = 3
            
            self.tags = [Tags.Enchantment, Tags.Metallic]
            self.range = 0

            self.resist_arcane = 0
            self.upgrades['resist'] = (25, 2)
            self.upgrades['duration'] = 15
            self.upgrades['resist_arcane'] = (1, 2, "Arcane Insulation")
            self.upgrades["retroactive"] = (1, 4, "Retroactive", "You now gain Iron Aura when you cast this spell, during which all minions you summon will automatically gain Ironize for the remaining duration.")

        def cast_instant(self, x, y):
            duration = self.get_stat("duration")
            if self.get_stat("retroactive"):
                self.caster.apply_buff(MinionBuffAura(lambda: IronSkinBuff(self), lambda unit: True, "Iron Aura", "minions"), duration)
                return
            for unit in self.caster.level.units:
                if unit == self.caster:
                    continue
                if self.caster.level.are_hostile(unit, self.caster):
                    continue
                unit.apply_buff(IronSkinBuff(self), duration)

    if cls is LightningHaloSpell:

        def on_init(self):
            self.name = "Lightning Halo"
            self.range = 0
            self.max_charges = 5
            self.duration = 9
            self.tags = [Tags.Enchantment, Tags.Lightning]
            self.level = 3
            self.damage = 15
            self.element = Tags.Lightning

            self.radius = 3
            self.upgrades['radius'] = (1, 1)
            self.upgrades['duration'] = (3, 2)
            self.upgrades['damage'] = (10, 2)
            self.upgrades["holy"] = (1, 5, "Divine Halo", "Lightning Halo also deals [holy] damage.")
            self.upgrades["repel"] = (1, 3, "Repelling Halo", "Units inside the halo are pushed away by [1_tile:radius] each turn.")

        def get_description(self):
            return ("Deal [{damage}_lightning:lightning] damage to all units in a [{radius}_tile:radius] ring each turn, and whenever a unit enters an affected tile.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is LightningHaloBuff:

        def __init__(self, spell):
            Buff.__init__(self)
            self.spell = spell
            self.name = "Lightning Halo"
            self.description = "Deals lightning damage in a ring each turn"
            self.buff_type = BUFF_TYPE_BLESS
            self.asset = ['status', 'lightning_halo']
            self.stack_type = STACK_REPLACE
            self.damage = self.spell.get_stat("damage")
            self.holy = self.spell.get_stat("holy")
            self.repel = self.spell.get_stat("repel")
            self.global_triggers[EventOnMoved] = lambda evt: on_moved(self, evt)

        def on_moved(self, evt):
            for point in self.spell.get_impacted_tiles(self.owner.x, self.owner.y):
                if point.x == evt.x and point.y == evt.y:
                    evt.unit.deal_damage(self.damage, Tags.Lightning, self.spell)
                    if self.holy:
                        evt.unit.deal_damage(self.damage, Tags.Holy, self.spell)

        def on_advance(self):
            if self.repel:
                for unit in self.owner.level.get_units_in_ball(self.owner, self.radius):
                    if unit is self.owner:
                        continue
                    push(unit, self.owner, 1)
            self.owner.level.queue_spell(self.nova())

        def nova(self):
            self.owner.level.show_effect(0, 0, Tags.Sound_Effect, 'sorcery_ally')
            for p in self.spell.get_impacted_tiles(self.owner.x, self.owner.y):
                self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Lightning, self.spell)
                if self.holy:
                    self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Holy, self.spell)
            yield

    if cls is MercurialVengeance:

        def on_init(self):
            self.owner_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Metallic.color
            self.description = "If an enemy kills this unit, it is inflicted with Mercurize."

        def on_death(self, evt):
            # cast a Mercurize with the summoner's buffs
            if evt.damage_event and are_hostile(evt.damage_event.source.owner, self.owner):
                spell = MercurizeSpell()
                spell.owner = self.owner
                spell.caster = self.owner
                spell.statholder = self.spell.statholder or self.spell.caster
                self.owner.level.act_cast(self.owner, spell, evt.damage_event.source.owner.x, evt.damage_event.source.owner.y, pay_costs=False)

    if cls is MercurizeSpell:

        def on_init(self):
            self.name = "Mercurize"

            self.level = 3
            self.tags = [Tags.Dark, Tags.Metallic, Tags.Enchantment, Tags.Conjuration]

            self.damage = 2

            self.max_charges = 6
            self.duration = 6

            self.range = 8

            self.minion_damage = 10

            self.upgrades['damage'] = (4, 4)
            self.upgrades['duration'] = (10, 3)
            self.upgrades['dark'] = (1, 2, "Morbidity", "Mercurized targets also take [dark] damage.")
            self.upgrades['noxious_aura'] = (1, 5, "Toxic Fumes", "Quicksilver Geists have a noxious aura that deals [2_poison:poison] damage to enemy units within [3_tiles:radius] each turn.")
            self.upgrades['vengeance'] = (1, 5, "Mercurial Vengeance", "When a Quicksilver Geist is killed by an enemy, its killer is affliected with Mercurize.")
            self.upgrades["accumulate"] = (1, 3, "Bioaccumulate", "Each turn, the target is inflicted with [poison] for a duration equal to this spell's [damage] stat, stacking with any existing [poison] the target has.")

    if cls is MercurizeBuff:

        def __init__(self, spell):
            self.spell = spell
            self.damage = spell.get_stat("damage")
            self.dtypes = [Tags.Physical, Tags.Poison]
            if spell.get_stat("dark"):
                self.dtypes.append(Tags.Dark)
            self.accumulate = spell.get_stat("accumulate")
            Buff.__init__(self)

        def on_advance(self):
            for dtype in self.dtypes:
                self.owner.deal_damage(self.damage, dtype, self.spell)
            if not self.accumulate:
                return
            existing = self.owner.get_buff(Poison)
            if existing:
                existing.turns_left += self.damage
            else:
                self.owner.apply_buff(Poison(), self.damage)

        def on_death(self, evt):
            geist = Ghost()
            geist.name = "Mercurial %s" % self.owner.name
            geist.asset_name = "mercurial_geist"
            geist.max_hp = self.owner.max_hp
            geist.tags.append(Tags.Metallic)
            geist.resists[Tags.Ice] = 100
            trample = SimpleMeleeAttack(damage=self.spell.get_stat('minion_damage'))
            geist.spells = [trample]
            if self.spell.get_stat('noxious_aura'):
                geist.buffs.append(DamageAuraBuff(damage=2, damage_type=Tags.Poison, radius=self.spell.get_stat("radius", base=3)))
            if self.spell.get_stat('vengeance'):
                geist.buffs.append(MercurialVengeance(self.spell))
            self.spell.summon(geist, target=self.owner)

    if cls is ArcaneVisionSpell:

        def on_init(self):
            self.name = "Mystic Vision"
            self.range = 0
            self.max_charges = 4
            self.duration = 8
            self.bonus = 5
            self.tags = [Tags.Enchantment, Tags.Arcane]
            self.level = 3

            self.upgrades['duration'] = (8, 2)
            self.upgrades['bonus'] = (5, 4)
            self.upgrades['aura'] = (1, 7, "Vision Aura", "When you cast this spell, apply Mystic Vision to all of your minions, and gain Vision Aura.\nFor the duration, whenever you summon a minion, you automatically apply Mystic Vision to it.")

        def cast_instant(self, x, y):

            bonus = self.get_stat("bonus")

            def buff_func():
                buff = GlobalAttrBonus('range', bonus)
                buff.name = "Mystic Vision"
                return buff
            
            duration = self.get_stat("duration")
            buff = buff_func()
            self.caster.apply_buff(buff, duration)

            if self.get_stat('aura'):
                self.caster.apply_buff(MinionBuffAura(buff_func, lambda unit: True, "Vision Aura", "minions"), duration)

    if cls is PainMirrorSpell:

        def on_init(self):
            self.name = "Pain Mirror"
            self.range = 0
            self.duration = 10

            self.level = 3

            self.max_charges = 5

            self.upgrades['duration'] = (10, 2)
            self.upgrades["false"] = (1, 4, "False Pain", "Damage resisted or blocked by [SH:shields] is now also counted by Pain Mirror.")
            self.upgrades["masochism"] = (1, 3, "Masochism", "Damage inflicted by allies will cause Pain Mirror to deal double damage.")
            self.upgrades["holy"] = (1, 6, "Holy Martyr", "[Dark] damage dealt by Pain Mirror that is resisted or blocked by [SH:shields] will be redealt as [holy] damage.")

            self.tags = [Tags.Dark, Tags.Enchantment]

    if cls is PainMirror:

        def __init__(self, source=None):
            self.source = source
            Buff.__init__(self)

        def on_init(self):
            self.name = "Pain Mirror"
            self.masochism = 0
            self.holy = 0
            if isinstance(self.source, PainMirrorSpell):
                if self.source.get_stat("false"):
                    self.owner_triggers[EventOnPreDamaged] = lambda evt: on_pre_damaged(self, evt)
                else:
                    self.owner_triggers[EventOnDamaged] = self.on_damage
                self.masochism = self.source.get_stat("masochism")
                self.holy = self.source.get_stat("holy")
            else:
                self.owner_triggers[EventOnDamaged] = self.on_damage
            self.color = Tags.Dark.color

        def is_friendly_fire(self, source):
            return hasattr(source, "owner") and not are_hostile(source.owner, self.owner)

        def on_damage(self, event):
            damage = event.damage
            if self.masochism and is_friendly_fire(self, event.source):
                damage *= 2
            self.owner.level.queue_spell(self.reflect(damage))

        def on_pre_damaged(self, evt):
            damage = evt.damage
            if damage <= 0:
                return
            if self.owner.resists[evt.damage_type] < 0 and not self.owner.shields:
                damage *= math.ceil(1 - self.owner.resists[evt.damage_type]/100)
            if self.masochism and is_friendly_fire(self, evt.source):
                damage *= 2
            self.owner.level.queue_spell(self.reflect(damage))

        def reflect(self, damage):
            for u in self.owner.level.get_units_in_los(self.owner):
                if are_hostile(self.owner, u):
                    resisted = 0
                    if self.holy:
                        if u.shields:
                            resisted = damage
                        else:
                            resisted = math.floor(damage*u.resists[Tags.Dark]/100)
                    u.deal_damage(damage, Tags.Dark, self.source or self)
                    if resisted:
                        u.deal_damage(resisted, Tags.Holy, self.source or self)
                    yield

    if cls is SealFate:

        def on_init(self):
            self.name = "Seal Fate"
            self.range = 8
            self.max_charges = 13
            self.tags = [Tags.Enchantment, Tags.Dark]
            self.level = 3
            self.delay = 4

            self.stats.append('delay')

            self.damage = 160
            self.upgrades['range'] = 7
            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Seal Fate can be cast without line of sight.")
            self.upgrades['damage'] = (80, 2)
            self.upgrades['spreads'] = (1, 4, "Spreading Curse", "When Sealed Fate's duration expires, it jumps to a random enemy in line of sight with renewed duration.\nIf an enemy with Sealed Fate dies, the curse jumps to a random enemy in line of sight with its current duration.")

    if cls is SealedFateBuff:

        def __init__(self, spell):
            Buff.__init__(self)
            self.spell = spell
            self.name = "Sealed Fate"
            self.buff_type = BUFF_TYPE_CURSE
            self.asset = ['status', 'sealed_fate']
            self.spreads = self.spell.get_stat("spreads")
            self.damage = self.spell.get_stat("damage")
            self.delay = self.spell.get_stat("delay")
            if self.spreads:
                self.owner_triggers[EventOnDeath] = lambda evt: on_death(self, evt)

        def on_death(self, evt):
            possible_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if u != self.owner and are_hostile(u, self.spell.owner)]
            if possible_targets:
                target = random.choice(possible_targets)
                target.apply_buff(SealedFateBuff(self.spell), self.turns_left)

        def on_advance(self):
            if self.turns_left == 1:
                self.owner.remove_buff(self)
                self.owner.deal_damage(self.damage, Tags.Dark, self.spell)

                if self.spreads:
                    possible_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if u != self.owner and are_hostile(u, self.spell.owner)]
                    if possible_targets:
                        target = random.choice(possible_targets)
                        target.apply_buff(SealedFateBuff(self.spell), self.delay)

    if cls is ShrapnelBlast:

        def on_init(self):
            self.name = "Shrapnel Blast"

            self.tags = [Tags.Fire, Tags.Metallic, Tags.Sorcery]
            self.level = 3
            self.max_charges = 6
            self.radius = 4
            self.range = 7
            self.damage = 12
            self.requires_los = False
            self.num_targets = 16

            self.upgrades['num_targets'] = (12, 3, "More Shrapnel", "[12:num_targets] more shrapnel shards are shot.")
            self.upgrades["channel"] = (1, 7, "Particle Surge", "Shrapnel Blast becomes a channeled spell, and no longer destroys the target wall.\nEach shard now deals damage in a beam between the target tile and its destination.", "behavior")
            self.upgrades['homing'] = (1, 7, "Magnetized Shards", "The shrapnel shards now only target enemies.\nIf no enemies are in the affected area, no more shards will be fired.\nShards not fired do not count as missed; no shards can miss with this upgrade.", "behavior")
            self.upgrades["chasm"] = (1, 4, "Unearth", "This spell can now be cast on chasms.")

        def get_description(self):
            return ("Detonate target wall tile.\n"
                    "The explosion fires [{num_targets}_shards:num_targets] at random tiles in a [{radius}_tile:radius] radius.\n"
                    "Each shard deals [{damage}_physical:physical] damage.\n"
                    "There is a chance to refund a charge of this spell on cast, equal to half the number of shards that miss divided by the total number of shards.").format(**self.fmt_dict())

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            if not self.caster.level.tiles[x][y].is_wall():
                return self.get_stat("chasm") and self.caster.level.tiles[x][y].is_chasm
            return True

        def cast(self, x, y, channel_cast=False):

            channel = self.get_stat('channel')
            if channel and not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)))
                return
            
            damage = self.get_stat('damage')
            homing = self.get_stat("homing")
            num_shards = self.get_stat('num_targets')
            possible_targets = list(self.caster.level.get_points_in_ball(x, y, self.get_stat('radius')))
            shards_missed = 0

            for _ in range(num_shards):
                targets = possible_targets

                if homing:
                    def can_home(t):
                        u = self.caster.level.get_unit_at(t.x, t.y)
                        if not u:
                            return False
                        return are_hostile(self.caster, u)
                    targets = [t for t in possible_targets if can_home(t)]

                if targets:
                    target = random.choice(targets)
                    if channel:
                        missed = True
                        for point in Bolt(self.caster.level, Point(x, y), target, find_clear=False):
                            if self.caster.level.get_unit_at(point.x, point.y):
                                missed = False
                            self.caster.level.deal_damage(point.x, point.y, damage, Tags.Physical, self)
                            yield
                        if missed:
                            shards_missed += 1
                    else:
                        if not self.caster.level.get_unit_at(target.x, target.y):
                            shards_missed += 1
                        self.caster.level.deal_damage(target.x, target.y, damage, Tags.Physical, self)
                    yield

            if not channel:
                self.caster.level.make_floor(x, y)
            
            if random.random() < shards_missed/num_shards/2:
                self.cur_charges = min(self.get_stat("max_charges"), self.cur_charges + 1)

        def get_impacted_tiles(self, x, y):
            return list(self.caster.level.get_points_in_ball(x, y, self.get_stat('radius')))

    if cls is BestowImmortality:

        def on_init(self):

            self.name = "Suspend Mortality"
            self.tags = [Tags.Dark, Tags.Holy, Tags.Enchantment]

            self.lives = 1
            self.duration = 40
            self.level = 3

            self.max_charges = 8

            self.requires_los = False
            self.range = 8

            self.upgrades['lives'] = (3, 2)
            self.upgrades["additive"] = (1, 4, "Additive", "If the target already has reincarnations, you can now cast this spell on the target to add its number of lives to said reincarnations.")
            self.upgrades["eternity"] = (1, 7, "Eternity", "Suspend Mortality now adds reincarnations as a passive buff, which is permanent and cannot be dispelled.")

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return False
            return not unit.has_buff(ReincarnationBuff) or self.get_stat("additive")

        def get_description(self):
            return ("Target unit gains the ability to reincarnate on death [{lives}_times:holy] for [{duration}_turns:duration].\n"
                    "Cannot be cast on targets that already have reincarnations.").format(**self.fmt_dict())

        def cast_instant(self, x, y):

            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return
            
            existing = unit.get_buff(ReincarnationBuff)
            if existing:
                if self.get_stat("additive"):
                    existing.lives += self.get_stat('lives')
                    existing.name = "Reincarnation %i" % existing.lives
                    if self.get_stat("eternity"):
                        existing.buff_type = BUFF_TYPE_PASSIVE
                        existing.turns_left = 0
                    elif existing.turns_left > 0:
                        existing.turns_left = max(existing.turns_left, self.get_stat("duration"))
                return
            
            buff = ReincarnationBuff(self.get_stat('lives'))
            duration = self.get_stat("duration")
            if self.get_stat("eternity"):
                buff.buff_type = BUFF_TYPE_PASSIVE
                duration = 0
            unit.apply_buff(buff, duration)

    if cls is UnderworldPortal:

        def on_init(self):
            self.requires_los = False
            self.range = 99
            self.name = "Underworld Passage"
            self.max_charges = 3
            self.tags = [Tags.Dark, Tags.Sorcery, Tags.Translocation]
            self.level = 3
            self.imps_summoned = 0

            self.upgrades['max_charges'] = 3
            self.upgrades["seeker"] = (1, 3, "Underworld Seeker", "You can now spend 1 extra charge to cast this spell even if you are not next to a chasm.")
            self.upgrades["fauna"] = (1, 3, "Underworld Fauna", "After teleporting, summon a spirit strider, ghost mantis, ghost toad, large ghost worm ball, or ghostly goatia near you, chosen at random.")

        def next_to_chasm(self, center):
            for p in self.caster.level.get_points_in_ball(center.x, center.y, 1.5, diag=True):
                if self.caster.level.tiles[p.x][p.y].is_chasm:
                    return True

        def can_cast(self, x, y):
            if not self.caster.level.can_stand(x, y, self.caster):
                return False
            if not next_to_chasm(self, Point(x, y)):
                return False
            if not next_to_chasm(self, self.caster):
                if not self.get_stat("seeker") or self.cur_charges < 2:
                    return False
            return Spell.can_cast(self, x, y)

        def cast_instant(self, x, y):
            if not next_to_chasm(self, self.caster):
                self.cur_charges -= 1
            self.caster.level.act_move(self.caster, x, y, teleport=True)
            if self.get_stat("fauna"):
                unit_types = [DisplacerBeastGhost, MantisGhost, GhostToad, WormBallGhostly, GoatHeadGhost]
                unit = random.choice(unit_types)()
                apply_minion_bonuses(self, unit)
                self.summon(unit, radius=5)

    if cls is VoidOrbSpell:

        def on_init(self):
            self.name = "Void Orb"
            self.minion_damage = 9
            self.radius = 1
            self.range = 9
            self.max_charges = 4

            self.melt_walls = True

            self.minion_health = 15

            self.element = Tags.Arcane
            
            self.tags = [Tags.Arcane, Tags.Orb, Tags.Conjuration]
            self.level = 3

            self.upgrades['fire'] = (1, 5, "Red Giant", "Void Orb gains [1_radius:radius].\nVoid Orb also deals [fire] damage.")
            self.upgrades["dark"] = (1, 5, "Black Hole", "Each turn, Void Orb pulls all nearby enemies [1_tile:range] toward itself before dealing damage; the pull range is the orb's radius plus 2.\nVoid Orb also deals [dark] damage.")
            self.upgrades['range'] = (5, 2)
            self.upgrades['minion_damage'] = (9, 3)
            self.upgrades['orb_walk'] = (1, 2, "Void Walk", "Targeting an existing Void Orb with another detonates it, dealing its damage and melting walls in a radius equal to the orb's radius plus 2.\nYou are then teleported to that location if possible.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["orb_radius"] = self.get_stat("radius") + self.get_stat("fire")
            return stats

        def on_orb_walk(self, existing):
            # Burst
            x = existing.x
            y = existing.y
            damage = self.get_stat('minion_damage')
            radius = self.get_stat("radius")

            dtypes = [Tags.Arcane]
            if self.get_stat("fire"):
                dtypes.append(Tags.Fire)
                radius += 1
            if self.get_stat("dark"):
                dtypes.append(Tags.Dark)

            for stage in Burst(self.caster.level, Point(x, y), radius + 2, ignore_walls=True):
                for point in stage:
                    unit = self.caster.level.get_unit_at(point.x, point.y)
                    if unit is self.caster or unit is existing:
                        for dtype in dtypes:
                            self.caster.level.show_effect(point.x, point.y, dtype)
                    else:
                        for dtype in dtypes:
                            self.caster.level.deal_damage(point.x, point.y, damage, dtype, self)
                        if self.caster.level.tiles[point.x][point.y].is_wall():
                            self.caster.level.make_floor(point.x, point.y)
                yield
            
            existing.kill()
            if self.caster.level.can_move(self.caster, x, y, teleport=True):
                self.caster.level.act_move(self.caster, x, y, teleport=True)

        def on_make_orb(self, orb):
            orb.resists[Tags.Lightning] = 0
            orb.shields = 3

        def on_orb_move(self, orb, next_point):
            level = orb.level
            damage = self.get_stat('minion_damage')
            radius = self.get_stat("radius")
            
            dtypes = [Tags.Arcane]
            if self.get_stat("fire"):
                dtypes.append(Tags.Fire)
                radius += 1
            if self.get_stat("dark"):
                dtypes.append(Tags.Dark)
                for unit in [unit for unit in level.get_units_in_ball(next_point, radius + 2, diag=True) if are_hostile(self.caster, unit)]:
                    pull(unit, next_point, 1)
            level.queue_spell(boom(self, next_point, radius, damage, dtypes, orb))

        def boom(self, origin, radius, damage, dtypes, orb):
            for stage in Burst(self.caster.level, origin, radius, ignore_walls=True):
                for p in stage:
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if unit is orb or unit is self.caster:
                        for dtype in dtypes:
                            self.caster.level.show_effect(p.x, p.y, dtype)
                    else:
                        # Melt walls
                        if self.caster.level.tiles[p.x][p.y].is_wall():
                            self.caster.level.make_floor(p.x, p.y)
                        for dtype in dtypes:
                            self.caster.level.deal_damage(p.x, p.y, damage, dtype, self)
                yield

        def get_orb_impact_tiles(self, orb):
            return [p for stage in Burst(self.caster.level, orb, self.get_stat("radius") + self.get_stat("fire") + 2, ignore_walls=True) for p in stage]

        def get_description(self):
            return ("Summon a void orb next to the caster.\n"
                    "The orb melts deals [{minion_damage}_arcane:arcane] damage each turn and melts walls in a radius of [{orb_radius}_tiles:radius].\n"
                    "The orb has no will of its own, each turn it will float one tile towards the target.\n"
                    "The orb can be destroyed by lightning damage.").format(**self.fmt_dict())

    if cls is BlizzardSpell:

        def on_init(self):

            self.name = "Blizzard"

            self.tags = [Tags.Enchantment, Tags.Ice, Tags.Nature]
            self.level = 4
            self.max_charges = 4

            self.range = 9
            self.radius = 4

            self.damage = 5
            self.duration = 5

            self.upgrades['damage'] = (5, 2)
            self.upgrades['radius'] = (2, 3)
            self.upgrades['duration'] = (5, 2)
            self.upgrades['requires_los'] = (-1, 3, "Blindcasting", "Blizzard can be cast without line of sight")
            self.upgrades["hailstorm"] = (1, 6, "Hailstorm", "If an affected tile already has a blizzard cloud, the unit on that tile is dealt [ice] damage equal to twice the damage of this spell, and [frozen:freeze] for [1_turn:duration].")

        def cast(self, x, y):
            duration = self.get_stat('duration')
            damage = self.get_stat('damage')
            hailstorm = self.get_stat("hailstorm")
            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
                for p in stage:
                    if hailstorm:
                        existing = self.caster.level.tiles[p.x][p.y].cloud
                        if isinstance(existing, BlizzardCloud):
                            self.caster.level.deal_damage(p.x, p.y, damage*2, Tags.Ice, self)
                            unit = self.caster.level.get_unit_at(p.x, p.y)
                            if unit:
                                unit.apply_buff(FrozenBuff(), 1)
                    cloud = BlizzardCloud(self.caster)
                    cloud.duration = duration
                    cloud.damage = damage
                    cloud.source = self
                    yield self.caster.level.add_obj(cloud, p.x, p.y)

    if cls is BoneBarrageSpell:

        def on_init(self):
            self.name = "Bone Barrage"
            self.range = 14
            self.tags = [Tags.Dark, Tags.Sorcery]
            self.level = 4
            self.max_charges = 7

            self.upgrades['beam'] = (1, 6, "Bone Spears", "Bone Barrage damages all enemies in a beam from the minion to the target.")
            self.upgrades['animation'] = (1, 7, "Shambler Assembly", "Bone Barrage can target empty tiles.\nIf it does, it creates a bone shambler at that tile with HP equal to the damage it would have dealt.\nIf you have the Cursed Bones upgrade, the bone shambler will also deal [dark] damage with its melee attack.")
            self.upgrades["requires_los"] = (-1, 2, "Blindcasting", "Bone Barrage can be cast without line of sight.")
            self.add_upgrade(CursedBones())

        def bolt(self, source, target, damage):
            beam = self.get_stat('beam')

            for point in Bolt(self.caster.level, source, target):
                
                self.caster.level.projectile_effect(point.x, point.y, proj_name='bone_arrow', proj_origin=source, proj_dest=target)
                yield True

                unit = self.caster.level.get_unit_at(point.x, point.y)
                if beam and unit and are_hostile(unit, self.caster):
                    unit.deal_damage(damage, Tags.Physical, self)

            unit = self.caster.level.get_unit_at(target.x, target.y)
            if unit:
                unit.deal_damage(damage, Tags.Physical, self)
            yield False

    if cls is ChimeraFarmiliar:

        def on_init(self):
            self.name = "Chimera Familiar"
            self.tags = [Tags.Chaos, Tags.Conjuration]
            self.level = 4
            self.max_charges = 4
            self.minion_health = 26
            self.minion_damage = 5
            self.minion_range = 5
            self.minion_resists = 50

            self.upgrades['minion_resists'] = (50, 2)
            self.upgrades["minion_health"] = (20, 3)
            self.upgrades["casts"] = (1, 6, "Doublecast", "The chimera now casts 2 of your spells per turn.")
            self.upgrades["morph"] = (1, 6, "Wild Metamorphosis", "The fire lion and lightning snake that the chimera transforms into upon reaching 0 HP can now also cast your spells.\nThe fire lion can only cast your [fire] and [chaos] spells.\nThe lightning snake can only cast your [lightning] and [chaos] spells.\nEach of them can only cast 1 spell per turn.")
            self.add_upgrade(ChimeraFamiliarSelfSufficiency())

            self.casts = 1
            self.must_target_walkable = True
            self.must_target_empty = True

        def get_description(self):
            return ("Summon a Chimera Familiar, which has [{minion_health}_HP:minion_health], and [{minion_resists}:damage] resistance to [fire], [lightning], and [physical].\n"
                    "Each turn, the chimera will cast [{casts}:num_targets] of your [fire], [lightning], or [chaos] [sorcery] spells that can be cast from its tile, preferring spells with the highest [max_charges:max_charges], consuming 1 charge from the spells copied. This also counts as you casting the spell.\n"
                    "If the chimera cannot cast your spells, it will use [fire] and [lightning] ranged attacks with [{minion_damage}:minion_damage] damage and [{minion_range}:minion_range] range.").format(**self.fmt_dict())

        def get_lion(self):
            unit = RedLion()
            unit.name = "Lion Familiar"
            apply_minion_bonuses(self, unit)
            if self.get_stat("morph"):
                unit.spells.insert(0, ChimeraFamiliarSpellConduit(lightning=False))
            bonus = self.get_stat("minion_resists") - self.minion_resists
            for tag in [Tags.Lightning, Tags.Physical]:
                unit.resists[tag] = bonus
            return unit

        def get_snake(self):
            unit = GoldenSnake()
            unit.name = "Snake Familiar"
            apply_minion_bonuses(self, unit)
            if self.get_stat("morph"):
                unit.spells.insert(0, ChimeraFamiliarSpellConduit(fire=False))
            bonus = self.get_stat("minion_resists") - self.minion_resists
            for tag in [Tags.Fire, Tags.Physical]:
                unit.resists[tag] = bonus
            return unit

        def cast_instant(self, x, y):
            chimera = ChaosChimera()
            chimera.asset_name = "chaos_chimera"
            chimera.name = "Chimera Familiar"
            apply_minion_bonuses(self, chimera)
            chimera.spells.insert(0, ChimeraFamiliarSpellConduit(casts=self.get_stat("casts")))
            minion_resists = self.get_stat("minion_resists")
            for tag in [Tags.Fire, Tags.Lightning, Tags.Physical]:
                chimera.resists[tag] = minion_resists
            chimera.buffs[0].spawner = lambda: get_lion(self)
            chimera.buffs[1].spawner = lambda: get_snake(self)
            self.summon(chimera, Point(x, y))

    if cls is ConductanceSpell:

        def on_init(self):
            self.name = "Conductance"
            self.tags = [Tags.Lightning, Tags.Enchantment]
            self.level = 4
            self.max_charges = 12
            self.resistance_debuff = 50
            self.duration = 10
            self.cascade_range = 4
            self.can_target_empty = False

            self.upgrades['cascade_range'] = (4, 4)
            self.upgrades['resistance_debuff'] = (50, 2)
            self.upgrades['max_charges'] = (6, 2)

        def can_cast(self, x, y):
            return Spell.can_cast(self, x, y)

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(curr_module.ConductanceBuff(self), self.get_stat("duration"))

        def get_description(self):
            return ("Curse an enemy with the essence of conductivity.\n"
                    "That enemy loses [{resistance_debuff}_lightning:lightning] resistance.\n"
                    "Whenever [lightning] damage is dealt to the target, deal the same amount of [lightning] damage, before counting resistances, to another random enemy in a [{cascade_range}_tile:cascade_range] burst. New targets with Conductance are prioritized, and a new target without Conductance is inflicted with Conductance for half the duration of conductance on the original target.\n"
                    "A target can only be affected once per turn.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is ConjureMemories:

        def on_init(self):
            self.tags = [Tags.Arcane, Tags.Conjuration, Tags.Enchantment]
            self.name = "Conjure Memories"
            self.max_charges = 3
            self.range = 0
            self.level = 4
            self.num_summons = 2
            self.duration = 10

            self.upgrades['max_charges'] = (3, 3)
            self.upgrades["duration"] = (10, 3)
            self.upgrades["num_summons"] = (2, 5, "Num Summons", "[2:num_summons] more dead allies are re-summoned when the effect expires.")

        def get_description(self):
            return ("Memorize all allies you summon for the next [{duration}_turns:duration].\n"
                    "When this effect expires, re-summon [{num_summons}:num_summons] of the memorized allies that are not currently alive.\n"
                    "Casting this spell again ends the previous instance of the effect early, replacing it with a new instance that inherits the memorized allies of the previous instance that have not been re-summoned.\n"
                    "This does not allow you to bring allies from one realm to the next, or duplicate minions that you can otherwise only summon one of.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            buff = ConjureMemoriesBuff(self)
            existing = self.caster.get_buff(ConjureMemoriesBuff)
            if existing:
                buff.allies = existing.allies
                self.caster.remove_buff(existing)
            self.caster.apply_buff(buff, self.get_stat("duration"))

    if cls is DeathGazeSpell:

        def on_init(self):
            self.name = "Death Gaze"
            self.range = 0
            self.tags = [Tags.Dark, Tags.Sorcery, Tags.Eye]
            self.level = 4
            self.max_charges = 10
            self.damage = 4
            self.element = Tags.Dark

            self.upgrades['damage'] = (4, 3)
            self.upgrades['max_charges'] = (6, 2)
            self.upgrades['vampiric'] = (1, 4, "Vampiric Gaze", "Each allied unit heals for 100% of the damage it causes")

    if cls is EssenceFlux:

        def on_init(self):
            self.name = "Essence Flux"
            self.tags = [Tags.Arcane, Tags.Chaos, Tags.Enchantment]

            self.max_charges = 12
            self.level = 4
            self.range = 7

            self.upgrades['max_charges'] = (6, 2)
            self.upgrades["selective"] = (1, 3, "Selective Flux", "When targeting an ally with this spell, the resistances of enemies are not swapped.\nWhen targeting an enemy with this spell, the resistances of allies are not swapped.\nIn both cases, both allies and enemies are treated as the same group of units.")

        def cast(self, x, y):
            points = self.get_impacted_tiles(x, y)
            selective = self.get_stat("selective")
            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return
            for p in points:
                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit:
                    if selective and are_hostile(target, unit):
                        continue

                    old_resists = unit.resists.copy()
                    for e1, e2 in [
                        (Tags.Fire, Tags.Ice),
                        (Tags.Lightning, Tags.Physical),
                        (Tags.Dark, Tags.Holy),
                        (Tags.Poison, Tags.Arcane)]:

                        if old_resists[e1] == 0 and old_resists[e2] == 0:
                            continue

                        if old_resists[e1] == old_resists[e2]:
                            continue

                        unit.resists[e1] = old_resists[e2]
                        unit.resists[e2] = old_resists[e1]

                        color = e1.color if old_resists[e1] > old_resists[e2] else e2.color

                        etype = random.choice([e1, e2])
                        self.caster.level.show_effect(unit.x, unit.y, Tags.Debuff_Apply, fill_color=color)
                        yield

    if cls is SummonFieryTormentor:

        def on_init(self):
            self.name = "Fiery Tormentor"

            self.tags = [Tags.Dark, Tags.Fire, Tags.Conjuration]

            self.minion_health = 34
            self.minion_damage = 7
            self.minion_duration = 50
            self.minion_range = 2

            self.radius = 4

            self.max_charges = 7
            self.level = 4

            self.range = 7

            self.upgrades['minion_damage'] = (3, 2)
            self.upgrades['minion_health'] = (10, 2)
            self.upgrades['radius'] = (2, 3)
            self.upgrades['frostfire'] = (1, 3, "Frostfire Tormentor", "Summons a frostfire tormentor instead.", "variant")
            self.upgrades['ghostfire'] = (1, 3, "Ghostfire Tormentor", "Summons a ghostfire tormentor instead.", "variant")
            self.add_upgrade(FieryTormentorRemorse())

            self.must_target_walkable = True
            self.must_target_empty = True

    if cls is SummonIceDrakeSpell:

        def on_init(self):
            self.name = "Ice Drake"
            self.range = 4
            self.max_charges = 2
            self.tags = [Tags.Ice, Tags.Conjuration, Tags.Dragon]
            self.level = 4
            
            self.minion_range = 7
            self.minion_health = 45
            self.minion_damage = 8
            self.breath_damage = 7
            self.duration = 2

            self.upgrades['minion_health'] = (25, 2)
            self.upgrades['duration'] = (3, 2, "Freeze Duration")
            self.upgrades['dragon_mage'] = (1, 5, "Dragon Mage", "Summoned Ice Drakes can cast Icicle with a 3 turn cooldown.\nThis Icicle gains all of your upgrades and bonuses.")

        def cast_instant(self, x, y):
            drake = IceDrake()

            drake.max_hp = self.get_stat('minion_health')
            drake.spells[0].damage = self.get_stat('breath_damage')
            drake.spells[0].range = self.get_stat('minion_range')
            drake.spells[0].duration = self.get_stat('duration')
            drake.spells[1].damage = self.get_stat('minion_damage')

            if self.get_stat('dragon_mage'):
                dchill = Icicle()
                dchill.statholder = self.caster
                dchill.max_charges = 0
                dchill.cur_charges = 0
                dchill.cool_down = 3
                drake.spells.insert(1, dchill)

            self.summon(drake, Point(x, y))

    if cls is LightningFormSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 3
            self.name = "Lightning Form"
            
            self.tags = [Tags.Lightning, Tags.Enchantment, Tags.Translocation]
            self.level = 4

            self.upgrades['max_charges'] = (3, 2)
            self.upgrades["ice"] = (1, 4, "Ice Infusion", "Now also gives [100_ice:ice] resistance and functions with [ice] spells.")
            self.upgrades["cloud"] = (1, 3, "Cloud Form", "When inside a thunderstorm cloud, Lightning Form will not run out, and you will automatically generate a thunderstorm cloud within [3_tiles:radius] every turn.\nIf you have Ice Infusion, this upgrade also works with blizzard clouds.")

        def cast(self, x, y):
            self.caster.apply_buff(curr_module.LightningFormBuff(self))
            yield

    if cls is StormSpell:

        def on_init(self):
            self.max_charges = 4
            self.name = "Lightning Storm"
            self.duration = 10
            self.range = 9
            self.radius = 4
            self.damage = 12
            self.strikechance = 50
            
            self.upgrades['strikechance'] = (25, 2)
            self.upgrades['requires_los'] = (-1, 3, "Blindcasting", "Lightning Storm can be cast without line of sight")
            self.upgrades['radius'] = (2, 2)
            self.upgrades['damage'] = 7
            self.upgrades["twice"] = (1, 5, "Strike Twice", "If an affected tile already has a thunderstorm cloud, the unit on that tile is dealt [lightning] damage equal to the damage of this spell.\nIf you have the Strikechance upgrade, there is a 50% chance to deal damage again.")

            self.tags = [Tags.Lightning, Tags.Nature, Tags.Enchantment]
            self.level = 4

        def cast(self, x, y):
            twice = self.get_stat("twice")
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            strikechance = self.get_stat('strikechance') / 100.0
            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
                for p in stage:
                    if twice:
                        existing = self.caster.level.tiles[p.x][p.y].cloud
                        if isinstance(existing, StormCloud):
                            self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)
                            if strikechance > 0.5 and random.random() < 0.5:
                                self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)
                    cloud = StormCloud(self.caster)
                    cloud.duration = duration
                    cloud.damage = damage
                    cloud.strikechance = strikechance
                    cloud.source = self
                    yield self.caster.level.add_obj(cloud, p.x, p.y)

    if cls is OrbControlSpell:

        def on_init(self):
            self.name = "Orb Control"

            self.tags = [Tags.Sorcery, Tags.Orb]

            self.range = 9

            self.level = 4
            self.requires_los = False
            self.max_charges = 11

            self.upgrades["max_charges"] = (9, 4)
            self.upgrades["dupe"] = (1, 5, "Orb Duplication", "When casting this spell, every allied [orb] will instead continue moving in its original path, but cast a copy of its corresponding [orb] spell targeting the target of this spell.\nThere is a chance to consume a charge of the corresponding spell, equal to the pre-existing orb's remaining duration divided by its maximum duration.\nThe spell will not be copied if it tries but cannot consume a charge, in which case the orb will be redirected to the target tile.")

        def cast_instant(self, x, y, channel_cast=False):

            dupe = self.get_stat("dupe")

            for u in self.caster.level.units:

                if u.team != self.caster.team:
                    continue
                buff = u.get_buff(OrbBuff)
                if not buff:
                    continue
                
                if dupe:
                    spell = buff.spell
                    spend_charge = (random.random() < u.turns_to_death/(spell.get_stat("range") - 1))
                    if not spend_charge or spell.cur_charges > 0:
                        spell_copy = type(spell)()
                        spell_copy.statholder = spell.caster
                        spell_copy.owner = u
                        spell_copy.caster = u
                        spell_copy.range = RANGE_GLOBAL
                        spell_copy.cur_charges = 0
                        spell_copy.max_charges = 0
                        self.caster.level.act_cast(u, spell_copy, x, y, pay_costs=False)
                        # Change caster to the player so that the duplicated orbs don't hurt the player
                        spell_copy.owner = spell.owner
                        spell_copy.caster = spell.caster
                        if spend_charge:
                            spell.cur_charges -= 1
                        continue

                path = self.caster.level.get_points_in_line(u, Point(x, y))[1:]
                u.turns_to_death = len(path)
                buff.dest = Point(x, y)

    if cls is Permenance:

        def on_init(self):
            self.max_charges = 4
            self.duration = 20
            self.name = "Permanence"
            self.tags = [Tags.Enchantment]
            self.level = 4
            self.range = 0
            self.upgrades['duration'] = (20, 3)
            self.upgrades["retroactive"] = (1, 3, "Retroactive", "When you cast this spell, all friendly units' buffs and enemies' debuffs are extended by [5_turns:duration].\nEach buff or debuff can only be extended this way once.")

        def cast_instant(self, x, y):
            self.caster.apply_buff(PermenanceBuff(), self.get_stat('duration'))
            if self.get_stat("retroactive"):
                for unit in list(self.caster.level.units):
                    buff_type = BUFF_TYPE_CURSE if are_hostile(self.caster, unit) else BUFF_TYPE_BLESS
                    for buff in unit.buffs:
                        if buff.buff_type == buff_type and buff.turns_left and not hasattr(buff, "permanence_extended"):
                            buff.turns_left += 5
                            buff.permanence_extended = True

    if cls is PuritySpell:

        def on_init(self):
            self.name = "Purity"

            self.duration = 6
            self.level = 4
            self.max_charges = 4

            self.upgrades['duration'] = (6, 3)
            self.upgrades['max_charges'] = (4, 3)
            self.upgrades["morale"] = (1, 5, "Pure Morale", "All buffs received while Purity is active will have their durations increased by 50%, rounded down.")
            self.range = 0

            self.tags = [Tags.Holy, Tags.Enchantment]

        def extend_buff(evt):
            if evt.buff.buff_type == BUFF_TYPE_BLESS:
                evt.buff.turns_left = math.floor(evt.buff.turns_left*1.5)

        def cast_instant(self, x, y):
            buffs = list(self.caster.buffs)
            for b in buffs:
                if b.buff_type == BUFF_TYPE_CURSE:
                    self.caster.remove_buff(b)
            buff = PurityBuff()
            if self.get_stat("morale"):
                buff.owner_triggers[EventOnBuffApply] = extend_buff
            self.caster.apply_buff(buff, self.get_stat('duration'))

    if cls is PyrostaticPulse:

        def on_init(self):
            self.name = "Pyrostatic Pulse"
            self.level = 4

            self.damage = 8

            self.max_charges = 8
            self.range = 8
            self.tags = [Tags.Fire, Tags.Lightning, Tags.Sorcery]

            self.upgrades['range'] = (4, 2)
            self.upgrades['damage'] = (4, 3)
            self.upgrades['max_charges'] = (8, 2)
            self.upgrades["channel"] = (1, 6, "Channeling", "Pyrostatic Pulse becomes a channeled spell, and gains [1_damage:damage] per turn channeled.")

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage and [{damage}_lightning:lightning] damage in a beam and tiles adjacent to the beam.").format(**self.fmt_dict())

        def cast(self, x, y, channel_cast=False):
            if self.get_stat('channel') and not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)))
                return
            if channel_cast:
                self.caster.apply_buff(PyrostaticSurgeBuff())
            yield self.cast_instant(x, y)

        def cast_instant(self, x, y):
            damage = self.get_stat("damage")
            for p in self.get_impacted_tiles(x, y):
                self.caster.level.deal_damage(p.x, p.y, damage, Tags.Fire, self)
                self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)

    if cls is SearingSealSpell:

        def on_init(self):
            self.name = "Searing Seal"
            
            self.tags = [Tags.Fire, Tags.Enchantment]
            self.level = 4
            self.max_charges = 6
            self.range = 0
            self.duration = 6

            self.upgrades['max_charges'] = (6, 2)
            self.upgrades['duration'] = (6, 1)
            self.upgrades["purefire"] = (1, 6, "Purefire Seal", "[Holy] and [arcane] damage can now also fuel Searing Seal, but with half the efficiency of [fire] damage.")

    if cls is SearingSealBuff:

        def on_damage(self, evt):
            if evt.damage_type == Tags.Fire:
                self.charges += evt.damage
            if self.spell.get_stat("purefire") and evt.damage_type in [Tags.Holy, Tags.Arcane]:
                self.charges += evt.damage//2

    if cls is SummonSiegeGolemsSpell:

        def on_init(self):
            self.name = "Siege Golems"
            self.tags = [Tags.Fire, Tags.Conjuration, Tags.Metallic]
            self.level = 4
            self.max_charges = 3
            self.range = 5

            self.minion_damage = 30
            self.minion_range = 15
            self.radius = 3

            self.minion_health = 25
            self.num_summons = 3

            self.upgrades['radius'] = (2, 4)
            self.upgrades['num_summons'] = (3, 3)
            self.upgrades['minion_range'] = (7, 2)
            self.upgrades["heal"] = (1, 6, "Phoenix Ashes", "Each inferno cannon's attack and self-destruct will now heal allies instead of damaging them.\nThe wizard and inferno cannons will not be healed, but will also not take damage.")
            self.upgrades["demo"] = (1, 4, "Wall Demolition", "Each inferno cannon's attack and self-destruct will now destroy walls.")
            self.upgrades["phase"] = (1, 2, "Phase Operator", "Siege golems gain the ability to teleport next to nearby inferno cannons.")

        def cannon(self):
            unit = Unit()
            unit.tags = [Tags.Construct, Tags.Metallic, Tags.Fire]
            unit.name = "Inferno Cannon"
            unit.stationary = True

            unit.resists[Tags.Physical] = 50
            unit.resists[Tags.Fire] = -100

            unit.spells = [InfernoCannonBlast(damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range'), radius=self.get_stat('radius'), heal=self.get_stat("heal"), demo=self.get_stat("demo"))]

            unit.buffs.append(InfernoCannonExplosion(damage=self.get_stat('minion_damage'), radius=self.get_stat('radius'), heal=self.get_stat("heal"), demo=self.get_stat("demo")))

            unit.max_hp = self.get_stat("minion_health", base=18)
            unit.source = self
            return unit

        def golem(self):
            golem = SiegeOperator(self.cannon)
            golem.spells[2].range = 3
            if self.get_stat("phase"):
                golem.spells[2] = SiegeGolemTeleport(3)
            golem.spells[1].heal = math.ceil(self.get_stat("minion_health", base=18)/9)
            golem.spells[1].description = "Repair %d damage to a %s" % (golem.spells[1].heal, golem.spells[1].siege_name)
            golem.name = "Golem Siege Mechanic"
            golem.asset_name = "golem_siege"
            golem.max_hp = 25
            golem.tags = [Tags.Metallic, Tags.Construct]
            apply_minion_bonuses(self, golem)

            return golem

    if cls is FeedingFrenzySpell:

        def on_init(self):
            self.max_charges = 3
            self.name = "Sight of Blood"
            self.duration = 15
            self.range = RANGE_GLOBAL
            self.can_target_empty = False
            self.shot_cooldown = 3

            self.minion_health = 22
            self.minion_damage = 5
            self.minion_range = 5
            self.bloodlust_bonus = 2

            self.upgrades['duration'] = (15, 3)
            self.upgrades["shot_cooldown"] = (-1, 4)
            self.upgrades["bloodlust_bonus"] = (1, 3)
            self.upgrades["feeding_frenzy"] = (1, 2, "Feeding Frenzy", "On each activation, each allied unit in line of sight of the target that has [bloodlust:demon] has a chance to gain another stack of [bloodlust:demon].\nThe chance is equal to the percentage of the target's missing HP.")
            self.upgrades["unending"] = (1, 5, "Unending Bloodlust", "When the target dies, the curse is applied to another random enemy in line of sight for its remaining duration.")
            
            self.tags = [Tags.Nature, Tags.Enchantment, Tags.Conjuration, Tags.Eye]
            self.level = 4

        def get_impacted_tiles(self, x, y):
            return Spell.get_impacted_tiles(self, x, y)

        def cast(self, x, y):
            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return
            target.apply_buff(SightOfBloodBuff(self), self.get_stat("duration"))
            yield

        def can_cast(self, x, y):
            return Spell.can_cast(self, x, y)

        def get_description(self):
            return ("Curse a target in line of sight to attract bloodthirsty predators for [{duration}_turns:duration].\n"
                    "Every [{shot_cooldown}_turns:shot_cooldown], summon a blood vulture near the target, which is a [nature] [demon] minion with [{minion_health}_HP:minion_health] and attacks that deal [{minion_damage}_physical:physical] damage.\n"
                    "The blood vulture's melee attack grants itself [10_turns:duration] of [bloodlust:demon] on hit, which increases all of its damage by [{bloodlust_bonus}:minion_damage]. It also has a dive attack with [{minion_range}_range:minion_range] and [3_turns:cooldown] cooldown.\n"
                    "This curse is not considered an [eye] buff, but its activation interval uses the [shot_cooldown:shot_cooldown] stat of [eye] spells.").format(**self.fmt_dict())

    if cls is ShieldSiphon:

        def on_init(self):
            self.name = "Siphon Shields"

            self.max_charges = 3
            self.level = 4

            self.tags = [Tags.Arcane, Tags.Enchantment]
            self.range = 0

            self.shield_steal = 1

            self.upgrades['shield_burn'] = (1, 4, "Shield Burn", "Deal [5_fire:fire] damage per shield stolen.\nEach is dealt as a separate hit, and benefits from damage bonuses.")
            self.upgrades['shield_steal'] = (4, 1, "Shield Steal", "Up to 4 more [SH:shields] are stolen from each enemy.")
            self.upgrades["mirage"] = (1, 3, "Shield Mirage", "If you already have [20_SH:shields], then every additional [3_SH:shields] stolen will summon a shield mirage near you.\nShield mirages are stationary, flying [arcane] minions with fixed 1 HP, [3_SH:shields], and no resistances.")

        def cast(self, x, y):

            shield_steal = self.get_stat("shield_steal")
            shield_burn = self.get_stat("shield_burn")
            mirage = self.get_stat("mirage")
            damage = self.get_stat("damage", base=5)

            total = 0
            targets = [u for u in self.caster.level.get_units_in_los(self.caster) if are_hostile(u, self.caster)]
            for u in targets:

                if not u.shields:
                    continue

                stolen = min(shield_steal, u.shields)

                self.caster.level.show_effect(u.x, u.y, Tags.Shield_Expire)			
                u.shields -= stolen

                if shield_burn:
                    for _ in range(stolen):
                        u.deal_damage(damage, Tags.Fire, self)

                total += stolen

                yield

            if total:

                extra = self.caster.shields + total - 20
                if extra > 0 and mirage:
                    for _ in range(extra//3):
                        unit = Unit()
                        unit.name = "Shield Mirage"
                        unit.asset = ["UnderusedOptions", "Units", "shield_mirage"]
                        unit.max_hp = 1
                        unit.tags = [Tags.Arcane]
                        unit.resists[Tags.Poison] = 0
                        unit.shields = 3
                        unit.stationary = True
                        unit.flying = True
                        self.summon(unit, radius=5, sort_dist=False)
                
                self.caster.add_shields(total)

            yield

    if cls is StormNova:

        def on_init(self):
            self.name = "Storm Burst"
            self.level = 4
            self.tags = [Tags.Ice, Tags.Lightning, Tags.Sorcery]

            self.max_charges = 4

            self.damage = 10
            self.duration = 3
            self.radius = 5
            self.range = 0

            self.upgrades['duration'] = (2, 3)
            self.upgrades['clouds'] = (1, 2, "Cloud Nova", "The nova leaves storm clouds and blizzards behind")
            self.upgrades['radius'] = (2, 3)

        def get_description(self):
            return ("Unleashes a [{radius}_tile:radius] burst of storm energy.\n"
                    "Each tile in the burst takes [{damage}_ice:ice] damage and [{damage}_lightning:lightning] damage.\n"
                    "Units dealt ice damage are [frozen] for [{duration}_turns:duration].\n"
                    "Units dealt lightning damage are [stunned] for [{duration}_turns:duration].").format(**self.fmt_dict())

        def cast(self, x, y):
            damage = self.get_stat('damage')
            damage_bonus = damage - self.damage
            duration = self.get_stat('duration')
            duration_bonus = duration - self.duration
            clouds = self.get_stat('clouds')
            for stage in Burst(self.caster.level, Point(self.caster.x, self.caster.y), self.get_stat('radius')):
                for p in stage:
                    if (p.x, p.y) == (self.caster.x, self.caster.y):
                        continue
                    lightning_dealt = self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)
                    ice_dealt = self.caster.level.deal_damage(p.x, p.y, damage, Tags.Ice, self)
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if unit:
                        if ice_dealt:
                            unit.apply_buff(FrozenBuff(), duration)
                        if lightning_dealt:
                            unit.apply_buff(Stun(), duration)
                    if clouds:
                        if random.choice([True, False]):
                            cloud = BlizzardCloud(self.caster)
                            cloud.damage += damage_bonus
                        else:
                            cloud = StormCloud(self.caster)
                            cloud.damage += 2*damage_bonus
                        cloud.duration += duration_bonus
                        cloud.source = self
                        self.caster.level.add_obj(cloud, p.x, p.y)
                yield

    if cls is SummonStormDrakeSpell:

        def on_init(self):
            self.name = "Storm Drake"
            self.range = 4
            self.max_charges = 2
            self.tags = [Tags.Lightning, Tags.Conjuration, Tags.Dragon]
            self.level = 4
            self.minion_health = 45
            self.minion_damage = 8
            self.breath_damage = StormDrake().spells[0].damage
            self.minion_range = 7
            self.strikechance = 50
            self.upgrades['minion_health'] = (25, 2)
            self.upgrades["strikechance"] = (25, 2)
            self.upgrades["surge"] = (1, 3, "Cloud Surge", "If an affected tile already has a thunderstorm cloud, the unit on that tile is dealt [lightning] damage equal to the storm drake's breath damage.\nIf you have the Strikechance upgrade, there is a 50% chance to deal damage again.")
            self.upgrades['dragon_mage'] = (1, 5, "Dragon Mage", "Summoned Storm Drakes can cast Lightning Bolt with a 3 turn cooldown.\nThis Lightning Bolt gains all of your upgrades and bonuses.")
        
            self.must_target_empty = True

        def cast_instant(self, x, y):
            drake = StormDrake()
            drake.max_hp = self.get_stat('minion_health')
            drake.spells[0] = SummonedStormDrakeBreath(self)
            drake.spells[1].damage = self.get_stat('minion_damage')
            if self.get_stat('dragon_mage'):
                lbolt = LightningBoltSpell()
                lbolt.statholder = self.caster
                lbolt.max_charges = 0
                lbolt.cur_charges = 0
                lbolt.cool_down = 3
                drake.spells.insert(1, lbolt)
            self.summon(drake, Point(x, y))

        def get_description(self):
            return ("Summon a storm drake at target square.\n"
                    "Storm drakes have [{minion_health}_HP:minion_health], fly, and have [100_lightning:lightning] resist.\n"
                    "Storm drakes have a breath weapon which creates storm clouds that have a [{strikechance}%_chance:strikechance] to deal [{breath_damage}_lightning:lightning] damage.\n"
                    "Storm drakes have a melee attack which deals [{minion_damage}_physical:physical] damage.").format(**self.fmt_dict())

    if cls is IceWall:

        def on_init(self):
            self.name = "Wall of Ice"
            self.minion_health = 36
            self.minion_duration = 15
            self.minion_range = 3
            self.minion_damage = 5

            self.level = 4
            self.max_charges = 6

            self.tags = [Tags.Conjuration, Tags.Ice]

            self.range = 7
            self.radius = 1

            self.upgrades['radius'] = (1, 2)
            self.upgrades['minion_range'] = (3, 3)
            self.upgrades['minion_damage'] = (5, 3)
            self.add_upgrade(IceWallForcefulConstruction())

        def get_impacted_tiles(self, x, y): 
            points = self.caster.level.get_perpendicular_line(self.caster, Point(x, y), length=self.get_stat('radius'))
            if not self.get_stat("forceful"):
                points = [p for p in points if self.caster.level.can_walk(p.x, p.y, check_unit=True)]
            return points

        def cast(self, x, y):

            minion_damage = self.get_stat('minion_damage')
            minion_range = self.get_stat('minion_range')
            minion_health = self.get_stat('minion_health')
            minion_duration = self.get_stat('minion_duration')
            forceful = self.get_stat("forceful")
            damage = self.get_stat("damage", base=22)
            duration = self.get_stat("duration", base=3)

            for p in self.get_impacted_tiles(x, y):
                elemental = Unit()
                elemental.name = "Ice Elemental"
                snowball = SimpleRangedAttack(damage=minion_damage, damage_type=Tags.Ice, range=minion_range)
                snowball.name = "Snowball"
                elemental.spells.append(snowball)
                elemental.max_hp = minion_health
                elemental.stationary = True
                
                elemental.tags = [Tags.Elemental, Tags.Ice]
                
                elemental.resists[Tags.Physical] = 50
                elemental.resists[Tags.Fire] = -100
                elemental.resists[Tags.Ice] = 100
                
                elemental.turns_to_death = minion_duration

                if forceful:
                    self.caster.level.make_floor(p.x, p.y)
                    self.caster.level.deal_damage(p.x, p.y, damage, Tags.Ice, self)
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if unit:
                        unit.apply_buff(FrozenBuff(), duration)

                self.summon(elemental, target=p, radius=0)
                yield

    if cls is WatcherFormBuff:

        def __init__(self, spell):
            self.spell = spell
            Stun.__init__(self)

        def on_applied(self, owner):
            self.arcane = self.spell.get_stat("arcane")
            self.transform_asset_name = "watcher" if not self.arcane else "void_watcher"
            self.stack_type = STACK_TYPE_TRANSFORM
            self.resists[Tags.Physical] = 100
            self.resists[Tags.Lightning] = 100
            self.resists[Tags.Fire] = 100
            self.resists[Tags.Poison] = 100
            if self.arcane:
                self.resists[Tags.Arcane] = 100
            self.color = Tags.Lightning.color
            self.name = "Watcher Form"
            self.damage = self.spell.get_stat("damage")
            if not self.owner.is_player_controlled:
                self.damage = self.damage//5

        def on_advance(self):

            possible_targets = self.owner.level.units
            possible_targets = [t for t in possible_targets if self.owner.level.are_hostile(t, self.owner)]
            if not self.arcane:
                possible_targets = [t for t in possible_targets if self.owner.level.can_see(t.x, t.y, self.owner.x, self.owner.y)]

            if possible_targets:
                random.shuffle(possible_targets)
                target = max(possible_targets, key=lambda t: distance(t, self.owner))
                self.owner.level.queue_spell(self.shoot(target))
            else:
                # Show the effect fizzling
                self.owner.deal_damage(0, Tags.Lightning, self)

        def shoot(self, target):
            points = self.owner.level.get_points_in_line(Point(self.owner.x, self.owner.y), Point(target.x, target.y), find_clear=not self.arcane)[1:]
            for p in points:
                self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Lightning, self.spell)
                if self.arcane:
                    if self.owner.level.tiles[p.x][p.y].is_wall():
                        self.owner.level.make_floor(p.x, p.y)
                    self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Arcane, self.spell)
                yield

    if cls is WatcherFormSpell:

        def on_init(self):
            self.name = "Watcher Form"
            self.range = 0
            self.max_charges = 5
            self.duration = 5
            self.damage = 40
            self.element = Tags.Lightning
            self.tags = [Tags.Enchantment, Tags.Lightning, Tags.Arcane, Tags.Eye]
            self.level = 4

            self.upgrades['damage'] = (30, 3)
            self.upgrades['max_charges'] = (3, 2)
            self.upgrades['duration'] = 3
            self.upgrades["arcane"] = (1, 6, "Void Watcher", "Gain [100_arcane:arcane] resist.\nWatcher Form now instead targets the furthest unit from the caster regardless of line of sight, melts through walls, and also deals [arcane] damage.")

        def cast_instant(self, x, y):
            self.caster.apply_buff(WatcherFormBuff(self), self.get_stat('duration'))

        def get_description(self):
            return ("Each turn, fire a lightning bolt at the farthest enemy in line of sight dealing [{damage}_lightning:lightning] damage in a beam.\n"
                    "Gain [100_fire:fire], [100_lightning:lightning], [100_physical:physical], and [100_poison:poison] resist.\n"
                    "The uer cannot move or cast spells for the duration. If the caster is not you, this spell only deals 20% damage.\n"
                    "Lasts [{duration}_turns:duration].\n").format(**self.fmt_dict())

    if cls is BallLightning:

        def on_init(self):
            self.name = "Ball Lightning"

            self.num_targets = 3
            self.minion_damage = 6
            self.minion_health = 12

            self.level = 5
            self.range = 9
            self.max_charges = 4

            self.radius = 4

            self.tags = [Tags.Orb, Tags.Lightning, Tags.Conjuration]

            self.upgrades['num_targets'] = (2, 3)
            self.upgrades['range'] = (5, 2)
            self.upgrades['minion_damage'] = (10, 5)
            self.upgrades['orb_walk'] = (1, 6, "Lightning Barrage", "Targeting an existing lightning orb causes it to shoot a number of beams equal to twice its [num_targets:num_targets], each targeting a random enemy in line of sight.\nAn enemy can be hit by more than one beam.")

        def get_description(self):
            return ("Summon a lighting orb next to the caster.\n"
                    "Each turn the orb fires [{num_targets}_beams:num_targets] of electricity at random enemy units in line of sight. The beams deal [{minion_damage}_lightning:lightning] damage.\n"
                    "The orb has no will of its own, each turn it will float one tile towards the target.\n"
                    "The orb can be destroyed by arcane damage.").format(**self.fmt_dict())

        def on_make_orb(self, orb):
            orb.resists[Tags.Arcane] = 0

        def on_orb_walk(self, orb):
            damage = self.get_stat('minion_damage')
            for _ in range(2*self.get_stat("num_targets")):
                targets = [u for u in orb.level.get_units_in_los(orb) if are_hostile(u, self.caster)]
                if not targets:
                    return
                for p in orb.level.get_points_in_line(orb, random.choice(targets))[1:]:
                    orb.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)
                yield

    if cls is CantripCascade:

        def on_init(self):
            self.name = "Cantrip Cascade"
            self.level = 5
            self.tags = [Tags.Arcane, Tags.Sorcery]
            self.max_charges = 3
            self.angle = math.pi / 6
            self.range = 7
            self.upgrades['max_charges'] = (3, 2)
            self.upgrades['range'] = (3, 3)
            self.upgrades["focus"] = (1, 4, "Focused Cascade", "Each cantrip has a chance to be cast an additional time.\nThis chance is equal to 1 divided by the number of enemies in the affected area at the time of casting this spell.")

        def cast_instant(self, x, y):
            units = [self.caster.level.get_unit_at(p.x, p.y) for p in self.get_impacted_tiles(x, y)]
            enemies = [u for u in units if u and are_hostile(u, self.caster)]
            spells = [s for s in self.caster.spells if s.level == 1 and Tags.Sorcery in s.tags]

            chance = 1/len(enemies) if self.get_stat("focus") else 0

            pairs = list(itertools.product(enemies, spells))

            random.shuffle(pairs)

            for enemy, spell in pairs:
                self.caster.level.act_cast(self.caster, spell, enemy.x, enemy.y, pay_costs=False)
                if random.random() < chance:
                    self.caster.level.act_cast(self.caster, spell, enemy.x, enemy.y, pay_costs=False)

    if cls is IceWind:

        def on_init(self):
            self.name = "Chill Wind"

            self.level = 5
            self.tags = [Tags.Ice, Tags.Sorcery]

            self.max_charges = 2

            self.damage = 21
            self.duration = 6
            self.radius = 1

            self.range = RANGE_GLOBAL
            self.requires_los = False

            self.upgrades['max_charges'] = (2, 3)
            self.upgrades['damage'] = (14, 2)
            self.upgrades["radius"] = (1, 5, "Width", "Chill Wind now affects a line [5_tiles:radius] wide.")
        
        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["width"] = self.get_stat("radius")*2 + 1
            return stats

        def get_description(self):
            return ("Deals [{damage}_ice:ice] damage and inflicts [{duration}_turns:duration] of [frozen] on units in a [{width}_tile:radius] wide line perpendicular to the caster.").format(**self.fmt_dict())

        def get_impacted_tiles(self, x, y):
            radius = self.get_stat("radius")
            line = self.caster.level.get_perpendicular_line(self.caster, Point(x, y))
            result = set()
            for p in line:
                for q in self.caster.level.get_points_in_rect(p.x - radius, p.y - radius, p.x + radius, p.y + radius):
                    result.add(q)
            return result

    if cls is FaeCourt:

        def on_init(self):
            self.name = "Fae Court"
            self.num_summons = 5
            self.max_charges = 2
            self.heal = 5
            self.minion_range = 4
            self.minion_duration = 15
            self.minion_health = 9
            self.shields = 1

            self.minion_damage = 4

            self.range = 0

            self.level = 5

            self.tags = [Tags.Nature, Tags.Arcane, Tags.Conjuration]

            self.upgrades['num_summons'] = (5, 4)
            self.upgrades['heal'] = (8, 3)
            self.upgrades['shields'] = (1, 2)
            self.upgrades['summon_queen'] = (1, 7, "Summon Queen", "A fae queen is summoned as well")
            self.upgrades['glass_fae'] = (1, 6, "Glass Faery", "Summon glass faeries instead of normal ones.")

    if cls is SummonFloatingEye:

        def on_init(self):
            self.name = "Floating Eye"
            self.minion_duration = 4
            self.tags = [Tags.Eye, Tags.Arcane, Tags.Conjuration]
            self.level = 5
            self.max_charges = 6

            ex = FloatingEye()

            self.minion_health = ex.max_hp
            self.shields = ex.shields

            self.minion_duration = 16

            self.upgrades['minion_duration'] = (16, 2)
            self.upgrades['max_charges'] = (2, 3)
            self.upgrades["independent"] = (1, 3, "Independent Eye", "The floating eye now has an attack with unlimited range that deals [2_arcane:arcane] damage.\nThis attack benefits from [minion_damage:minion_damage] bonuses.")

            self.must_target_empty = True

        def cast_instant(self, x, y):
            eye = FloatingEye()
            if not self.get_stat("independent"):
                eye.spells = []
            apply_minion_bonuses(self, eye)
            eye.buffs.append(FloatingEyeBuff(self))

            self.summon(eye, Point(x, y))

    if cls is FlockOfEaglesSpell:

        def on_init(self):

            self.name = "Flock of Eagles"

            self.minion_health = 18
            self.minion_damage = 6
            self.minion_range = 5
            self.num_summons = 4
            self.shields = 0

            self.max_charges = 2

            self.upgrades['num_summons'] = (2, 3)
            self.upgrades['shields'] = (2, 4)
            self.upgrades['thunderbirds'] = (1, 4, "Thunderbirds", "Summon thunderbirds instead of eagles.\nThunderbirds deal and are immune to [lightning] damage.", "species")
            self.upgrades["ravens"] = (1, 5, "White Ravens", "Summon white ravens instead of eagles.\nWhite ravens resist [dark] damage, and their melee attacks inflict [3_turns:duration] of [blind].", "species")

            self.range = 0

            self.level = 5
            self.tags = [Tags.Conjuration, Tags.Nature, Tags.Holy]

        def get_description(self):
            return ("Summons [{num_summons}_eagles:num_summons] near the caster.\n"
                    "Eagles have [{minion_health}_HP:minion_health] and can fly.\n"
                    "Eagles have a melee attack which deals [{minion_damage}_physical:physical] damage, and a dive attack with the same damage and [{minion_range}_range:minion_range].").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            minion_damage = self.get_stat('minion_damage')
            minion_range = self.get_stat('minion_range')
            minion_health = self.get_stat('minion_health')
            shields = self.get_stat('shields')
            thunderbird = self.get_stat('thunderbirds')
            raven = self.get_stat("ravens")
            for _ in range(self.get_stat('num_summons')):
                eagle = Unit()
                eagle.name = "Eagle"

                dive = LeapAttack(damage=minion_damage, range=minion_range)
                peck = SimpleMeleeAttack(damage=minion_damage)

                dive.name = 'Dive'
                peck.name = 'Claw'

                eagle.spells.append(peck)
                eagle.spells.append(dive)
                eagle.max_hp = minion_health

                eagle.flying = True
                eagle.tags = [Tags.Living, Tags.Holy, Tags.Nature]

                eagle.shields = shields

                if thunderbird:
                    for s in eagle.spells:
                        s.damage_type = Tags.Lightning
                    eagle.tags.append(Tags.Lightning)
                    eagle.resists[Tags.Lightning] = 100
                    eagle.name = "Thunderbird"
                elif raven:
                    eagle.spells[0] = SimpleMeleeAttack(damage=minion_damage, buff=BlindBuff, buff_duration=3)
                    eagle.tags.append(Tags.Dark)
                    eagle.resists[Tags.Dark] = 50
                    eagle.name = "White Raven"
                    eagle.asset = ["UnderusedOptions", "Units", "white_raven"]

                self.summon(eagle, Point(x, y))

    if cls is SummonIcePhoenix:

        def on_init(self):
            self.name = "Ice Phoenix"
            self.level = 5
            self.max_charges = 2
            self.tags = [Tags.Conjuration, Tags.Ice, Tags.Holy]

            self.minion_health = 74
            self.minion_damage = 9
            self.minion_range = 4
            self.lives = 1
            self.radius = 6

            self.upgrades['lives'] = (2, 3, "Reincarnations", "The phoenix will reincarnate 2 more times")
            self.upgrades['minion_damage'] = (9, 2)
            self.add_upgrade(IcePhoenixFreeze())
            self.add_upgrade(IcePhoenixIcyJudgment())

            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["explosion_damage"] = self.get_stat("minion_damage", base=25)
            return stats

        def get_description(self):
            return ("Summon an ice phoenix.\n"
                    "The phoenix has [{minion_health}_HP:minion_health], flies, and reincarnates [{lives}_times:holy] upon death.\n"
                    "The phoenix has a ranged attack which deals [{minion_damage}_ice:ice] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "When the phoenix dies, it explodes in a [{radius}_tile:radius] radius, dealing [{explosion_damage}_ice:ice] damage to enemies and granting [2_SH:shields] to allies.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            phoenix = Unit()
            phoenix.max_hp = self.get_stat('minion_health')
            phoenix.name = "Ice Phoenix"

            phoenix.tags = [Tags.Ice, Tags.Holy]

            phoenix.buffs.append(curr_module.IcePhoenixBuff(self))
            phoenix.buffs.append(ReincarnationBuff(self.get_stat('lives')))

            phoenix.flying = True

            phoenix.resists[Tags.Ice] = 100
            phoenix.resists[Tags.Dark] = -50

            phoenix.spells.append(SimpleRangedAttack(damage=self.get_stat('minion_damage'), range=self.get_stat('minion_range'), damage_type=Tags.Ice))
            self.summon(phoenix, target=Point(x, y))

    if cls is MegaAnnihilateSpell:

        def on_init(self):
            self.damage = 99
            self.max_charges = 3
            self.name = "Mega Annihilate"
            
            self.tags = [Tags.Chaos, Tags.Sorcery]
            self.level = 5

            self.cascade_range = 0
            self.arcane = 0
            self.dark = 0

            self.upgrades['cascade_range'] =  (4, 3, 'Cascade', 'Hits from Mega Annihilate will jump to nearby targets if the main target is killed or if targeting an empty tile.\nThis ignores line of sight.')
            self.upgrades['dark'] =  (1, 2, 'Dark Annihilation', 'Mega Annihilate deals an additional [dark] damage hit')
            self.upgrades['arcane'] =  (1, 2, 'Arcane Annihilation', 'Mega Annihilate deals an additional [arcane] damage hit')
            self.upgrades['damage'] = (99, 4)

    if cls is RingOfSpiders:

        def on_init(self):

            self.name = "Ring of Spiders"
            self.duration = 10
            self.range = 8

            self.level = 5
            self.max_charges = 2

            self.damage = 0
            
            self.minion_health = 14
            self.minion_damage = 2

            self.upgrades['damage'] = (32, 2, "Damage", "Deal [poison] damage to the target tile.")
            self.upgrades['minion_health'] = (10, 3)
            self.upgrades['aether_spiders'] = (1, 6, "Aether Spiders", "Summon aether spiders instead of regular spiders.", "species")
            self.upgrades['steel_spiders'] = (1, 6, "Steel Spiders", "Summon steel spiders instead of regular spiders.", "species")

            self.tags = [Tags.Nature, Tags.Conjuration]

        def cast(self, x, y):
            
            aether = self.get_stat('aether_spiders')
            steel = self.get_stat("steel_spiders")
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')

            for p in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(p.x, p.y)

                rank = max(abs(p.x - x), abs(p.y - y))

                if rank == 0:
                    if damage:
                        self.caster.level.deal_damage(x, y, damage, Tags.Poison, self)
                elif rank == 1:
                    if not unit and self.caster.level.tiles[p.x][p.y].can_walk:
                        if aether:
                            spider = PhaseSpider()
                        elif steel:
                            spider = SteelSpider()
                        else:
                            spider = GiantSpider()
                        spider.spells[0].damage = self.get_stat('minion_damage', base=spider.spells[0].damage)
                        spider.max_hp = self.get_stat('minion_health', base=spider.max_hp)
                        self.summon(spider, p)
                    if unit:
                        unit.apply_buff(Poison(), duration)
                else:
                    if not unit and not self.caster.level.tiles[p.x][p.y].is_wall():
                        cloud = SpiderWeb()
                        cloud.owner = self.caster
                        self.caster.level.add_obj(cloud, *p)
                    if unit:
                        unit.apply_buff(Stun(), 1)
                yield

    if cls is SlimeformSpell:

        def on_init(self):
            self.name = "Slime Form"
            self.tags = [Tags.Arcane, Tags.Enchantment, Tags.Conjuration]
            self.level = 5
            self.max_charges = 2
            self.range = 0
            self.duration = 8

            self.upgrades['fire_slimes'] = (1, 3, "Fire Slime", "Summon fire slime instead of green slimes.", "slime color")
            self.upgrades['ice_slimes'] = (1, 3, "Ice Slime", "Summon ice slime instead of green slimes.", "slime color")
            self.upgrades['void_slimes'] = (1, 4, "Void Slime", "Summon void slime instead of green slimes.", "slime color")
            self.upgrades["natural_slimes"] = (1, 4, "Natural Slime", "Summoned green slimes become [nature] minions.\nSummoned green slimes gain [10_HP:minion_health] and [7_damage:minion_damage].", "slime color")
            self.upgrades["minion_health"] = (10, 3)
            self.add_upgrade(SlimeFormAdvancedSlimes())
            self.upgrades['duration'] = (10, 4)

            self.minion_health = 10
            self.minion_damage = 3

        def get_description(self):
            return ("Assume slime form for [{duration}_turns:duration].\n"
                    "Gain [50_physical:physical] resist while in slime form.\n"
                    "Gain [100_poison:poison] resist while in slime form.\n"
                    "Summon a friendly slime each turn while in slime form.\n"
                    "Slimes have [{minion_health}_HP:minion_health], have a 50% chance each turn to gain 10% max HP, and split into two slimes upon reaching twice their starting HP.\n"
                    "Slimes have a melee attack which deals [{minion_damage}_poison:poison] damage.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            self.caster.apply_buff(curr_module.SlimeFormBuff(self), self.get_stat('duration'))

    if cls is DragonRoarSpell:

        def on_init(self):
            self.name = "Dragon Roar"
            self.tags = [Tags.Dragon, Tags.Nature, Tags.Enchantment]
            self.max_charges = 2
            self.level = 6
            self.range = 0

            self.hp_bonus = 25
            self.damage = 12

            self.duration = 25

            self.upgrades['hp_bonus'] = (20, 3)
            self.upgrades['max_charges'] = (1, 2)
            self.upgrades["retroactive"] = (1, 4, "Retroactive", "You now gain Dragon Aura when you cast this spell, during which all [dragon] minions you summon will automatically gain Dragon Roar for the remaining duration.")

            self.cooldown_reduction = 1
            self.stats.append('cooldown_reduction')

        def cast_instant(self, x, y):

            duration = self.get_stat("duration")
            
            if self.get_stat("retroactive"):
                buff = MinionBuffAura(lambda: DragonRoarBuff(self), lambda unit: Tags.Dragon in unit.tags, "Dragon Aura", "dragon minions")
                buff.stack_type = STACK_INTENSITY
                self.caster.apply_buff(buff, duration)
                return

            for unit in self.caster.level.units:
                if Tags.Dragon not in unit.tags:
                    continue
                if are_hostile(unit, self.caster):
                    continue
                unit.apply_buff(DragonRoarBuff(self), duration)

    if cls is SummonGoldDrakeSpell:

        def on_init(self):
            self.name = "Gold Drake"
            self.range = 4
            self.max_charges = 2
            self.tags = [Tags.Holy, Tags.Conjuration, Tags.Dragon]
            self.level = 6

            self.minion_health = 45
            self.minion_damage = 8
            self.breath_damage = 9
            self.minion_range = 7

            self.upgrades['minion_health'] = (25, 2)
            self.upgrades['metal'] = (1, 4, "True Gold", "The gold drake becomes a [metallic] unit, gaining [100_lightning:lightning], [100_ice:ice], [50_fire:fire], and [50_physical:physical] resistances.")
            self.upgrades['dragon_mage'] = (1, 5, "Dragon Mage", "Summoned Gold Drakes can cast Heavenly Blast with a 3 turn cooldown.\nThis Heavenly Blast gains all of your upgrades and bonuses.")
            self.add_upgrade(GoldGuardian())

            self.must_target_empty = True

        def cast_instant(self, x, y):
            drake = GoldDrake()
            drake.team = self.caster.team
            drake.max_hp = self.get_stat('minion_health')
            drake.spells[0].damage = self.get_stat('breath_damage')
            drake.spells[0].range = self.get_stat('minion_range')
            drake.spells[1].damage = self.get_stat('minion_damage')

            if self.get_stat("metal"):
                drake.tags.append(Tags.Metallic)
            
            if self.get_stat('dragon_mage'):
                hlight = HolyBlast()
                hlight.statholder = self.caster
                hlight.max_charges = 0
                hlight.cur_charges = 0
                hlight.cool_down = 3
                drake.spells.insert(1, hlight)

            self.summon(drake, Point(x, y))

    if cls is ImpGateSpell:

        def on_init(self):
            self.name = "Imp Swarm"
            self.range = 0
            self.max_charges = 3
            self.duration = 5
            self.tags = [Tags.Enchantment, Tags.Conjuration, Tags.Chaos]
            self.level = 6

            self.minion_health = 5
            self.minion_damage = 4
            self.minion_duration = 11
            self.minion_range = 3
            self.num_summons = 2

            self.upgrades['minion_range'] = (2, 3)
            self.upgrades['num_summons'] = (1, 2)
            self.upgrades['minion_duration'] = (7, 2)
            self.upgrades['minion_damage'] = (5, 4)

            self.upgrades['metalswarm'] = (1, 6, "Metal Swarm", "Imp swarm summons furnace imps, copper imps, and tungsten imps instead of fire, spark, and iron imps.", "swarm")
            self.upgrades['fireswarm'] = (1, 6, "Fire Swarm", "Imp swarm summons firestorm imps, chaos imps, and ash imps instead of fire, spark, and iron imps.", "swarm")
            self.upgrades['megaswarm'] = (1, 7, "Mega Swarm", "Imp swarm summons giant imps instead of normal sized ones", "swarm")

            self.imp_choices = [FireImp, SparkImp, IronImp]

        def get_imp_choices(self):
            if self.get_stat('metalswarm'):
                return [CopperImp, FurnaceImp, TungstenImp]
            elif self.get_stat('fireswarm'):
                return [FirestormImp, ChaosImp, AshImp]
            elif self.get_stat('megaswarm'):
                return [SparkImpGiant, FireImpGiant, IronImpGiant]
            else:
                return self.imp_choices

    if cls is MysticMemory:

        def on_init(self):
            self.tags = [Tags.Arcane]
            self.name = "Mystic Memory"
            self.max_charges = 1
            self.level = 6
            self.range = 0

            self.upgrades['max_charges'] = (1, 2)
            self.add_upgrade(RecentMemory())

        def cast_instant(self, x, y):
            spells = [s for s in self.caster.spells if s is not self and s.cur_charges == 0]
            if not spells:
                return
            
            recent = self.caster.get_buff(RecentMemory)
            if recent and recent.recent_spell and recent.recent_spell.cur_charges == 0:
                choice = recent.recent_spell
            else:
                choice = random.choice(spells)
            choice.cur_charges = choice.get_stat('max_charges')

    if cls is SearingOrb:

        def on_init(self):
            self.name = "Searing Orb"

            self.minion_damage = 3
            self.minion_health = 8
            self.max_charges = 3
            self.level = 6
            self.range = 9

            self.radius = 3

            self.tags = [Tags.Fire, Tags.Orb, Tags.Conjuration]

            self.upgrades['range'] = (5, 2)
            self.upgrades['melt_walls'] = (1, 4, "Matter Melting", "Searing Orb can melt and be cast through walls")
            self.upgrades["safety"] = (1, 2, "Safety", "Searing Orb no longer damages your minions.")

        def on_orb_move(self, orb, next_point):
            damage = self.get_stat('minion_damage')
            safety = self.get_stat("safety")
            for u in orb.level.get_units_in_los(next_point):
                if u is self.caster or u is orb:
                    continue
                if safety and not are_hostile(u, self.caster):
                    continue
                u.deal_damage(damage, Tags.Fire, self)

    if cls is KnightBuff:
        
        def on_applied(self, owner):
            self.max_hp = self.owner.max_hp
            self.shields = self.owner.shields

        def on_init(self):
            self.name = "Bound Knight"
            self.owner_triggers[EventOnDamaged] = lambda evt: on_damaged(self, evt)

        def on_damaged(self, evt):
            if self.owner.cur_hp <= 0:
                self.owner.cur_hp = 1
                for buff in list(self.owner.buffs):
                    if buff.buff_type == BUFF_TYPE_CURSE:
                        self.owner.remove_buff(buff)
                self.owner.max_hp = max(self.owner.max_hp, self.max_hp)
                self.owner.shields = max(self.owner.shields, self.shields)
                self.owner.deal_damage(-self.owner.max_hp, Tags.Heal, self)
                self.summoner.deal_damage(40, Tags.Holy, self)

    if cls is SummonKnights:

        def on_init(self):
            self.name = "Knightly Oath"
            self.level = 7
            self.tags = [Tags.Conjuration, Tags.Holy]

            self.minion_health = 90

            self.max_charges = 2
            self.minion_damage = 7
            
            self.range = 0
            
            # Purely for shrine bonuses
            self.minion_range = 6

            self.upgrades['void_court'] = (1, 5, "Void Court", "Summon only void knights.  Summon a void champion as well.", "court")
            self.upgrades['storm_court'] = (1, 5, "Storm Court","Summon only storm knights.  Summon a storm champion as well.", "court")
            self.upgrades['chaos_court'] = (1, 5, "Chaos Court", "Summon only chaos knights.  Summon a chaos champion as well.", "court")
            self.upgrades["promotion"] = (1, 6, "Promotion", "Each non-champion knight will be promoted to a champion after [20_turns:duration].")
            self.upgrades['max_charges'] = (1, 3)

        def get_description(self):
            return ("Summon a void knight, a chaos knight, and a storm knight.\n"
                    "Each knight has [{minion_health}_HP:minion_health], various resistances, and an arsenal of unique magical abilities.\n"
                    "Whenever a knight is about to die to damage, the caster takes [40_holy:holy] damage to fully heal the knight, restore all [SH:shields], and remove all debuffs.").format(**self.fmt_dict())

        def cast(self, x, y):

            knights = [VoidKnight(), ChaosKnight(), StormKnight()]
            if self.get_stat('void_court'):
                knights = [Champion(VoidKnight()), VoidKnight(), VoidKnight(), VoidKnight()]
            if self.get_stat('storm_court'):
                knights = [Champion(StormKnight()), StormKnight(), StormKnight(), StormKnight()]
            if self.get_stat('chaos_court'):
                knights = [Champion(ChaosKnight()), ChaosKnight(), ChaosKnight(), ChaosKnight()]

            promotion = self.get_stat("promotion")
            def promote(knight):
                unit = Champion(knight)
                apply_minion_bonuses(self, unit)
                return unit

            for u in knights:
                if promotion:
                    spawner = None
                    if u.name == "Chaos Knight":
                        spawner = lambda: promote(ChaosKnight())
                    elif u.name == "Void Knight":
                        spawner = lambda: promote(VoidKnight())
                    elif u.name == "Storm Knight":
                        spawner = lambda: promote(StormKnight())
                    if spawner:
                        u.buffs.append(MatureInto(spawner, 20))
                apply_minion_bonuses(self, u)
                u.buffs.append(KnightBuff(self.caster))
                self.summon(u)
                yield

    if cls is MulticastBuff:

        def on_init(self):
            self.name = "Multicast"
            self.description = "Whenever you cast a sorcery spell, copy it."
            self.can_copy = True
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.copies = self.spell.get_stat("copies")
            self.adaptive = self.spell.get_stat("adaptive")

        def on_spell_cast(self, evt):
            if evt.spell.item:
                return
            if Tags.Sorcery not in evt.spell.tags:
                return

            if self.can_copy:
                self.can_copy = False
                copies = self.copies
                if self.adaptive:
                    if evt.spell.level == 5 or evt.spell.level == 4:
                        copies += 1
                    elif evt.spell.level == 3 or evt.spell.level == 2:
                        copies += 2
                    elif evt.spell.level == 1:
                        copies += 3
                for _ in range(copies):
                    if evt.spell.can_cast(evt.x, evt.y):
                        evt.caster.level.act_cast(evt.caster, evt.spell, evt.x, evt.y, pay_costs=False)
                evt.caster.level.queue_spell(self.reset())

    if cls is MulticastSpell:

        def on_init(self):
            self.name = "Multicast"
            self.duration = 3
            self.copies = 1
            self.max_charges = 3
            self.multi_conjure = 0
            self.upgrades['copies'] = (1, 4)
            self.upgrades['duration'] = (4, 3)
            self.upgrades['max_charges'] = (4, 2)
            self.upgrades["adaptive"] = (1, 6, "Adaptive Copy", "Level 5 and 4 spells are now copied 1 additional time.\nLevel 3 and 2 spells are now copied 2 additional times.\nLevel 1 spells are now copied 3 additional times.")
            self.range = 0
            self.level = 7
            self.tags = [Tags.Enchantment, Tags.Arcane]

    if cls is SpikeballFactory:

        def on_init(self):
            self.name = "Spikeball Factory"
            self.tags = [Tags.Metallic, Tags.Conjuration]

            self.level = 7

            self.max_charges = 1

            self.minion_health = 40
            self.range = 0

            self.upgrades['manufactory'] = (1, 6, "Manufactory", "Surrounds the initially summoned gates with another layer of gates")
            self.upgrades['copper'] = (1, 7, "Copper Spikeballs", "Summons copper spikeballs instead of normal ones")
            self.upgrades['minion_health'] = (20, 3)
            self.upgrades['max_charges'] = (1, 3)
            self.upgrades["forceful"] = (1, 4, "Forceful Construction", "Wall and chasm tiles in the affected area are converted to floor tiles, and units tossed up to [3_tiles:radius] away, before summoning the spikeball gates.")

        def cast(self, x, y):
            forceful = self.get_stat("forceful")
            for p in self.get_impacted_tiles(x, y):
                if forceful:
                    self.caster.level.make_floor(p.x, p.y)
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if unit:
                        randomly_teleport(unit, 3, requires_los=True)
                gate = MonsterSpawner(self.spikeball)
                apply_minion_bonuses(self, gate)
                self.summon(gate, p, radius=0)
                yield

        def get_impacted_tiles(self, x, y):
            points = set()
            forceful = self.get_stat("forceful")
            point = Point(self.caster.x, self.caster.y)
            for p in self.owner.level.get_adjacent_points(point, filter_walkable=not forceful, check_unit=not forceful):
                points.add(p)
            if self.get_stat('manufactory'):
                for p in list(points):
                    for q in self.owner.level.get_adjacent_points(p, filter_walkable=not forceful, check_unit=not forceful):
                        if q != point:
                            points.add(q)
            return points

    if cls is WordOfIce:

        def on_init(self):
            self.name = "Word of Ice"
            self.level = 7
            self.tags = [Tags.Ice, Tags.Word]
            self.max_charges = 1
            self.duration = 5
            self.damage = 50
            self.range = 0

            self.hp_threshold = 50

            self.upgrades['duration'] = (4, 3)
            self.upgrades['max_charges'] = (1, 2)
            self.upgrades["hp_threshold"] = (30, 5)

        def cast(self, x, y):
            units = [u for u in self.caster.level.units if are_hostile(u, self.caster)]
            random.shuffle(units)
            duration = self.get_stat("duration")
            damage = self.get_stat('damage')
            hp_threshold = self.get_stat("hp_threshold")
            for u in units:
                if u.cur_hp < hp_threshold:
                    u.apply_buff(FrozenBuff(), duration)
                if Tags.Fire in u.tags:
                    u.deal_damage(damage, Tags.Ice, self)
                if random.random() < .3:
                    yield

        def get_description(self):
            return ("All non [ice] immune enemies under [{hp_threshold}:damage] current HP are [frozen] for [{duration}_turns:duration].\n"
                    "Deals [{damage}_ice:ice] damage to all [fire] units.").format(**self.fmt_dict())

    if cls is ArcaneCredit:

        def on_init(self):
            self.name = "Arcane Credit"
            self.owner_triggers[EventOnSpellCast] = self.on_cast
            self.color = Tags.Arcane.color
            self.description = "Every non [arcane] spell has a 50% chance to refund 1 charge on cast."

        def on_cast(self, evt):
            if Tags.Arcane not in evt.spell.tags and random.random() < 0.5:
                evt.spell.cur_charges += 1
                evt.spell.cur_charges = min(evt.spell.cur_charges, evt.spell.get_stat('max_charges'))

    if cls is ArcaneAccountant:

        def on_init(self):
            self.tags = [Tags.Arcane]
            self.level = 4
            self.name = "Arcane Accounting"
            self.duration = 2
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def get_description(self):
            return "Whenever you cast the last charge of an [arcane] spell, your non [arcane] spell have a 50%% chance to refund 1 charge on cast for [%i_turns:duration], starting from the next turn." % self.get_stat("duration")

        def on_spell_cast(self, evt):
            if Tags.Arcane in evt.spell.tags and evt.spell.cur_charges == 0:
                self.owner.apply_buff(ArcaneCredit(), self.get_stat("duration") + 1)

    if cls is Hibernation:

        def on_advance(self):
            for unit in [unit for unit in self.owner.level.units if unit is not self.owner and not are_hostile(self.owner, unit)]:
                if Tags.Living in unit.tags or Tags.Nature in unit.tags:
                    unit.apply_buff(HibernationBuff())

        def get_description(self):
            return ("Your [living] and [nature] minions gain [75_ice:ice] resistance, [freeze] for [3_turns:duration] upon taking [ice] damage, and heal for [15_HP:heal] each turn while [frozen].\n"
                    "For every [100_ice:ice] resistance a minion has above 100, it will be healed each turn for the same amount. An excess of less than 100 instead has a chance to heal the minion.").format(**self.fmt_dict())

    if cls is HibernationBuff:

        def on_pre_advance(self):
            if Tags.Living not in self.owner.tags and Tags.Nature not in self.owner.tags:
                self.owner.remove_buff(self)
                return
            if self.owner.has_buff(FrozenBuff):
                self.owner.deal_damage(-15, Tags.Heal, self)
            elif self.owner.resists[Tags.Ice] > 100:
                amount = self.owner.resists[Tags.Ice] - 100
                while amount > 100:
                    self.owner.deal_damage(-15, Tags.Heal, self)
                    amount -= 100
                if random.random() < amount/100:
                    self.owner.deal_damage(-15, Tags.Heal, self)

    if cls is HolyWater:

        def on_init(self):
            self.name = "Holy Water"
            self.description = "Whenever a [frozen] enemy takes [holy] damage, all allies in line of sight gain [1_SH:shields], up to a max of [5:shields].\nAll affected allies then deal [2_holy:holy] or [2_ice:ice] damage in a radius equal to the number of [SH:shields] they have.\nThis damage is fixed, and cannot be increased using shrines, skills, or buffs.\nThis skill cannot trigger itself."
            self.level = 5
            self.global_triggers[EventOnDamaged] = self.on_damage
            self.tags = [Tags.Holy, Tags.Ice]

        def on_damage(self, evt):
            if not are_hostile(self.owner, evt.unit):
                return
            if evt.damage_type != Tags.Holy:
                return
            if evt.source is self:
                return
            if not evt.unit.has_buff(FrozenBuff):
                return

            for u in self.owner.level.get_units_in_los(evt.unit):
                if are_hostile(u, self.owner):
                    continue
                if u.shields < 5:
                    u.add_shields(1)
                damage_aura(self, u, u.shields)
        
        def damage_aura(self, origin, radius):

            effects_left = 7

            for unit in self.owner.level.get_units_in_ball(origin, radius):
                if not self.owner.level.are_hostile(self.owner, unit):
                    continue
                unit.deal_damage(2, random.choice([Tags.Holy, Tags.Ice]), self)
                effects_left -= 1

            # Show some graphical indication of this aura if it didnt hit much
            points = self.owner.level.get_points_in_ball(origin.x, origin.y, radius)
            points = [p for p in points if not self.owner.level.get_unit_at(p.x, p.y)]
            random.shuffle(points)
            for _ in range(effects_left):
                if not points:
                    return
                p = points.pop()
                self.owner.level.deal_damage(p.x, p.y, 0, random.choice([Tags.Holy, Tags.Ice]), self)

    if cls is UnholyAlliance:

        def on_init(self):
            self.name = "Unholy Alliance"
            self.description = ("If you have a [holy] minion, your [undead] and [demon] minions gain [7_damage:damage] and [100_holy:holy] resistance.\n"
                                "If you have an [undead] or [demon] minion, your [holy] minions gain [7_damage:damage].")
            self.level = 5
            self.tags = [Tags.Dark, Tags.Holy]

            self.holy_minions = []
            self.unholy_minions = []

        def on_advance(self):

            self.holy_minions = []
            self.unholy_minions = []
            units = [unit for unit in self.owner.level.units if not are_hostile(unit, self.owner)]
            for unit in units:
                if Tags.Holy in unit.tags:
                    self.holy_minions.append(unit)
                if Tags.Undead in unit.tags or Tags.Demon in unit.tags:
                    self.unholy_minions.append(unit)

            for unit in units:
                if Tags.Holy in unit.tags:
                    buff = unit.get_buff(UnholyAllianceHolyBuff)
                    if buff and not self.unholy_minions:
                        unit.remove_buff(buff)
                    elif self.unholy_minions and not buff:
                        unit.apply_buff(UnholyAllianceHolyBuff())
                if Tags.Undead in unit.tags or Tags.Demon in unit.tags:
                    buff = unit.get_buff(UnholyAllianceUnholyBuff)
                    if buff and not self.holy_minions:
                        unit.remove_buff(buff)
                    elif self.holy_minions and not buff:
                        unit.apply_buff(UnholyAllianceUnholyBuff())


    if cls is WhiteFlame:

        def on_init(self):
            self.name = "White Flame"
            self.tags = [Tags.Fire]
            self.level = 5
            self.damage = 18
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def get_description(self):
            return "Whenever you cast a [fire] spell at a tile other than your own, the unit on that tile loses [100_fire:fire] resistance, which is removed at the beginning of your next turn.\nThen deal [%d_fire:fire] damage to the targeted tile." % self.get_stat('damage')

        def on_spell_cast(self, evt):
            if Tags.Fire not in evt.spell.tags:
                return
            # dont white flame yourself with eye of fire or whatever
            if evt.x == self.owner.x and evt.y == self.owner.y:
                return
            self.owner.apply_buff(RemoveBuffOnPreAdvance(WhiteFlameDebuff))
            unit = self.owner.level.get_unit_at(evt.x, evt.y)
            if unit:
                unit.apply_buff(WhiteFlameDebuff())
            self.owner.level.deal_damage(evt.x, evt.y, self.get_stat('damage'), Tags.Fire, self)

    if cls is Teleblink:

        def on_init(self):
            self.tags = [Tags.Arcane, Tags.Nature, Tags.Translocation]
            self.level = 5
            self.name = "Glittering Dance"
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.casts = 0

            self.minion_damage = 4
            self.heal = 5

            self.minion_range = 4
            self.minion_duration = 10
            self.minion_health = 9
            self.shields = 1
            self.num_summons = 2
            self.cast_last = False

    if cls is Hypocrisy:

        def on_init(self):
            self.name = "Hypocrisy"
            self.description = ("Whenever you cast a [dark] spell, if your next spell is a [holy] spell of equal or lower level, that spell refunds 1 charge on cast.\n"
                                "Whenever you cast a [holy] spell, if your next spell is a [dark] spell of equal or lower level, that spell refunds 1 charge on cast.\n"
                                "A spell that benefitted from Hypocrisy will not let your next spell benefit from Hypocrisy.")
            self.tags = [Tags.Dark, Tags.Holy]
            self.level = 5
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def on_spell_cast(self, evt):
            if evt.spell.level < 1:
                return
            if Tags.Dark in evt.spell.tags:
                for buff in self.owner.buffs:
                    if isinstance(buff, HypocrisyStack) and buff.tag == Tags.Dark and buff.level >= evt.spell.level:
                        return
            if Tags.Holy in evt.spell.tags:
                for buff in self.owner.buffs:
                    if isinstance(buff, HypocrisyStack) and buff.tag == Tags.Holy and buff.level >= evt.spell.level:
                        return
            for tag in [Tags.Dark, Tags.Holy]:
                if tag not in evt.spell.tags:
                    continue
                btag = Tags.Holy if tag == Tags.Dark else Tags.Dark
                b = HypocrisyStack(btag, evt.spell.level)
                self.owner.apply_buff(b)

    if cls is HypocrisyStack:

        def on_spell_cast(self, evt):
            if self.tag in evt.spell.tags and evt.spell.level <= self.level:
                evt.spell.cur_charges += 1
                evt.spell.cur_charges = min(evt.spell.cur_charges, evt.spell.get_stat('max_charges'))
            # Queue this so that the removal happens after the Hypocrisy upgrade determines whether the player has any Hypocrisy stacks
            self.owner.level.queue_spell(remove_hypocrisy(self))
        
        def remove_hypocrisy(self):
            self.owner.remove_buff(self)
            yield

    if cls is Purestrike:

        def on_init(self):
            self.name = "Purestrike"
            self.tags = [Tags.Holy, Tags.Arcane]
            self.level = 6
            self.global_triggers[EventOnPreDamaged] = self.on_damage
            self.can_redeal = lambda unit, source, damage_type: can_redeal(self, unit, source, damage_type)

        def on_damage(self, evt):
            if evt.damage_type != Tags.Physical:
                return
            if not evt.source or not evt.source.owner:
                return
            if evt.source.owner.shields < 1 and not evt.source.owner.has_buff(PureGraceBuff):
                return
            if evt.damage < 2:
                return
            if not are_hostile(evt.unit, self.owner):
                return
            self.owner.level.queue_spell(self.do_conversion(evt))
        
        def on_advance(self):
            for unit in self.owner.level.units:
                if unit.shields > 0:
                    unit.apply_buff(PureGraceBuff(), 1)
        
        def get_description(self):
            return ("At the end of your turn, all [shielded:shields] allies gain Pure Grace for [1_turn:duration]. This duration is fixed and unaffected by bonuses.\n"
                    "Whenever [physical] damage is dealt to an enemy, if the source of that damage is [shielded:shields] or has Pure Grace, redeal half of that damage as [arcane] and half of that damage as [holy].\n"
                    "Enemies will instead gain Pure Penance, which has the same effect when they deal [physical] damage to other enemies.")

        def can_redeal(self, u, source, damage_type):
            return damage_type == Tags.Physical and source.owner and (source.owner.shields > 0 or source.owner.has_buff(PureGraceBuff)) and (u.resists[Tags.Holy] < 100 or u.resists[Tags.Arcane] < 100)

    if cls is StormCaller:

        def on_damage(self, evt):
            if not are_hostile(self.owner, evt.unit):
                return

            if evt.damage_type not in [Tags.Ice, Tags.Lightning]:
                return

            bonus = self.get_stat("damage")
            if random.choice([True, False]):
                cloud = BlizzardCloud(self.owner)
                cloud.damage += bonus
            else:
                cloud = StormCloud(self.owner)
                cloud.damage += 2*bonus
            cloud.duration = self.get_stat("duration")
            cloud.source = self

            if not self.owner.level.tiles[evt.unit.x][evt.unit.y].cloud:
                self.owner.level.add_obj(cloud, evt.unit.x, evt.unit.y)
            else:
                possible_points = self.owner.level.get_points_in_ball(evt.unit.x, evt.unit.y, 1, diag=True)
                def can_cloud(p):
                    tile = self.owner.level.tiles[p.x][p.y]
                    if tile.cloud:
                        return False
                    if tile.is_wall():
                        return False
                    return True

                possible_points = [p for p in possible_points if can_cloud(p)]
                if possible_points:
                    point = random.choice(possible_points)
                    self.owner.level.add_obj(cloud, point.x, point.y)

    if cls is Boneguard:

        def on_init(self):
            self.name = "Bone Guard"
            self.level = 6
            self.tags = [Tags.Dark, Tags.Conjuration]
            self.owner_triggers[EventOnUnitAdded] = self.on_unit_added
            self.minion_health = 40
            self.minion_damage = 9
            self.minion_range = 7
            self.num_summons = 4

        def get_description(self):
            return ("Begin each level accompanied by [{num_summons}:num_summons] bone knights and a bone archer, all of which have 1 reincarnation.\n"
                    "Bone knights have [{minion_health}_HP:minion_health], [1_SH:shields], [100_dark:dark] resist, and [50_ice:ice] resist.\n"
                    "Bone knights have a melee attack which deals [{minion_damage}_dark:dark] damage and drains 2 max HP from [living] targets.\n"
                    "The bone archer has a ranged attack with the same damage and [{minion_range}_range:minion_range], which drains 1 max HP from [living] targets.").format(**self.fmt_dict())

        def on_unit_added(self, evt):
            if evt.unit != self.owner:
                return
            for _ in range(self.get_stat('num_summons')):
                unit = BoneKnight()
                apply_minion_bonuses(self, unit)
                unit.buffs.append(ReincarnationBuff(1))
                self.summon(unit, target=self.owner, radius=5)
            unit = BoneKnightArcher()
            apply_minion_bonuses(self, unit)
            unit.buffs.append(ReincarnationBuff(1))
            self.summon(unit, target=self.owner, radius=5)

    if cls is Frostbite:

        def on_init(self):
            self.name = "Frostbite"
            self.level = 5
            self.tags = [Tags.Ice, Tags.Dark]
            self.damage = 7
            self.global_triggers[EventOnBuffApply] = lambda evt: on_buff_apply(self, evt)

        def get_description(self):
            return ("Whenever an enemy is [frozen:freeze], inflict Frostbite for the same duration, which deals [{damage}_dark:dark] damage per turn.\n"
                    "Whenever the remaining duration of [freeze] on an enemy is refreshed or extended, the remaining duration of frostbite will be lengthened to match if it is shorter.").format(**self.fmt_dict())

        def on_buff_apply(self, evt):
            if not isinstance(evt.buff, FrozenBuff):
                return
            if not are_hostile(self.owner, evt.unit):
                return
            evt.unit.apply_buff(FrostbiteBuff(self), evt.buff.turns_left)

    if cls is InfernoEngines:

        def on_init(self):
            self.name = "Inferno Engines"
            self.tags = [Tags.Fire, Tags.Metallic]
            self.level = 7
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.duration = 10

        def get_description(self):
            return ("Whenever you cast a [fire] spell, all of your [metallic] allies gain [2_damage:damage] [fire] aura with radius equal to the level of the spell you cast for [{duration}_turns:duration]. Lower-level instances of Inferno Engine cannot overwrite higher-level instances.\n"
                    "This damage is fixed, and cannot be increased using shrines, skills, or buffs.\n"
                    "You also gain Engine Aura, during which all [metallic] minions you summon and all minions that become [metallic] will automatically gain Inferno Engine.").format(**self.fmt_dict())

        def on_spell_cast(self, evt):
            if evt.spell.level <= 0:
                    return

            if Tags.Fire not in evt.spell.tags:
                return

            duration = self.get_stat("duration")
            
            self.owner.apply_buff(InfernoEngineAura(evt.spell.level), duration)

    for func_name, func in [(key, value) for key, value in locals().items() if callable(value)]:
        if hasattr(cls, func_name):
            setattr(cls, func_name, func)

for cls in [DeathBolt, FireballSpell, PoisonSting, SummonWolfSpell, AnnihilateSpell, Blazerip, BloodlustSpell, DispersalSpell, FireEyeBuff, EyeOfFireSpell, IceEyeBuff, EyeOfIceSpell, LightningEyeBuff, EyeOfLightningSpell, RageEyeBuff, EyeOfRageSpell, Flameblast, Freeze, HealMinionsSpell, HolyBlast, HallowFlesh, mods.BugsAndScams.Bugfixes.RotBuff, VoidMaw, InvokeSavagerySpell, MeltSpell, MeltBuff, PetrifySpell, SoulSwap, TouchOfDeath, ToxicSpore, VoidRip, CockatriceSkinSpell, AngelSong, AngelicChorus, Darkness, MindDevour, Dominate, EarthquakeSpell, FlameBurstSpell, SummonFrostfireHydra, SummonGiantBear, HolyFlame, HolyShieldSpell, ProtectMinions, LightningHaloSpell, LightningHaloBuff, MercurialVengeance, MercurizeSpell, MercurizeBuff, PainMirrorSpell, ArcaneVisionSpell, PainMirror, SealedFateBuff, SealFate, ShrapnelBlast, BestowImmortality, UnderworldPortal, VoidOrbSpell, BlizzardSpell, BoneBarrageSpell, ChimeraFarmiliar, ConductanceSpell, ConjureMemories, DeathGazeSpell, EssenceFlux, SummonFieryTormentor, SummonIceDrakeSpell, LightningFormSpell, StormSpell, OrbControlSpell, Permenance, PuritySpell, PyrostaticPulse, SearingSealSpell, SearingSealBuff, SummonSiegeGolemsSpell, FeedingFrenzySpell, ShieldSiphon, StormNova, SummonStormDrakeSpell, IceWall, WatcherFormBuff, WatcherFormSpell, BallLightning, CantripCascade, IceWind, FaeCourt, SummonFloatingEye, FlockOfEaglesSpell, SummonIcePhoenix, MegaAnnihilateSpell, RingOfSpiders, SlimeformSpell, DragonRoarSpell, SummonGoldDrakeSpell, ImpGateSpell, MysticMemory, SearingOrb, KnightBuff, SummonKnights, MulticastBuff, MulticastSpell, SpikeballFactory, WordOfIce, ArcaneCredit, ArcaneAccountant, Hibernation, HibernationBuff, HolyWater, UnholyAlliance, WhiteFlame, Teleblink, Hypocrisy, HypocrisyStack, Purestrike, StormCaller, Boneguard, Frostbite, InfernoEngines]:
    modify_class(cls)