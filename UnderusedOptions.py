from Spells import *
from Level import *
from Monsters import *
from Upgrades import *
from Variants import *
from RareMonsters import *
from Consumables import *

import mods.Bugfixes.Bugfixes
import mods.NoMoreScams.NoMoreScams
from mods.BugfixesExtended.BugfixesExtended import RemoveBuffOnPreAdvance, MinionBuffAura, drain_max_hp_kill, increase_cooldown, HydraBeam, FreezeDependentBuff, EventOnShieldDamaged
from mods.NoMoreScams.NoMoreScams import is_immune, FloatingEyeBuff, is_conj_skill_summon

import sys, math, random

curr_module = sys.modules[__name__]

class RegenAuraBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Regeneration Aura"
        self.color = Tags.Heal.color

    def on_advance(self):

        heal = self.spell.get_stat("heal")
        growth = heal//4 if self.spell.get_stat("growth") else 0

        for unit in list(self.owner.level.get_units_in_ball(self.owner, self.spell.get_stat("radius"))):

            if unit.is_player_controlled or unit is self.owner:
                continue
            if self.owner.level.are_hostile(self.owner, unit):
                continue
            unit.deal_damage(-heal, Tags.Heal, self.spell)

            if not growth:
                continue
            if Tags.Slime not in unit.tags:
                unit.max_hp += growth
                unit.deal_damage(-growth, Tags.Heal, self.spell)
            else:
                unit.deal_damage(-heal, Tags.Heal, self.spell)

class HibernationRegen(RegenBuff):

    def __init__(self, upgrade):
        self.upgrade = upgrade
        RegenBuff.__init__(self, 15)
        self.name = "Hibernation"
        self.color = Tags.Ice.color
        self.asset = ["UnderusedOptions", "Statuses", "hibernation"]
        self.stack_type = STACK_NONE
        self.break_dtype = None
        self.freeze = FrozenBuff()
    
    def on_init(self):
        self.owner_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def on_pre_damaged(self, evt):
        if evt.damage <= 0 or evt.damage_type not in [Tags.Fire, Tags.Physical]:
            return
        self.break_dtype = evt.damage_type
        self.owner.remove_buff(self)
    
    def on_applied(self, owner):
        self.freeze.owner = self.owner
        self.freeze.turns_left = self.turns_left
        if self.owner.resists[Tags.Ice] < 100 or self.owner.has_buff(FrozenBuff):
            return
        self.owner.level.event_manager.raise_event(EventOnBuffApply(self.freeze, self.owner), self.owner)
    
    def on_unapplied(self):
        self.freeze.break_dtype = self.break_dtype
        self.freeze.turns_left = self.turns_left
        if self.owner.resists[Tags.Ice] < 100 or self.owner.has_buff(FrozenBuff):
            return
        self.owner.level.event_manager.raise_event(EventOnUnfrozen(self.owner, self.break_dtype), self.owner)
        self.owner.level.event_manager.raise_event(EventOnBuffRemove(self.freeze, self.owner), self.owner)

class IceMirrorBuff(Buff):

    def on_init(self):
        self.description = "When damaged by an enemy, that enemy has a chance to be frozen for 1 turn, equal to this unit's percentage of missing HP."
        self.color = Tags.Ice.color
        self.owner_triggers[EventOnDamaged] = self.on_damaged

    def on_damaged(self, evt):
        if not evt.source.owner or not are_hostile(evt.source.owner, self.owner):
            return
        if random.random() < (self.owner.max_hp - self.owner.cur_hp)/self.owner.max_hp:
            evt.source.owner.apply_buff(FrozenBuff(), 1)

class CantripCleanup(Upgrade):

    def on_init(self):
        self.name = "Cantrip Cleanup"
        self.level = 4
        self.description = "If Cantrip Cascade is out of charges at the beginning of your turn, the first cantrip you cast each turn will cast all of your other cantrips at the same target, consuming charges as normal, if possible.\nIf you have the Focused Cascade upgrade, all of your cantrips will be cast a second time, if possible."
        self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
    
    def on_applied(self, owner):
        self.on_pre_advance()
    
    def on_pre_advance(self):
        self.can_copy = self.prereq.cur_charges <= 0
    
    def on_spell_cast(self, evt):
        if not self.can_copy or evt.spell.level != 1 or Tags.Sorcery not in evt.spell.tags:
            return
        self.can_copy = False
        focus = self.prereq.get_stat("focus")
        if focus and evt.spell.can_pay_costs() and evt.spell.can_cast(evt.x, evt.y):
            self.owner.level.act_cast(self.owner, evt.spell, evt.x, evt.y)
        spells = [s for s in self.owner.spells if s.level == 1 and Tags.Sorcery in s.tags and type(s) != type(evt.spell)]
        if not spells:
            return
        random.shuffle(spells)
        for spell in spells:
            for _ in range(2 if focus else 1):
                if not spell.can_pay_costs() or not spell.can_cast(evt.x, evt.y):
                    continue
                self.owner.level.act_cast(self.owner, spell, evt.x, evt.y)

class SpontaneousCombustion(Upgrade):

    def on_init(self):
        self.name = "Spontaneous Combustion"
        self.level = 3
        self.description = "Each turn, you have a chance to cast Combust Poison automatically if possible, consuming charges as usual.\nThe chance is equal to the average [poison] duration of all enemies divided by 100, up to 100%."
    
    def on_advance(self):
        if not self.prereq.can_pay_costs() or not self.prereq.can_cast(self.owner.x, self.owner.y):
            return
        total = 0
        count = 0
        for unit in self.owner.level.units:
            if not are_hostile(unit, self.owner):
                continue
            count += 1
            poison = unit.get_buff(Poison)
            if not poison:
                continue
            total += poison.turns_left
        if not count:
            return
        if random.random() < total/count/100:
            self.owner.level.act_cast(self.owner, self.prereq, self.owner.x, self.owner.y)

class AngelSongBuff(Buff):

    def __init__(self, heal, radius):
        Buff.__init__(self)
        self.heal = heal
        self.radius = radius
        self.name = "Angelic Chorus"
        self.color = Tags.Holy.color
        self.tags = []

    def get_tooltip(self):
        return "Each turn, living and holy allies in a %i tile radius are healed for %i HP. Undead, demon, and dark enemies in the radius take 2 fire and 2 holy damage." % (self.get_stat("radius"), self.heal)

    def on_advance(self):
        for unit in self.owner.level.get_units_in_ball(self.owner, self.get_stat('radius')):
            if unit.is_player_controlled:
                continue
            if (Tags.Living in unit.tags or Tags.Holy in unit.tags) and not are_hostile(unit, self.owner):
                unit.deal_damage(-self.heal, Tags.Heal, self)
            if (Tags.Dark in unit.tags or Tags.Undead in unit.tags or Tags.Demon in unit.tags) and are_hostile(unit, self.owner):
                unit.deal_damage(2, Tags.Fire, self)
                unit.deal_damage(2, Tags.Holy, self)

    def get_stat(self, attr, base=None):
        if base is None:
            base = getattr(self, attr, 0)
        if self.owner:
            return self.owner.get_stat(base, self, attr)
        else:
            return base

class AngelicSinger(Unit):
    def can_harm(self, other):
        if Unit.can_harm(self, other):
            return True
        return Tags.Dark in other.tags or Tags.Undead in other.tags or Tags.Demon in other.tags

class HungeringReachBuff(Buff):
    def __init__(self, spell):
        Buff.__init__(self)
        self.spell_bonuses[spell]["range"] = 2
        self.buff_type = BUFF_TYPE_PASSIVE
        self.stack_type = STACK_INTENSITY

class ShrapnelSpell(SimpleRangedAttack):

    def __init__(self, spell):
        self.spell = spell
        SimpleRangedAttack.__init__(self, name="Shrapnel", damage=spell.damage, range=spell.range)
        self.requires_los = False
        self.shards = spell.get_stat("num_targets")
    
    def get_stat(self, attr, base=None):
        if attr == "radius":
            return 0
        return self.spell.get_stat(attr, base)
    
    def get_description(self):
        return "Pierces through walls. Damage is based on the wizard's Shrapnel Blast. User has 75%% chance to act again after using this attack, but dies after using it %i times." % self.shards

    def hit(self, x, y):
        self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Physical, self.spell)

    def cast(self, x, y):
        yield from SimpleRangedAttack.cast(self, x, y)
        self.shards -= 1
        if self.shards <= 0:
            self.caster.kill()
            # In case the user is resurrected.
            self.shards = self.spell.get_stat("num_targets")
        elif self.caster.is_alive() and random.random() < 0.75:
            self.caster.advance()

class ShrapnelGolemExplosion(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
        self.owner_triggers[EventOnDeath] = self.on_death
        self.color = Tags.Fire.color
    
    def get_tooltip(self):
        return "On death, deal %i fire damage to all enemies in a %i tile radius." % (self.spell.get_stat("damage"), self.spell.get_stat("radius"))
    
    def on_death(self, evt):
        damage = self.spell.get_stat("damage")
        for p in self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.spell.get_stat("radius")):
            unit = self.owner.level.get_unit_at(p.x, p.y)
            if not unit or not are_hostile(unit, self.spell.caster):
                self.owner.level.show_effect(p.x, p.y, Tags.Fire)
            else:
                unit.deal_damage(damage, Tags.Fire, self.spell)

class TempScalespinnerRemoval(Buff):

    def __init__(self, buff):
        self.buff = buff
        Buff.__init__(self)
        self.buff_type = BUFF_TYPE_PASSIVE
        self.stack_type = STACK_INTENSITY
    
    def on_advance(self):
        self.buff.owner.remove_buff(self.buff)
        self.owner.remove_buff(self)

def possession_summon_ghost(self):

    if not self.turns_left:
        if self.mass:
            for _ in range(8):
                unit = Ghost()
                apply_minion_bonuses(self.spell, unit)
                self.spell.summon(unit, target=self.owner)
        return
    
    unit = Ghost()
    if self.king:
        unit = GhostKing()
    elif self.mass:
        unit = GhostMass()
    apply_minion_bonuses(self.spell, unit)
    unit.turns_to_death = self.turns_left
    self.spell.summon(unit, target=self.owner)
    yield

def possession_try_summon_gates(self):

    if not self.king:
        return
    self.timer -= 1
    if self.timer > 0:
        return
    self.timer = 10

    for _ in range(2):
        lair = MonsterSpawner(Ghost)
        apply_minion_bonuses(self.spell, lair)
        self.spell.summon(lair, target=self.owner, radius=5, sort_dist=False)

class PossessedAlly(Thorns):

    def __init__(self, spell, king=False, mass=False):
        self.spell = spell
        self.king = king
        self.mass = mass
        self.timer = 1
        Thorns.__init__(self, damage=spell.get_stat("minion_damage"), dtype=Tags.Dark)
        self.name = "Possessed"
        self.asset = ["UnderusedOptions", "Statuses", "possessed_ally"]
        self.color = Tags.Dark.color
        self.stack_type = STACK_INTENSITY
        self.show_effect = False
    
    def on_unapplied(self):
        self.owner.level.queue_spell(possession_summon_ghost(self))

    def do_thorns(self, unit):
        unit.deal_damage(self.damage, self.dtype, self.spell)
        yield

    def on_advance(self):
        possession_try_summon_gates(self)

class PossessedEnemy(Buff):

    def __init__(self, spell, king=False, mass=False):
        self.spell = spell
        self.king = king
        self.mass = mass
        self.timer = 1
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Possessed"
        self.asset = ["UnderusedOptions", "Statuses", "possessed_enemy"]
        self.color = Tags.Dark.color
        self.buff_type = BUFF_TYPE_CURSE
        self.stack_type = STACK_INTENSITY
        self.damage = self.spell.get_stat("minion_damage")
        self.show_effect = False
    
    def on_unapplied(self):
        self.owner.level.queue_spell(possession_summon_ghost(self))

    def on_advance(self):
        possession_try_summon_gates(self)
        self.owner.deal_damage(self.damage, Tags.Dark, self.spell)

class LivingScrollIcicle(Icicle):

    def __init__(self, statholder=None):
        Icicle.__init__(self)
        self.max_charges = 0
        self.cur_charges = 0
        self.statholder = statholder
    
    def get_description(self):
        return "Kills the caster"
    
    def cast(self, x, y):
        yield from Icicle.cast(self, x, y)
        self.caster.kill()

class LivingScrollHeavenlyBlast(HolyBlast):

    def __init__(self, statholder=None):
        HolyBlast.__init__(self)
        self.max_charges = 0
        self.cur_charges = 0
        self.statholder = statholder
    
    def get_description(self):
        return "Kills the caster"
    
    def cast(self, x, y):
        yield from HolyBlast.cast(self, x, y)
        self.caster.kill()

class WriteCeruleanScrolls(Spell):

    def on_init(self):
        self.name = "Scribe Cerulean Scrolls"
        self.num_summons = 0
        self.range = 0
        self.cool_down = 6

    def get_description(self):
        bonus = self.get_stat("num_summons")
        return "Summon %i-%i living icicle or heavenly blast scrolls" % (2 + bonus, 4 + bonus)

    def cast(self, x, y):
        minion_health = self.caster.source.get_stat("minion_health", base=5)
        num_summons = self.get_stat("num_summons") + random.randint(2, 4)
        for _ in range(num_summons):
            tag = random.choice([Tags.Ice, Tags.Holy])
            unit = Unit()
            unit.max_hp = minion_health
            unit.flying = True
            unit.resists[Tags.Arcane] = 100
            unit.resists[tag] = 100
            unit.tags = [Tags.Arcane, tag, Tags.Construct]
            if tag == Tags.Ice:
                unit.name = "Living Scroll of Icicle"
                unit.asset = ["UnderusedOptions", "Units", "living_icicle_scroll"]
                unit.spells = [LivingScrollIcicle(statholder=self.caster.source.caster)]
            else:
                unit.name = "Living Scroll of Heavenly Blast"
                unit.asset = ["UnderusedOptions", "Units", "living_heavenly_blast_scroll"]
                unit.spells = [LivingScrollHeavenlyBlast(statholder=self.caster.source.caster)]
            self.summon(unit, sort_dist=False)
            yield

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
        self.description = "On kill and when removing SH with damage, gain 1 SH, up to a max of %i." % self.max
        self.global_triggers[EventOnDeath] = self.on_death
        self.global_triggers[EventOnShieldDamaged] = self.on_shield_damaged
    
    def on_death(self, evt):
        if evt.damage_event and evt.damage_event.source.owner is self.owner:
            if self.owner.shields < self.max:
                self.owner.add_shields(1)
    
    def on_shield_damaged(self, evt):
        if evt.source.owner is self.owner:
            if self.owner.shields < self.max:
                self.owner.add_shields(1)

class StoneMirrorBuff(Buff):

    def on_init(self):
        self.name = "Stone Mirror"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = PetrifyBuff().color
        self.owner_triggers[EventOnDeath] = self.on_death
    
    def on_death(self, evt):
        petrify = None
        glassify = None
        for buff in self.owner.buffs:
            if type(buff) == PetrifyBuff:
                petrify = buff
            elif type(buff) == GlassPetrifyBuff:
                glassify = buff
        if not petrify and not glassify:
            return
        targets = [u for u in self.owner.level.get_units_in_los(self.owner) if u is not self.owner and not are_hostile(u, self.owner)]
        if not targets:
            return
        good_targets = [u for u in targets if not u.has_buff(StoneMirrorBuff)]
        if good_targets:
            target = random.choice(good_targets)
        else:
            target = random.choice(targets)
        target.apply_buff(StoneMirrorBuff())
        if petrify:
            target.apply_buff(PetrifyBuff(), petrify.turns_left)
        if glassify:
            target.apply_buff(GlassPetrifyBuff(), glassify.turns_left)

class ToxicMushboomAura(DamageAuraBuff):
    def __init__(self, radius):
        DamageAuraBuff.__init__(self, 1, Tags.Poison, radius)
        self.owner_triggers[EventOnDeath] = self.on_death
    
    def on_death(self, evt):
        for _ in range(3):
            self.on_advance()
    
    def get_tooltip(self):
        return DamageAuraBuff.get_tooltip(self) + "\nInstantly activates 3 times on death"

class BasiliskArmorBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Basilisk Armor"
        self.color = Tags.Nature.color
        self.petrify_duration = self.spell.get_stat("petrify_duration")
        self.thorns = self.spell.get_stat("thorns")
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
        damage = self.spell.get_stat("damage", base=16)
        if are_hostile(evt.caster, self.owner) and evt.x == self.owner.x and evt.y == self.owner.y:
            evt.caster.apply_buff(self.debuff(), self.petrify_duration)
            if self.thorns:
                evt.caster.deal_damage(damage, Tags.Poison, self.spell)
                if self.debuff is Stun:
                    evt.caster.deal_damage(damage, Tags.Lightning, self.spell)
                elif self.debuff is FrozenBuff:
                    evt.caster.deal_damage(damage, Tags.Ice, self.spell)
                elif self.debuff is GlassPetrifyBuff:
                    evt.caster.deal_damage(damage, Tags.Physical, self.spell)

class DarknessBuff(Spells.DarknessBuff):

    def __init__(self, spell):
        self.spell = spell
        Spells.DarknessBuff.__init__(self)
        self.stack_type = STACK_REPLACE
        self.holy = spell.get_stat("holy")
        self.clinging = spell.get_stat("clinging")
        self.conceal = spell.get_stat("conceal")
        self.fractal = spell.get_stat("fractal")
        self.global_triggers[EventOnPreDamaged] = self.on_pre_damaged

    def effect_unit(self, unit):
        hostile = are_hostile(unit, self.owner)
        if Tags.Undead in unit.tags or Tags.Demon in unit.tags:
            if hostile and self.holy and self.owner.is_blind():
                unit.deal_damage(2, Tags.Holy, self)
            return
        existing = unit.get_buff(BlindBuff)
        if self.clinging and hostile:
            if existing:
                existing.turns_left += 2
            else:
                unit.apply_buff(BlindBuff(), 2)
        else:
            if existing and existing.turns_left == 1 and unit is self.owner:
                unit.remove_buff(existing)
            unit.apply_buff(BlindBuff(), 1)
    
    def on_pre_damaged(self, evt):
        if evt.damage <= 0:
            return
        hostile = are_hostile(evt.unit, self.owner)
        blind = self.owner.is_blind()
        if self.conceal:
            if hostile or not blind:
                return
            if evt.unit is not self.owner and Tags.Undead not in evt.unit.tags and Tags.Demon not in evt.unit.tags:
                return
            if random.random() >= 0.5:
                return
            if hasattr(evt.unit, "negates"):
                evt.unit.negates.append(evt)
            else:
                evt.unit.negates = [evt]
        elif self.fractal:
            if not hostile or not blind or evt.damage <= 1 or evt.damage_type != Tags.Dark:
                return
            self.owner.level.queue_spell(self.deal_damage(evt.unit, evt.damage//2))

    def deal_damage(self, unit, damage):
        unit.deal_damage(damage, Tags.Dark, self.spell)
        yield

class SpiritBindingBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        self.applier = spell.caster
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
        spirit.flying = True
        self.spell.summon(spirit, target=self.owner)

class FireHydraBeam(HydraBeam):

    def __init__(self, spell, caster):
        HydraBeam.__init__(self, spell, caster, "Fire Beam", Tags.Fire, MeltSpell)
        self.cool_down = 2

    def can_redeal(self, target, already_checked):
        return self.dragon_mage_spell.get_stat("fire_resist") and not target.has_buff(MeltBuff) and target.resists[Tags.Fire] < 200

    def per_square_effect(self, x, y):
        self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)

class IceHydraBeam(HydraBeam):

    def __init__(self, spell, caster):
        HydraBeam.__init__(self, spell, caster, "Ice Beam", Tags.Ice, Freeze)
        self.cool_down = 2

    def can_redeal(self, target, already_checked):
        return self.dragon_mage_spell.get_stat("absolute_zero") and not target.has_buff(AbsoluteZeroBuff) and target.resists[Tags.Ice] < 200

    def per_square_effect(self, x, y):
        self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)

class FrostfireHydraBeam(HydraBeam):

    def __init__(self, spell, caster):
        HydraBeam.__init__(self, spell, caster, "Fire Beam", Tags.Fire, MeltSpell)
        self.other_dragon_mage_spell = Freeze()
        self.other_dragon_mage_spell.caster = caster
        self.other_dragon_mage_spell.owner = caster
        self.other_dragon_mage_spell.max_charges = 0
        self.other_dragon_mage_spell.cur_charges = 0
        self.other_dragon_mage_spell.range = RANGE_GLOBAL
        self.other_dragon_mage_spell.requires_los = False
        self.other_dragon_mage_spell.statholder = spell.caster
        self.cool_down = 0
        if random.choice([True, False]):
            self.change_element()

    def change_element(self):
        if self.damage_type == Tags.Fire:
            self.damage_type = Tags.Ice
        else:
            self.damage_type = Tags.Fire
        self.name = "%s Beam" % self.damage_type.name
        old = self.dragon_mage_spell
        self.dragon_mage_spell = self.other_dragon_mage_spell
        self.other_dragon_mage_spell = old

    def per_square_effect(self, x, y):
        self.caster.level.deal_damage(x, y, self.get_stat("damage"), self.damage_type, self)

    def can_redeal(self, target, already_checked):
        if self.damage_type == Tags.Fire:
            return self.dragon_mage_spell.get_stat("fire_resist") and not target.has_buff(MeltBuff) and target.resists[Tags.Fire] < 200
        else:
            return self.dragon_mage_spell.get_stat("absolute_zero") and not target.has_buff(AbsoluteZeroBuff) and target.resists[Tags.Ice] < 200

class FrostfireHydraBuff(Buff):

    def __init__(self, beam):
        self.beam = beam
        Buff.__init__(self)
        self.color = Tags.Dragon.color
        self.description = "Beam alternates between fire and ice each turn."

    def on_advance(self):
        self.beam.change_element()

class SpellConduitBuff(Buff):

    def __init__(self, fire=True, lightning=True, casts=1):
        self.fire = fire
        self.lightning = lightning
        self.casts = casts
        Buff.__init__(self)
        self.description = "Copies %i of the wizard's %s%s%s%s or chaos sorcery spells with the highest max charges that can be cast from this tile, consuming a charge from them and counting as the wizard casting them." % (self.casts, "fire" if self.fire else "", ", " if self.fire and self.lightning else "", "lightning" if self.lightning else "", "," if self.fire and self.lightning else "")
        self.color = Tags.Sorcery.color
    
    def copy_spell(self, spell):
        spell_copy = type(spell)()
        spell_copy.statholder = self.owner.source.caster
        spell_copy.owner = self.owner
        spell_copy.caster = self.owner
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
    
    def on_advance(self):
        if self.owner.has_buff(ChannelBuff):
            return
        casts_left = self.casts
        for spell in self.get_wizard_spells():
            spell_copy = self.copy_spell(spell)
            target = spell_copy.get_ai_target()
            if not target:
                continue
            spell.cur_charges -= 1
            self.owner.level.queue_spell(spell_copy.cast(target.x, target.y))
            self.owner.level.event_manager.raise_event(EventOnSpellCast(spell, self.owner.source.caster, target.x, target.y), self.owner.source.caster)
            casts_left -= 1
            if not casts_left:
                return

class WildMetamorphosis(Upgrade):

    def __init__(self, num=1):
        self.num = num
        Upgrade.__init__(self)

    def on_init(self):
        self.name = "Wild Metamorphosis%s" % ((" %i" % self.num) if self.num > 1 else "")
        self.level = 1
    
    def get_description(self):
        if not self.spell_bonuses:
            return "Chimera Familiar randomly gains [7_minion_health:minion_health], [3_minion_damage:minion_damage], or [1_minion_range:minion_range].\nThis upgrade can be purchased an unlimited number of times."
        else:
            return None

    def on_applied(self, owner):
        if self.spell_bonuses:
            return
        bonuses = {"minion_health": 7, "minion_damage": 3, "minion_range": 1}
        stat = random.choice(list(bonuses.keys()))
        self.spell_bonuses[ChimeraFarmiliar][stat] = bonuses[stat]
        self.prereq.add_upgrade(WildMetamorphosis(self.num + 1))

class ConductanceBuff(Buff):
	
    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)

    def on_init(self):
        self.name = "Conductance"
        self.color = Tags.Lightning.color
        self.resists[Tags.Lightning] = -self.spell.get_stat("resistance_debuff")
        self.cascade_range = self.spell.get_stat("cascade_range")
        self.strikechance = self.spell.get_stat("strikechance")
        self.buff_type = BUFF_TYPE_CURSE
        self.asset = ['status', 'conductance']
        self.owner_triggers[EventOnPreDamaged] = self.on_pre_damaged

    def on_pre_damaged(self, evt):
        if evt.damage <= 0 or evt.damage_type != Tags.Lightning or random.random() >= self.strikechance/100:
            return
        targets = [unit for unit in self.owner.level.get_units_in_ball(self.owner, self.cascade_range) if unit is not self.owner and are_hostile(self.spell.caster, unit) and self.owner.level.can_see(self.owner.x, self.owner.y, unit.x, unit.y)]
        if not targets:
            return
        self.owner.level.queue_spell(self.bolt(random.choice(targets), evt.damage))
    
    def bolt(self, target, damage):
        for point in Bolt(self.owner.level, self.owner, target):
            self.owner.level.show_effect(point.x, point.y, Tags.Lightning, minor=True)
            yield
        target.deal_damage(damage, Tags.Lightning, self.spell)
        target.apply_buff(curr_module.ConductanceBuff(self.spell), self.turns_left)

class FieryTormentorRemorse(Upgrade):

    def on_init(self):
        self.name = "Tormentor's Remorse"
        self.level = 2
        self.description = "The tormentor's soul suck now also heals the wizard, but the total amount healed cannot exceed the total damage that the wizard has taken from tormentors summoned by this spell, before counting healing penalty."
        self.global_triggers[EventOnUnitAdded] = self.on_unit_added
        self.global_triggers[EventOnDamaged] = self.on_damaged
        self.healing_pool = 0
    
    def on_unit_added(self, evt):
        if evt.unit.source is not self.prereq:
            return
        evt.unit.apply_buff(FieryTormentorRemorseIndicator(self))
    
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
    def get_description(self):
        return "Soul Suck heals the wizard for an amount equal to the damage done. Can apply no more than %i healing." % self.upgrade.healing_pool

class LightningFormBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
        self.transform_asset_name = "player_lightning_form"
        self.name = "Lightning Form"
        self.buff_type = BUFF_TYPE_BLESS
        self.asset = ['status', 'lightning_form']
        self.color = Tags.Lightning.color
        self.cast = True
        self.stack_type = STACK_TYPE_TRANSFORM

    def on_advance(self):
        if not self.cast:
            self.owner.remove_buff(self)
        self.cast = False

    def on_init(self):
        self.resists[Tags.Lightning] = 100
        self.resists[Tags.Physical] = 100
        self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
        self.owner_triggers[EventOnPass] = self.on_pass
        self.owner_triggers[EventOnPreDamaged] = self.on_pre_damaged

    def on_pre_damaged(self, evt):
        if evt.damage <= 0 or isinstance(evt.source, LightningFormSpell) or evt.damage_type != Tags.Lightning or self.owner.resists[Tags.Lightning] < 100 or not self.spell.get_stat("rod"):
            return
        targets = [u for u in self.owner.level.get_units_in_los(self.owner) if are_hostile(u, self.owner)]
        if not targets:
            return
        self.owner.level.queue_spell(self.bolt(random.choice(targets), evt))

    def bolt(self, target, evt):
        for p in Bolt(self.owner.level, self.owner, target):
            self.owner.level.show_effect(p.x, p.y, Tags.Lightning, minor=True)
        target.deal_damage(evt.damage, Tags.Lightning, self.spell)
        yield

    def on_spell_cast(self, evt):
        if Tags.Lightning not in evt.spell.tags:
            return
        self.cast = True
        swap = self.spell.get_stat("swap")
        if self.owner.level.can_move(self.owner, evt.x, evt.y, teleport=True, force_swap=swap):
            self.owner.level.queue_spell(self.do_teleport(evt.x, evt.y, swap))
                    
    def on_pass(self, evt):
        if self.owner.has_buff(ChannelBuff):
            self.cast = True

    def do_teleport(self, x, y, swap):
        if self.owner.level.can_move(self.owner, x, y, teleport=True, force_swap=swap):
            self.owner.level.act_move(self.owner, x, y, teleport=True, force_swap=swap)
        yield

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
        self.bloodrage_bonus = self.spell.get_stat("bloodrage_bonus")
        self.feeding_frenzy = self.spell.get_stat("feeding_frenzy")
        if self.spell.get_stat("unending"):
            self.owner_triggers[EventOnDeath] = self.on_death
        self.stack_type = STACK_REPLACE

    def on_advance(self):
        self.cooldown -= 1
        if self.cooldown == 0:
            self.cooldown = self.freq

            unit = Unit()
            unit.name = "Blood Vulture"
            unit.asset_name = "blood_hawk"
            unit.max_hp = self.minion_health
            unit.flying = True
            duration = self.spell.get_stat("duration", base=10)
            claw = SimpleMeleeAttack(damage=self.minion_damage, onhit=lambda caster, target: caster.apply_buff(BloodrageBuff(self.bloodrage_bonus), caster.get_stat(self.spell.get_stat("duration", base=10), claw, "duration")))
            claw.description = ""
            claw.get_description = lambda: "Gain %i damage for %i turns with each attack" % (self.bloodrage_bonus, unit.get_stat(self.spell.get_stat("duration", base=10), claw, "duration"))
            claw.name = "Frenzy Talons"
            dive = LeapAttack(damage=self.minion_damage, range=self.minion_range)
            dive.cool_down = 3
            dive.name = "Dive"
            unit.spells = [claw, dive]
            unit.resists[Tags.Dark] = 75
            unit.tags = [Tags.Nature, Tags.Demon]
            self.spell.summon(unit, target=self.owner, radius=5, sort_dist=False)

            if self.feeding_frenzy:
                duration = self.spell.get_stat("duration", base=10)
                for unit in [unit for unit in self.owner.level.get_units_in_los(self.owner) if not are_hostile(self.spell.caster, unit)]:
                    stacks = [buff.bonus for buff in unit.buffs if isinstance(buff, BloodrageBuff)]
                    if not stacks:
                        continue
                    max_bloodrage = max(stacks)
                    if max_bloodrage > 0 and random.random() >= self.owner.cur_hp/self.owner.max_hp:
                        unit.apply_buff(BloodrageBuff(max_bloodrage), duration)

    def on_death(self, evt):
        targets = [unit for unit in self.owner.level.get_units_in_los(self.owner) if are_hostile(self.spell.caster, unit)]
        if targets:
            random.choice(targets).apply_buff(SightOfBloodBuff(self.spell), self.turns_left)

class SummonedStormDrakeBreath(StormBreath):

    def __init__(self, spell):
        StormBreath.__init__(self)
        self.damage = spell.get_stat("breath_damage")
        self.range = spell.get_stat("minion_range")
        self.strikechance = spell.get_stat("strikechance")/100
        self.surge = spell.get_stat("surge")

    def per_square_effect(self, x, y):
        if self.surge:
            existing = self.caster.level.tiles[x][y].cloud
            if isinstance(existing, BlizzardCloud) or isinstance(existing, StormCloud):
                self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Lightning, self)
                if self.strikechance > 0.5 and random.random() < 0.5:
                    self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Lightning, self)
        cloud = StormCloud(self.caster, self.get_stat("damage"))
        cloud.source = self
        cloud.strikechance = self.strikechance
        self.caster.level.add_obj(cloud, x, y)

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
        if evt.source.owner and evt.source.owner.source is self.prereq and evt.source.owner.name == "Ice Phoenix":
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
        if source.owner and source.owner.source is self.prereq and source.owner.name == "Ice Phoenix":
            return True
        return False
    
    def on_pre_damaged(self, evt):
        if self.qualifies(evt.unit, evt.source, evt.damage_type):
            self.owner.level.queue_spell(self.deal_damage(evt))
    
    def deal_damage(self, evt):
        evt.unit.deal_damage(evt.damage//2, Tags.Holy, evt.source)
        yield

    # For my No More Scams mod
    def can_redeal(self, target, source, damage_type, already_checked):
        return self.qualifies(target, source, damage_type) and not is_immune(target, source, Tags.Holy, already_checked)

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
    def can_redeal(self, target, source, damage_type, already_checked):
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

class FrostbiteBuff(FreezeDependentBuff):

    def __init__(self, upgrade):
        self.upgrade = upgrade
        FreezeDependentBuff.__init__(self)
    
    def on_init(self):
        self.name = "Frostbite"
        self.asset = ["UnderusedOptions", "Statuses", "frostbite"]
        self.color = Tags.Dark.color
        self.buff_type = BUFF_TYPE_CURSE

    def on_advance(self):
        self.owner.deal_damage(self.upgrade.get_stat("damage"), Tags.Dark, self.upgrade)

class FragilityBuff(FreezeDependentBuff):

    def on_init(self):
        self.name = "Fragile"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Ice.color
        self.resists[Tags.Ice] = -100
        self.resists[Tags.Physical] = -100
        self.asset = ["UnderusedOptions", "Statuses", "fragility"]

class IceTapBuff(FreezeDependentBuff):

    def on_init(self):
        self.name = "Ice Tap"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Arcane.color
        self.asset = ["UnderusedOptions", "Statuses", "ice_tap"]

class IceResonanceBuff(FreezeDependentBuff):

    def on_init(self):
        self.name = "Ice Resonance"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Ice.color

class HolyArmorBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Holy Armor"
        self.stack_type = STACK_REPLACE
        self.color = Tags.Holy.color
        resist = self.spell.get_stat("resist")
        self.passed = True
        for tag in [Tags.Fire, Tags.Lightning, Tags.Physical, Tags.Dark]:
            self.resists[tag] = resist
        if self.spell.get_stat("riposte"):
            self.owner_triggers[EventOnDamaged] = self.on_damaged
            self.owner_triggers[EventOnPass] = self.on_pass

    def on_damaged(self, evt):
        if not self.passed:
            return
        if not evt.source.owner or not are_hostile(evt.source.owner, self.owner):
            return
        self.owner.level.queue_spell(self.riposte(evt.source.owner))
    
    def on_pass(self, evt):
        self.passed = True

    def on_pre_advance(self):
        self.passed = False

    def riposte(self, target):
        for point in Bolt(self.owner.level, self.owner, target, find_clear=False):
            self.owner.level.show_effect(point.x, point.y, Tags.Holy, minor=True)
            yield
        target.deal_damage(self.spell.get_stat("damage", base=18), Tags.Holy, self.spell)

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

    def get_description(self):
        return "Wall of Ice no longer requires line of sight to cast.\nWall and chasm tiles in the affected area are converted to floor tiles before summoning the ice elementals.\nUnits in the affected area take [%i_ice:ice] damage and are [frozen] for [%i_turns:duration]. If a unit is killed then an ice elemental is summoned in its tile." % (self.prereq.get_stat("damage", base=22), self.prereq.get_stat("duration", base=3))

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

class VoidOrbRedGiant(Upgrade):
    def on_init(self):
        self.name = "Red Giant"
        self.level = 5
        self.description = "Void Orb also deals [fire] damage."
        self.spell_bonuses[VoidOrbSpell]["radius"] = 1
        self.spell_bonuses[VoidOrbSpell]["fire"] = 1

class KnightlyOathBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)

    def on_applied(self, owner):
        self.max_hp = self.owner.max_hp
        self.shields = self.owner.shields

    def on_init(self):
        self.owner_triggers[EventOnDamaged] = self.on_damaged
        self.color = Tags.Holy.color
        self.description = "Upon reaching 0 HP, deal 40 holy damage to its summoner to fully heal self and remove all debuffs."
        self.undying = self.spell.caster.get_buff(KnightlyOathUndyingOath)

    def on_damaged(self, evt):
        if self.owner.cur_hp <= 0:
            self.owner.cur_hp = 1
            for buff in list(self.owner.buffs):
                if buff.buff_type == BUFF_TYPE_CURSE:
                    self.owner.remove_buff(buff)
            self.owner.max_hp = max(self.owner.max_hp, self.max_hp)
            self.owner.shields = max(self.owner.shields, self.shields)
            self.owner.deal_damage(-self.owner.max_hp, Tags.Heal, self.spell)
            if self.undying and self.undying.free_revive:
                self.undying.free_revive = False
            else:
                self.spell.caster.deal_damage(40, Tags.Holy, self.spell)

class KnightlyOathUndyingOath(Upgrade):

    def on_init(self):
        self.name = "Undying Oath"
        self.level = 7
        self.description = "Knightly Oath can now save one knight from death per turn for free, without dealing damage to the caster.\nThis is refreshed before the beginning of each of your turns."
        self.free_revive = True
    
    def on_pre_advance(self):
        self.free_revive = True

class WarpLightningBuff(Buff):
    def on_init(self):
        self.show_effect = False
        self.name = "Warp Lightning"
        self.buff_type = BUFF_TYPE_CURSE
        self.color = Tags.Lightning.color

class SwappersSchemeBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        self.stacks = 1
        Buff.__init__(self)
    
    def on_init(self):
        self.name = "Swapper's Scheme %i" % self.stacks
        self.color = Tags.Translocation.color
        self.owner_triggers[EventOnPreDamaged] = self.on_pre_damaged
    
    def on_attempt_apply(self, owner):
        for buff in owner.buffs:
            if isinstance(buff, SwappersSchemeBuff):
                buff.stacks += 1
                buff.name = "Swapper's Scheme %i" % buff.stacks
                return False
        return True

    def on_pre_damaged(self, evt):
        if evt.damage <= 0:
            return
        penetration = evt.penetration if hasattr(evt, "penetration") else 0
        if self.owner.resists[evt.damage_type] - penetration >= 100:
            return
        target = self.spell.get_ai_target()
        if not target:
            return
        unit = self.owner.level.get_unit_at(target.x, target.y)
        if not unit:
            return
        self.owner.shields += 1
        self.owner.level.queue_spell(self.spell.cast(target.x, target.y))
        self.owner.level.queue_spell(self.deal_damage(unit, evt))
        if self.stacks <= 1:
            self.owner.remove_buff(self)
        else:
            self.stacks -= 1
            self.name = "Swapper's Scheme %i" % self.stacks
    
    def deal_damage(self, target, evt):
        penetration = evt.penetration if hasattr(evt, "penetration") else 0
        target.deal_damage(evt.damage, evt.damage_type, evt.source, penetration=penetration)
        yield

def BoneBarrageBoneShambler(self, hp, extra_damage):
    unit = BoneShambler(hp)
    if self.get_stat("regrowth"):
        regen = hp//8
        if regen:
            unit.buffs.append(RegenBuff(regen))
    if self.get_stat("ghost"):
        damage = self.get_stat("minion_damage", base=extra_damage)
        if damage:
            unit.spells[0].onhit = lambda caster, target: target.deal_damage(damage, Tags.Dark, unit.spells[0])
            # For my No More Scams mod
            unit.spells[0].can_redeal = lambda target, already_checked: not is_immune(target, unit.spells[0], Tags.Dark, already_checked)
            unit.spells[0].description = "Deals %i additional dark damage." % damage
    buff = unit.get_buff(SplittingBuff)
    if buff:
        buff.spawner = lambda: BoneBarrageBoneShambler(self, unit.max_hp//2, extra_damage)
    return unit

class ChaosSiegeBuff(Buff):
    
    def on_init(self):
        self.name = "Chaos Siege"
        self.color = Tags.Chaos.color
        self.stack_type = STACK_INTENSITY
        self.spell_bonuses[ChaosBarrage]["num_targets"] = 2
        self.passed = True
        self.owner_triggers[EventOnPass] = self.on_pass

    def on_pre_advance(self):
        self.passed = False

    def on_advance(self):
        if not self.passed:
            self.owner.remove_buff(self)

    def on_pass(self, evt):
        self.passed = True

class SummonedVoidDrakeBreath(VoidBreath):

    def __init__(self):
        VoidBreath.__init__(self)
        self.essence = False
    
    def get_description(self):
        if self.essence:
            return "Deals damage to enemies in a cone and melts walls. Temporary allies gain +1 duration."
        else:
            return VoidBreath.get_description(self)

    def per_square_effect(self, x, y):

        if not self.caster.level.tiles[x][y].is_chasm:
            self.caster.level.make_floor(x, y)
        
        if not self.essence:
            self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Arcane, self)
        else:
            unit = self.caster.level.get_unit_at(x, y)
            if not unit or not are_hostile(unit, self.caster):
                self.caster.level.show_effect(x, y, Tags.Arcane)
                if unit and unit.turns_to_death is not None:
                    unit.turns_to_death += 1
            else:
                unit.deal_damage(self.get_stat("damage"), Tags.Arcane, self)

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
            self.minion_damage = 5

            self.upgrades['damage'] = (12, 1)
            self.upgrades['max_charges'] = (10, 2)
            self.upgrades['minion_damage'] = (9, 3)
            self.upgrades["soulfeedback"] = (1, 5, "Soul Feedback", "Death Bolt deals additional damage equal to 4 times the number of [undead], [demon], [holy], and [arcane] minions you have.", "soul")
            self.upgrades['soulbattery'] = (1, 7, "Soul Battery", "Death Bolt permenantly gains [1_damage:damage] whenever it slays a [living] target.\nUnits killed before you gain this upgrade are also counted.", "soul")
            self.kills = 0

        def get_stat(self, attr, base=None):
            if attr != "damage" or not self.get_stat("soulbattery"):
                return Spell.get_stat(self, attr, base)
            return Spell.get_stat(self, attr, base) + self.kills

        def cast(self, x, y):
            for p in Bolt(self.caster.level, self.caster, Point(x, y)):
                self.caster.level.show_effect(p.x, p.y, Tags.Dark, minor=True)
                yield
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return
            if Tags.Living in unit.tags:
                # Queue the skeleton raise as the first spell to happen after the damage so that it will pre-empt stuff like ghostfire
                self.caster.level.queue_spell(self.try_raise(self.caster, unit))
            damage = self.get_stat("damage")
            if self.get_stat("soulfeedback"):
                for u in self.caster.level.units:
                    if are_hostile(u, self.owner):
                        continue
                    if not [tag for tag in [Tags.Undead, Tags.Demon, Tags.Holy, Tags.Arcane] if tag in u.tags]:
                        continue
                    damage += 4
            unit.deal_damage(damage, Tags.Dark, self)

        def try_raise(self, caster, unit):
            if unit and not unit.is_alive():
                self.kills += 1
                skeleton = mods.Bugfixes.Bugfixes.raise_skeleton(caster, unit, source=self, summon=False)
                if not skeleton:
                    return
                skeleton.spells[0].damage = self.get_stat('minion_damage')
                self.summon(skeleton, target=unit)
                yield

    if cls is FireballSpell:

        def on_init(self):
            self.radius = 2
            self.damage = 9
            self.name = "Fireball"
            self.max_charges = 18
            self.range = 8

            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 1

            self.upgrades['radius'] = (1, 3)
            self.upgrades['damage'] = (8, 2)
            self.upgrades['max_charges'] = (8, 2)
            self.upgrades['range'] = (3, 1)

            self.upgrades['chaos'] = (1, 3, "Chaos Ball", "Fireball redeals a percentage of its [fire] damage to enemies as [lightning] and [physical] damage.\nThe percentage is 25%, plus 1/4 of each enemy's [fire] resistance if positive.", "damage type")
            self.upgrades['energy'] = (1, 4, "Energy Ball", "Fireball redeals a percentage of its [fire] damage to enemies as [arcane] and [holy] damage.\nThe percentage is 25%, plus 1/4 of each enemy's [fire] resistance if positive.", "damage type")
            self.upgrades['ash'] = (1, 5, "Ash Ball", "Fireball redeals a percentage of its [fire] damage to enemies as [dark] and [poison] damage.\nThe percentage is 25%, plus 1/4 of each enemy's [fire] resistance if positive.\nEnemies are also [blinded] for [1_turn:duration].", "damage type")

        def cast(self, x, y):
            target = Point(x, y)
            damage = self.get_stat('damage')
            blind = False
            redeals = []
            if self.get_stat("chaos"):
                redeals = [Tags.Lightning, Tags.Physical]
            elif self.get_stat("energy"):
                redeals = [Tags.Arcane, Tags.Holy]
            elif self.get_stat("ash"):
                redeals = [Tags.Dark, Tags.Poison]
                blind = True
            for p in Bolt(self.caster.level, self.caster, target):
                self.caster.level.show_effect(p.x, p.y, Tags.Fire, minor=True)
                for tag in redeals:
                    self.caster.level.show_effect(p.x, p.y, tag, minor=True)
                yield
            for stage in Burst(self.caster.level, target, self.get_stat('radius')):
                for point in stage:
                    self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)
                    if not redeals:
                        continue
                    unit = self.caster.level.get_unit_at(point.x, point.y)
                    if unit and are_hostile(unit, self.caster):
                        bonus_damage = math.floor(damage*(25 + (unit.resists[Tags.Fire]/4 if unit.resists[Tags.Fire] > 0 else 0))/100)
                        for tag in redeals:
                            unit.deal_damage(bonus_damage, tag, self)
                        if blind:
                            unit.apply_buff(BlindBuff(), 1)
                    else:
                        for tag in redeals:
                            self.caster.level.show_effect(point.x, point.y, tag)
                yield
    
    if cls is MagicMissile:

        def on_init(self):
            self.name = "Magic Missile"
            self.range = 12
            self.tags = [Tags.Arcane, Tags.Sorcery]
            self.level = 1

            self.damage = 11
            self.damage_type = Tags.Arcane

            self.max_charges = 20
            self.shield_burn = 0

            self.upgrades['max_charges'] = (15, 2)
            self.upgrades['damage'] = (10, 3)
            self.upgrades['range'] = (5, 1)
            self.upgrades['shield_burn'] = (3, 1, "Shield Burn", "Magic Missile removes up to [3_SH:shields] from the target before dealing damage.")
            self.upgrades['slaughter'] = (1, 4, "Slaughter Bolt", "If Magic Missile targets a [living] or [nature] unit, 2/3 of its damage is redealt as [poison], [dark], and [physical] damage.")
            self.upgrades['holy'] = (1, 4, "Holy Bolt", "If Magic Missile targets a [demon] or [undead] unit, it also deals [holy] damage.")
            self.upgrades['disruption'] = (1, 6, "Disruption Bolt", "If Magic Missile targets an [arcane] unit, it also deals [dark] and [holy] damage.")

        def cast(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            damage = self.get_stat('damage')
                    
            for p in Bolt(self.caster.level, self.caster, Point(x, y)):
                self.caster.level.show_effect(p.x, p.y, Tags.Arcane, minor=True)
                yield

            if unit:
                if self.get_stat('shield_burn'):
                    unit.shields -= self.get_stat('shield_burn')
                    unit.shields = max(unit.shields, 0)
                unit.deal_damage(damage, Tags.Arcane, self)
                if self.get_stat('slaughter') and (Tags.Living in unit.tags or Tags.Nature in unit.tags):
                    for dtype in [Tags.Poison, Tags.Dark, Tags.Physical]:
                        unit.deal_damage(2*damage//3, dtype, self)
                if self.get_stat('holy') and (Tags.Undead in unit.tags or Tags.Demon in unit.tags):
                    unit.deal_damage(damage, Tags.Holy, self)
                if self.get_stat('disruption') and Tags.Arcane in unit.tags:
                    for dtype in [Tags.Dark, Tags.Holy]:
                        unit.deal_damage(damage, dtype, self)

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
            self.upgrades['antigen'] = (1, 2, "Acidity", "Damaged targets lose [100_poison:poison] resistance.\nIf this removes the target's [poison] immunity, the target will still be [poisoned].")
            self.upgrades["torment"] = (1, 5, "Torment", "Deal 1 extra damage per 10 turns of [poison] on the target, and 1 extra damage per turn of every other debuff on the target.\nDeal 1 extra damage per debuff on the target. Multiple stacks of the same type of debuff are counted as different debuffs.")

        def get_description(self):
            return ("Apply [{duration}_turns:duration] of [poison] and deal [{damage}_physical:physical] damage to target unit.\n"
                    + text.poison_desc).format(**self.fmt_dict())

        def cast(self, x, y):

            for p in Bolt(self.caster.level, self.caster, Point(x, y), find_clear=False):
                self.caster.level.show_effect(p.x, p.y, Tags.Poison, minor=True)
                yield
            
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return
            
            poisoned = False
            if unit.resists[Tags.Poison] < 100:
                unit.apply_buff(Poison(), self.get_stat('duration'))
                poisoned = True

            damage = self.get_stat("damage")
            if self.get_stat("torment"):
                for debuff in [buff for buff in unit.buffs if buff.buff_type == BUFF_TYPE_CURSE]:
                    damage += 1
                    if isinstance(debuff, Poison):
                        damage += math.ceil(debuff.turns_left/10)
                    else:
                        damage += debuff.turns_left
            dealt = unit.deal_damage(damage, Tags.Physical, self)
            
            if dealt and self.get_stat('antigen'):
                unit.apply_buff(Acidified())
                if not poisoned:
                    unit.apply_buff(Poison(), self.get_stat('duration'))

    if cls is SummonWolfSpell:

        def on_init(self):
            self.max_charges = 12
            self.name = "Wolf"
            self.minion_health = 11
            self.minion_damage = 5
            self.upgrades['leap_range'] = (1, 3, "Pounce", "Summoned wolves gain a leap attack with [{minion_range}_range:minion_range].")
            self.upgrades['minion_damage'] = 4
            self.upgrades['minion_health'] = (12, 3)

            self.upgrades['blood_hound'] = (1, 3, "Blood Hound", "Summon blood hounds instead of wolves.", "hound")
            self.upgrades['ice_hound'] = (1, 3, "Ice Hound", "Summon ice hounds instead of wolves.", "hound")
            self.upgrades['clay_hound'] = (1, 6, "Clay Hound", "Summon clay hounds instead of wolves.", "hound")
            self.upgrades['wolf_pack'] = (1, 7, "Wolf Pack", "Each cast of Wolf consumes an additional charge and summons [{num_summons}:num_summons] wolves.\nThis counts as casting the spell an additional time.")

            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 1

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["num_summons"] = self.get_stat("num_summons", base=4)
            stats["minion_range"] = self.get_stat('minion_range', base=4)
            return stats

        def make_wolf(self):
            wolf = Unit()
            wolf.name = "Wolf"
            wolf.max_hp = self.get_stat('minion_health')
            wolf.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))
            wolf.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('leap_range'):
                wolf.spells.append(LeapAttack(damage=self.get_stat('minion_damage'), damage_type=Tags.Physical, range=self.get_stat('minion_range', base=4)))

            if self.get_stat('blood_hound'):
                wolf.name = "Blood Hound"
                wolf.asset_name = "blood_wolf"
                melee = wolf.spells[0]
                melee.onhit = lambda caster, target: caster.apply_buff(BloodrageBuff(2), caster.get_stat(self.get_stat("duration", base=10), melee, "duration"))
                melee.name = "Frenzy Bite"
                melee.description = ""
                melee.get_description = lambda: "Gain +2 damage for %i turns with each attack" % wolf.get_stat(self.get_stat("duration", base=10), melee, "duration")
                
                wolf.tags = [Tags.Demon, Tags.Nature]
                wolf.resists[Tags.Dark] = 75

            elif self.get_stat('ice_hound'):
                for s in wolf.spells:
                    s.damage_type = Tags.Ice
                wolf.resists[Tags.Ice] = 100
                wolf.resists[Tags.Fire] = -50
                wolf.resists[Tags.Dark] = 50
                wolf.name = "Ice Hound"
                wolf.tags = [Tags.Demon, Tags.Ice]
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
                num_wolves = self.get_stat("num_summons", base=4)
                self.cur_charges -= 1
                self.cur_charges = max(self.cur_charges, 0)
                self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)
            for _ in range(num_wolves):
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
            self.arcane = 0
            self.dark = 0

            self.upgrades['cascade'] =  (1, 3, 'Cascade', 'Hits from Annihilate will jump to targets up to [{cascade_range}_tiles:cascade_range] away if the main target is killed or if targeting an empty tile. This ignores line of sight.')
            self.upgrades['nightmare'] =  (1, 2, 'Nightmare Annihilation', 'Annihilate also deals [arcane] and [dark] damage.')
            self.upgrades["micro"] = (1, 2, "Micro Annihilate", "Annihilate will deal [1_fire:fire], [1_lightning:lightning], and [1_physical:physical] damage before its other hits. This damage is fixed, and cannot be increased using shrines, skills, or buffs.\nIf you have the Nightmare Annihilation upgrade, this will deal [dark] and [arcane] damage as well.")
            self.upgrades['max_charges'] = (16, 6)

        def cast(self, x, y):
            
            cur_target = Point(x, y)
            dtypes = [Tags.Fire, Tags.Lightning, Tags.Physical]
            if self.get_stat('arcane'):
                dtypes.append(Tags.Arcane)
            if self.get_stat('dark'):
                dtypes.append(Tags.Dark)
            if self.get_stat("nightmare"):
                dtypes.extend([Tags.Arcane, Tags.Dark])
            
            damage = self.get_stat('damage')
            cascade = self.get_stat("cascade")
            cascade_range = self.get_stat("cascade_range", base=4)
            inescapable = self.get_stat("inescapable")
            micro = [True, False] if self.get_stat("micro") else [False]

            for is_micro in micro:
                for dtype in dtypes:
                    if cascade and not self.caster.level.get_unit_at(cur_target.x, cur_target.y):
                        other_targets = [t for t in self.caster.level.get_units_in_ball(cur_target, cascade_range) if are_hostile(t, self.caster)]
                        if other_targets:
                            cur_target = random.choice(other_targets)
                    if inescapable:
                        unit = self.caster.level.get_unit_at(cur_target.x, cur_target.y)
                        if unit:
                            unit.shields = 0
                            for buff in list(unit.buffs):
                                if buff.buff_type == BUFF_TYPE_BLESS:
                                    unit.remove_buff(buff)
                    self.caster.level.deal_damage(cur_target.x, cur_target.y, damage if not is_micro else 1, dtype, self)
            yield

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
            self.upgrades["phantom"] = (1, 6, "Phantom Zone", "Summon a void ghost in the former location of each unit teleported away.\nThese void ghosts cannot be affected by this spell.")

        def cast(self, x, y):
            phantom = self.get_stat("phantom")
            for target in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat('radius')):

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
                self.caster.level.act_move(target, target_point.x, target_point.y, teleport=True)
                self.caster.level.show_effect(target.x, target.y, Tags.Translocation)
                if phantom:
                    ghost = GhostVoid()
                    apply_minion_bonuses(self, ghost)
                    self.summon(ghost, target=old)
                
                yield

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

        def on_shoot(self, target_point):
            unit = self.owner.level.get_unit_at(target_point.x, target_point.y)
            if not unit:
                return
            already_berserk = unit.has_buff(BerserkBuff)
            unit.apply_buff(BerserkBuff(), self.berserk_duration)
            if not already_berserk or not self.spell.get_stat("psychosis"):
                return
            for spell in unit.spells:
                if not spell.can_pay_costs():
                    continue
                target_point = spell.get_ai_target()
                if not target_point:
                    continue
                target = unit.level.get_unit_at(target_point.x, target_point.y)
                if not target:
                    continue
                if are_hostile(target, self.spell.caster):
                    unit.level.act_cast(unit, spell, target_point.x, target_point.y)
                    return
            unit.apply_buff(Stun(), 1)

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
            self.upgrades['psychosis'] = (1, 5, "Psychosis", "When an already [berserk] enemy is targeted by Eye of Rage, it now chooses a random valid target for one of its abilities.\nIf the new target is another enemy, the first enemy is forced to use that ability on the new target. Otherwise the first enemy is [stunned] for [1_turn:duration].")

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
            self.upgrades["absolute_zero"] = (1, 6, "Absolute Zero", "When targeting an enemy, the target now permanently loses [100_ice:ice] resistance before being [frozen].")
            self.upgrades["permafrost"] = (1, 5, "Permafrost", "When targeting an already [frozen] enemy, increase the duration of [freeze] on it by one third of this spell's duration if the result is greater than this spell's duration.\nThen deal [ice] damage equal to twice the target's [freeze] duration.\nThis upgrade cannot extend [freeze] duration on targets that can gain clarity.")

        def cast_instant(self, x, y):
            duration = self.get_stat("duration")
            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return
            if not are_hostile(target, self.caster):
                target.apply_buff(FrozenBuff(), duration)
                return
            if self.get_stat("absolute_zero"):
                target.apply_buff(AbsoluteZeroBuff())
            existing = target.get_buff(FrozenBuff)
            if existing and self.get_stat("permafrost"):
                if not target.gets_clarity:
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
            self.upgrades["cleanse"] = (1, 2, "Cleansing Light", "Healing Light will now remove all debuffs from affected allies before healing them.")

            self.tags = [Tags.Holy, Tags.Sorcery]
            self.level = 2

        def cast(self, x, y):

            heal = self.get_stat("heal")
            shields = self.get_stat('shields')
            cleanse = self.get_stat("cleanse")

            for unit in self.caster.level.get_units_in_los(self.caster):
                if unit.team == TEAM_PLAYER and unit is not self.caster:

                    # Dont heal the player if a gold drake is casting
                    if unit.is_player_controlled:
                        continue

                    if cleanse:
                        for buff in unit.buffs:
                            if buff.buff_type == BUFF_TYPE_CURSE:
                                unit.remove_buff(buff)

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
            self.upgrades['spiritbind'] = (1, 4, "Spirit Bind", "Enemies hit are inflicted with Spirit Binding.\nWhen an enemy with Spirit Binding dies, summon a spirit near it for [{minion_duration}_turns:minion_duration].\nSpirit are [holy] [undead] minions with [{minion_health}_HP:minion_health] and attacks with [{minion_range}_range:minion_range] that deal [{minion_damage}_holy:holy] damage.\nSpirit Binding is removed from all units at the beginning of your next turn.")
            self.upgrades['shield'] = (1, 3, "Shield", "Affected ally units gain [2_SH:shields], to a maximum of [5_SH:shields].")
            self.upgrades['echo_heal'] = (1, 4, "Echo Heal", "Affected ally units are re-healed for half the initial amount each turn for [{duration}_turns:duration].")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_health"] = self.get_stat("minion_health", base=4)
            stats["minion_damage"] = self.get_stat("minion_damage", base=2)
            stats["minion_range"] = self.get_stat("minion_range", base=3)
            stats["minion_duration"] = self.get_stat("minion_duration", base=7)
            stats["duration"] = self.get_stat("duration", base=5)
            return stats

        def cast(self, x, y):
            target = Point(x, y)
            damage = self.get_stat("damage")
            shield = self.get_stat("shield")
            echo_heal = self.get_stat("echo_heal")
            duration = self.get_stat("duration", base=5)
            bind = self.get_stat("spiritbind") and self.caster.is_alive()

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
            self.max_charges = 6
            self.range = 9
            self.requires_los = False

            self.holy_vulnerability = 100
            self.fire_vulnerability = 0
            self.max_health_loss = 25
            self.radius = 4

            self.upgrades["radius"] = (3, 3)
            self.upgrades['max_health_loss'] = (25, 3)
            self.upgrades['fire_vulnerability'] = (50, 2, "Fire Vulnerability")
            self.upgrades["mockery"] = (1, 2, "Mockery of Life", "Affected units no longer gain [dark] resistance.")
            self.upgrades["friendly"] = (1, 4, "Vigor Mortis", "When your minions are affected, their max HP are instead buffed by the same percentage.\nThey do not suffer healing reduction, and instead gain [100_poison:poison] resistance.\nIf you have the Fire Vulnerability upgrade, they instead gain [50_ice:ice] resistance.\nIf you have the Mockery of Life upgrade, they still gain [dark] resistance and do not lose [holy] resistance.")
            self.upgrades["rot"] = (1, 4, "Flesh Rot", "When affecting a unit already affected by Hollow Flesh, this spell also deals [poison] damage equal to 25% of the max HP that unit lost from Hollow Flesh.\nIf you have the Vigor Mortis upgrade, this will instead [heal] affected allies.")

        def get_impacted_tiles(self, x, y):
            return Spell.get_impacted_tiles(self, x, y)

        def get_description(self):
            return ("Curse units in a [{radius}_tile:radius] radius except the caster to become [undead].\n"
                    "Affected units lose [{max_health_loss}%:damage] of their max HP.\n"
                    "Affected units lose [100_holy:holy] resistance.\n"
                    "Affected units gain [100_dark:dark] resistance.\n"
                    "Affected units suffer 100% healing penalty.").format(**self.fmt_dict())

        def cast(self, x, y):
            friendly = self.get_stat("friendly")
            rot = self.get_stat("rot")
            for unit in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat("radius")):
                if unit is self.caster:
                    continue
                if rot:
                    existing = unit.get_buff(mods.Bugfixes.Bugfixes.RotBuff)
                    if existing:
                        if existing.buff_type == BUFF_TYPE_CURSE:
                            unit.deal_damage(existing.hp//4, Tags.Poison, self)
                        else:
                            unit.deal_damage(-(existing.hp//4), Tags.Heal, self)
                buff = mods.Bugfixes.Bugfixes.RotBuff(self)
                if friendly and not are_hostile(unit, self.caster):
                    buff.buff_type = BUFF_TYPE_BLESS
                else:
                    buff.buff_type = BUFF_TYPE_CURSE
                unit.apply_buff(buff)
            yield

    if cls is mods.Bugfixes.Bugfixes.RotBuff:

        def on_init(self):
            self.color = Tags.Undead.color
            self.name = "Hollow Flesh"
            self.asset = ['status', 'rot']
            self.originally_undead = False
            self.stack_type = STACK_REPLACE
            self.friendly = self.spell.get_stat("friendly")
            self.mockery = self.spell.get_stat("mockery")
            self.hp = 0

        def on_applied(self, owner):
            self.hp = math.floor(self.owner.max_hp*self.spell.get_stat('max_health_loss')/100)

            if self.friendly and self.buff_type == BUFF_TYPE_BLESS:
                self.owner.max_hp += self.hp
                self.owner.deal_damage(-self.hp, Tags.Heal, self.spell)
            else:
                drain_max_hp(self.owner, self.hp)
            if Tags.Undead in self.owner.tags:
                self.originally_undead = True
            else:
                self.owner.tags.append(Tags.Undead)
            
            self.resists[Tags.Dark] = 100
            self.resists[Tags.Holy] = -100
            if self.friendly and self.buff_type == BUFF_TYPE_BLESS:
                if self.mockery:
                    self.resists[Tags.Holy] = 0
                self.resists[Tags.Poison] = 100
                self.resists[Tags.Ice] = self.spell.get_stat('fire_vulnerability')
            else:
                if self.mockery:
                    self.resists[Tags.Dark] = 0
                self.resists[Tags.Fire] = -self.spell.get_stat('fire_vulnerability')
                self.resists[Tags.Heal] = 100

        def on_unapplied(self):
            if self.buff_type == BUFF_TYPE_CURSE:
                self.owner.max_hp += self.hp
            else:
                drain_max_hp(self.owner, self.hp)
            if not self.originally_undead and Tags.Undead in self.owner.tags:
                self.owner.tags.remove(Tags.Undead)

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
            self.upgrades["shield_eater"] = (1, 3, "Shield Eater", "The maw gains [1_SH:shields] on kill and when removing [SH:shields] with damage, up to the [SH:shields] amount of this spell.")

            self.must_target_empty = True

        def get_description(self):
            return ("Summons a hungry maw.\n"
                    "The maw has [{minion_health}_HP:minion_health], [{shields}_SH:shields], floats, and is stationary.\n"
                    "The maw has a [{minion_damage}_physical:physical] damage tongue attack, which pulls the target [{pull_strength}_tiles:range] towards it, with a range of [{minion_range}_tiles:minion_range].\n"
                    "The maw has a melee bite that deals the same damage but attacks 3 times.\n"
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
            melee = SimpleMeleeAttack(damage=damage, attacks=3)
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
            self.upgrades["stampede"] = (1, 5, "Stampede", "If no melee targets are available, each ally will instead try to perform a charge attack with a range of [{minion_range}_tiles:minion_range].\nThis attack does not stun.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_range"] = self.get_stat("minion_range", base=6)
            return stats

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
                melee_targets = [u for u in self.caster.level.get_units_in_ball(unit, radius=1, diag=True) if are_hostile(u, self.caster) and not is_immune(u, melee, melee.damage_type, [])]
                if melee_targets:
                    target = random.choice(melee_targets)
                    self.caster.level.act_cast(unit, melee, target.x, target.y, pay_costs=False)
                    yield
                elif charge:
                    charge.statholder = unit
                    charge.caster = unit
                    charge.owner = unit
                    charge_targets = [u for u in units if are_hostile(u, self.caster) and charge.can_cast(u.x, u.y) and not is_immune(u, charge, charge.damage_type, [])]
                    if not charge_targets:
                        continue
                    target = random.choice(charge_targets)
                    self.caster.level.act_cast(unit, charge, target.x, target.y, pay_costs=False)
                    yield

    if cls is MagnetizeSpell:

        def on_init(self):
            self.name = "Magnetize"
            self.tags = [Tags.Lightning, Tags.Metallic, Tags.Enchantment]

            self.level = 2
            self.max_charges = 10
            self.can_target_self = True

            self.radius = 5
            self.pull_strength = 1

            self.range = 9
            self.requires_los = False

            self.duration = 5

            self.upgrades['radius'] = (3, 3)
            self.upgrades['pull_strength'] = (1, 2, "Pull Distance")
            self.upgrades['duration'] = (10, 2)
            self.upgrades['universal'] = (1, 3, "Universal Magnetism", "Magnetize can target non [metallic] units.")
            self.upgrades["planar"] = (1, 4, "Planar Magnetism", "Each turn, after pulling all enemies in its radius, a magnetized target teleports a random enemy outside of its radius into a random tile in its radius.")

        def get_impacted_tiles(self, x, y):
            return [Point(x, y)]

    if cls is MagnetizeBuff:

        def on_advance(self):

            radius = self.spell.get_stat('radius')
            pull_strength = self.spell.get_stat('radius')
            units = [u for u in self.owner.level.get_units_in_ball(self.owner, radius) if u != self.owner]
            random.shuffle(units)
            
            for u in units:
                if not are_hostile(u, self.spell.caster):
                    continue
                for p in self.owner.level.get_points_in_line(self.owner, u):
                    self.owner.level.show_effect(p.x, p.y, Tags.Lightning, minor=True)
                pull(u, self.owner, pull_strength)
                if distance(self.owner, u) < 2:
                    u.apply_buff(Stun(), 1)
            
            if not self.spell.get_stat("planar"):
                return
            units = [u for u in self.owner.level.units if are_hostile(u, self.spell.caster) and distance(u, self.owner) > radius]
            if not units:
                return
            random.shuffle(units)
            for u in units:
                point = self.owner.level.get_summon_point(self.owner.x, self.owner.y, radius_limit=radius, sort_dist=False, flying=u.flying)
                if not point:
                    continue
                self.owner.level.show_effect(u.x, u.y, Tags.Lightning, minor=True)
                self.owner.level.act_move(u, point.x, point.y, teleport=True)
                self.owner.level.show_effect(u.x, u.y, Tags.Lightning, minor=True)
                return

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
                unit.apply_buff(MeltBuff(self))
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
            self.max_charges = 20
            self.name = "Petrify"

            self.tags = [Tags.Arcane, Tags.Enchantment]

            self.duration = 10

            self.upgrades['max_charges'] = (10, 2)
            self.upgrades["duration"] = (10, 3)
            self.upgrades['glassify'] = (1, 3, 'Glassify', 'Turn the target to [glass] instead of stone.\n[Glassified] targets have [-100_physical:physical] resistance.')
            self.upgrades["mirror"] = (1, 4, "Stone Mirror", "When targeting an enemy, the target is also permanently inflicted with Stone Mirror.\nWhen a [petrified] or [glassified] enemy with Stone Mirror dies, one of that enemy's allies in its line of sight will also be inflicted with Stone Mirror and the dead enemy's remaining duration of [petrify] and [glassify].\nTargets without Stone Mirror are prioritized.")
            self.level = 2

        def cast(self, x, y):

            target = self.caster.level.get_unit_at(x, y)
            if not target:
                return

            self.caster.level.deal_damage(x, y, 0, Tags.Physical, self)
            buff = PetrifyBuff() if not self.get_stat('glassify') else GlassPetrifyBuff()
            target.apply_buff(buff, self.get_stat('duration'))
            if self.get_stat("mirror") and are_hostile(target, self.caster):
                target.apply_buff(StoneMirrorBuff())
            yield

    if cls is SoulSwap:

        def on_init(self):
            self.requires_los = False
            self.range = RANGE_GLOBAL

            self.name = "Soul Swap"
            
            self.max_charges = 9

            self.level = 2
            self.tags = [Tags.Dark, Tags.Sorcery, Tags.Translocation]

            self.upgrades['forced_transfer'] = (1, 2, 'Forced Transfer', 'Soul Swap can target enemy units as well.')
            self.upgrades["demon"] = (1, 3, "Infernal Swap", "Soul Swap can target [demon] units as well.")
            self.upgrades["relay"] = (1, 3, "Soul Relay", "The minion that you swapped with will immediately take an action without costing a turn.\nIf you have the Forced Transfer upgrade and swap with an enemy, that enemy is [stunned] for [1_turn:duration].")
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
            if Tags.Demon in unit.tags and self.get_stat("demon"):
                return True
            return False

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if self.caster.level.can_move(self.caster, x, y, teleport=True, force_swap=True):
                self.caster.level.act_move(self.caster, x, y, teleport=True, force_swap=True)
            if self.get_stat("relay"):
                if are_hostile(unit, self.caster):
                    unit.apply_buff(Stun(), 1)
                elif not unit.is_player_controlled:
                    self.caster.level.queue_spell(free_action(unit))

        def free_action(unit):
            if not unit.is_alive():
                return
            unit.advance()
            yield

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
            self.upgrades['raise']= (1, 6, 'Touch of the Reaper', 'When a target dies to Touch of Death, it is raise as a friendly Reaper for [{minion_duration}_turns:minion_duration].\nThe Reaper can cast Touch of Death, which gains all of your upgrades and bonuses, but dies automatically after raising another Reaper.')

            self.source = self

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_duration"] = self.get_stat('minion_duration', base=6)
            return stats

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit and self.get_stat("raise"):
                self.caster.level.queue_spell(try_raise(self, unit))
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

        def try_raise(self, unit):
            if unit.is_alive():
                return
            if self.caster.name == "Reaper":
                self.caster.kill()
            reaper = Reaper()
            reaper.turns_to_death = 6
            apply_minion_bonuses(self, reaper)
            spell = TouchOfDeath()
            spell.source = self.source
            spell.max_charges = 0
            spell.cur_charges = 0
            spell.caster = reaper
            spell.owner = reaper
            spell.statholder = self.source.caster
            reaper.spells[0] = spell
            reaper.buffs = []
            self.source.summon(reaper, Point(unit.x, unit.y))
            yield

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
            self.upgrades['toxic_mushboom'] = (1, 4, "Toxic Mushbooms", "Summon toxic mushbooms instead, which are like green mushbooms but also have auras that deal [1_poison:poison] damage in a [{radius}_tile:radius] radius.\nOn death, toxic mushbooms instantly activate their auras 3 times.", "color")
            self.upgrades['red_mushboom'] = (1, 5, "Red Mushbooms", "Summon red mushbooms instead, which do not apply [poison] but deal [{red_attack_damage}_fire:fire] damage on attack and [{red_boom_damage}_fire:fire] damage when exploding.", "color")
            self.upgrades['glass_mushboom'] = (1, 6, "Glass Mushbooms", "Summon glass mushbooms instead, which which do not apply [poison] but apply [glassify] for [{glass_attack_duration}_turns:duration] on attack and [{glass_boom_duration}_turns:duration] when exploding.", "color")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=3)
            stats["green_attack_duration"] = self.get_stat("duration", base=4)
            stats["green_boom_duration"] = self.get_stat("duration", base=12)
            stats["red_attack_damage"] = self.get_stat("minion_damage", base=5)
            stats["red_boom_damage"] = self.get_stat("minion_damage", base=9)
            stats["glass_attack_duration"] = self.get_stat("duration", base=2)
            stats["glass_boom_duration"] = self.get_stat("duration", base=3)
            return stats

        def get_description(self):
            return ("Summons [{num_summons}:num_summons] Mushbooms.\n"
                    "Mushbooms have [{minion_health}_HP:minion_health].\n"
                    "Mushbooms have a ranged attack dealing [{minion_damage}_poison:poison] damage and inflicting [{green_attack_duration}_turns:duration] of [poison].\n"
                    "Mushbooms inflict [{green_boom_duration}_turns:duration] of [poison] on units in melee range when they die.").format(**self.fmt_dict())

        def cast(self, x, y):
            green = 0
            toxic = self.get_stat('toxic_mushboom')
            red = self.get_stat('red_mushboom')
            glass = self.get_stat('glass_mushboom')
            radius = self.get_stat("radius", base=3)
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
                    spell.buff_name = "Glassed"
                    spell.description = ""
                else:
                    mushboom = GreenMushboom()
                    green = 1
                    duration = self.get_stat("duration", base=4)
                    spell = mushboom.spells[0]
                    spell.onhit = None
                    spell.buff = Poison
                    spell.buff_duration = duration
                    spell.buff_name = "Poison"
                    spell.description = ""
                if green or glass:
                    mushboom.buffs[0].apply_duration = self.get_stat("duration", base=mushboom.buffs[0].apply_duration)
                else:
                    mushboom.buffs[0].damage = self.get_stat("minion_damage", base=9)
                if toxic:
                    mushboom.name = "Toxic Mushboom"
                    mushboom.asset = ["UnderusedOptions", "Units", "toxic_mushboom"]
                    mushboom.buffs.append(ToxicMushboomAura(radius))
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
            self.can_target_self = True

            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Aether Swap can be cast without line of sight")
            self.upgrades['range'] = (3, 1)
            self.upgrades['max_charges'] = (10, 3)
            self.upgrades["patsy"] = (1, 5, "Patsy Swap", "You can now target yourself with this spell to give yourself a stack of Swapper's Scheme, which consumes another charge of the spell and counts as casting the spell twice.\nWhenever you are about to take damage, you automatically consume a stack of Swapper's Scheme to swap with a random valid enemy target of this spell. You gain [1_SH:shields], which ignores the normal [20_SH:shields] limit, while the target takes damage from both Aether Swap and the damage that you took.")
            self.upgrades["glitch"] = (1, 5, "Glitch Swap", "You can now target an empty tile with this spell to swap with a unit that does not exist, which consumes another charge of the spell and counts as casting the spell twice.\nThis summons a glitch phantom at your old location, which is an [arcane] minion with [1_SH:shields] and the same max HP as you that can cast Aether Swap with the same upgrades, skills, and shrine as your own. The glitch phantom has a fixed lifetime of [1_turn:minion_duration].")

            self.tags = [Tags.Arcane, Tags.Translocation, Tags.Sorcery]

        def get_description(self):
            return ("Swap places with target unit.\n"
                    "If that unit is hostile, it takes [{damage}_arcane:arcane] damage. Otherwise it gains [1_SH:shields].").format(**self.fmt_dict())

        def can_cast(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if not unit and (not self.get_stat("glitch") or self.cur_charges <= 1):
                return False
            if unit is self.caster and (not self.get_stat("patsy") or self.cur_charges <= 1):
                return False
            if not self.caster.level.tiles[x][y].can_walk:
                return False
            return Spell.can_cast(self, x, y)

        def cast_instant(self, x, y):

            if x == self.caster.x and y == self.caster.y:
                if self.get_stat("patsy") and self.cur_charges > 0:
                    self.caster.apply_buff(SwappersSchemeBuff(self))
                    self.cur_charges -= 1
                    self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)
                return

            target = self.caster.level.get_unit_at(x, y)
            
            old = Point(self.caster.x, self.caster.y)
            if self.caster.level.tiles[x][y].can_walk:
                self.caster.level.show_effect(x, y, Tags.Translocation)
                self.caster.level.act_move(self.caster, x, y, teleport=True, force_swap=True)	
                
            if target:
                if are_hostile(target, self.caster):
                    target.deal_damage(self.get_stat('damage'), Tags.Arcane, self)
                else:
                    target.add_shields(1)
            elif self.get_stat("glitch") and self.cur_charges > 0:
                unit = Unit()
                unit.asset = ["UnderusedOptions", "Units", "glitch_phantom"]
                unit.name = "Glitch Phantom"
                unit.tags = [Tags.Arcane]
                unit.shields = 1
                unit.max_hp = self.caster.max_hp
                unit.resists[Tags.Arcane] = 100
                spell = VoidRip()
                spell.max_charges = 0
                spell.cur_charges = 0
                spell.caster = unit
                spell.owner = unit
                spell.statholder = self.caster
                unit.spells = [spell]
                unit.turns_to_death = 1
                self.summon(unit, target=old)
                self.cur_charges -= 1
                self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)

    if cls is CockatriceSkinSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Basilisk Armor"
            self.duration = 10
            self.petrify_duration = 2

            self.upgrades['duration'] = 5
            self.upgrades["petrify_duration"] = (3, 2)
            self.upgrades["thorns"] = (1, 4, "Thorns", "Enemies targeting you with spells also take [{damage}_poison:poison] damage.\nIf you have the Stunning Armor upgrade, also deal [lightning] damage.\nIf you have the Freezing Armor upgrade, also deal [ice] damage.\nIf you have the Glassifying Armor upgrade, also deal [physical] damage.")
            self.upgrades["stun"] = (1, 2, "Stunning Armor", "Basilisk Armor inflicts [stun] instead of [petrify].", "armor")
            self.upgrades["freeze"] = (1, 2, "Freezing Armor", "Basilisk Armor inflicts [freeze] instead of [petrify].", "armor")
            self.upgrades["glassify"] = (1, 2, "Glassifying Armor", "Basilisk Armor inflicts [glassify] instead of [petrify].", "armor")

            self.tags = [Tags.Enchantment, Tags.Nature, Tags.Arcane]
            self.level = 3

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["damage"] = self.get_stat("damage", base=16)
            return stats

        def cast_instant(self, x, y):
            self.caster.apply_buff(BasiliskArmorBuff(self), self.get_stat("duration"))

        def get_description(self):
            return ("Whenever an enemy unit targets you with a spell or attack, that unit is [petrified] for [{petrify_duration}_turns:duration].\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is BlindingLightSpell:

        def on_init(self):
            self.name = "Blinding Light"

            self.range = 0
            self.max_charges = 4
            self.duration = 4
            self.damage = 14

            self.tags = [Tags.Holy, Tags.Sorcery]
            self.level = 3
            self.upgrades['duration'] = (4, 2)
            self.upgrades["safety"] = (1, 3, "Safety", "No longer affects friendly units.")
            self.upgrades['searing'] = (1, 4, "Searing Light", "Blinding Light now deals 1/7 of its normal damage to affected units that are not [undead], [demon], or [dark], rounded up.")

        def get_description(self):
            return ("[Blind] all units in line of sight of the caster for [{duration}_turns:duration].\n"
                    + text.blind_desc +
                    "\nDeals [{damage}_holy:holy] damage to affected [undead], [demon], and [dark] units.").format(**self.fmt_dict())

        def cast(self, x, y):
            targets = [u for u in self.caster.level.get_units_in_los(self.caster) if u is not self.caster]
            if self.get_stat("safety"):
                targets = [u for u in targets if are_hostile(u, self.caster)]
            random.shuffle(targets)

            duration = self.get_stat('duration')
            damage = self.get_stat('damage')
            searing = self.get_stat("searing")
            for target in targets:
                target.apply_buff(BlindBuff(), duration)

                if not (Tags.Undead in target.tags or Tags.Demon in target.tags or Tags.Dark in target.tags):
                    if searing:
                        target.deal_damage(math.ceil(damage/7), Tags.Holy, self)
                else:
                    target.deal_damage(damage, Tags.Holy, self)

                yield

    if cls is Teleport:

        def cast(self, x, y):
            start_loc = Point(self.caster.x, self.caster.y)

            self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Translocation)
            p = self.caster.level.get_summon_point(x, y)
            if p:
                yield self.caster.level.act_move(self.caster, p.x, p.y, teleport=True)
                self.caster.level.show_effect(self.caster.x, self.caster.y, Tags.Translocation)

            if self.get_stat('void_teleport'):
                damage = self.get_stat('max_charges')
                for unit in self.owner.level.get_units_in_los(self.caster):
                    if are_hostile(self.owner, unit):
                        unit.deal_damage(damage, Tags.Arcane, self)

            tag = None
            if self.get_stat('lightning_blink'):
                tag = Tags.Lightning
            elif self.get_stat('dark_blink'):
                tag = Tags.Dark
            if tag:
                damage = 2*self.get_stat("range")
                for stage in Burst(self.caster.level, Point(x, y), self.get_stat("radius", base=3), ignore_walls=self.get_stat("requires_los") <= 0):
                    for point in stage:
                        if point == Point(x, y):
                            continue
                        self.caster.level.deal_damage(point.x, point.y, damage, tag, self)
                    yield

    if cls is BlinkSpell:

        def on_init(self):
            self.range = 5
            self.requires_los = True
            self.name = "Blink"
            self.max_charges = 6
            self.tags = [Tags.Arcane, Tags.Sorcery, Tags.Translocation]
            self.level = 3

            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Blink can be cast without line of sight")
            self.upgrades['range'] = (3, 3)
            self.upgrades['max_charges'] = (5, 2)
            self.upgrades['lightning_blink'] = (1, 4, "Lightning Blink", "Blink deals [lightning] damage in a [{radius}_tile:radius] burst upon arrival.\n The damage is equal to twice the range of this spell.\nIf this spell has blindcasting, the burst can pass through walls.", 'damage')
            self.upgrades['dark_blink'] = (1, 4, "Dark Blink", "Blink deals [dark] damage in a [{radius}_tile:radius] burst upon arrival.\n The damage is equal to twice the range of this spell.\nIf this spell has blindcasting, the burst can pass through walls.", 'damage')

    if cls is AngelicChorus:

        def on_init(self):
            self.name = "Choir of Angels"

            self.minion_health = 10
            self.shields = 1
            self.minion_duration = 10
            self.num_summons = 3
            self.heal = 1
            self.radius = 5

            self.range = 7

            self.tags = [Tags.Holy, Tags.Conjuration]
            self.level = 3

            self.max_charges = 5

            self.upgrades['shields'] = (2, 2)
            self.upgrades['num_summons'] = (3, 4)
            self.upgrades['minion_duration'] = (10, 2)
            self.upgrades['heal'] = (2, 3)
            self.upgrades["fallen"] = (1, 7, "Fallen Choir", "The angels become [demon] units and gain [100_dark:dark] resistance.\nThey gain a wailing attack with a cooldown of [7_turns:duration] that deals [{cacophony_damage}_dark:dark] damage to enemies in the same radius as their song, and an attack with [{minion_range}_range:minion_range] that deals [{hellfire_damage}_fire:fire] damage.\nUnlike their song, these attacks benefit from bonuses to [minion_damage:minion_damage].")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["cacophony_damage"] = self.get_stat("minion_damage", base=7)
            stats["hellfire_damage"] = self.get_stat("minion_damage", base=4)
            stats["minion_range"] = self.get_stat("minion_range", base=4)
            return stats

        def get_description(self):
            return ("Summons a choir of [{num_summons}:num_summons] angelic singers.\n"
                    "The singers have [{minion_health}_HP:minion_health], [{shields}_SH:shields], and immunity to [fire] and [holy] damage.\n"
                    "Each turn the angels automatically sing, dealing [2_fire:fire] and [2_holy:holy] damage to all [undead], [demon], and [dark] enemies in a [{radius}_tile:radius] radius. This damage is fixed, and cannot be increased using shrines, skills, or buffs.\n"
                    "[Living] and [holy] allies in the song's radius except the Wizard are healed for [{heal}_HP:heal].\n"
                    "The angels vanish after [{minion_duration}:minion_duration] turns.").format(**self.fmt_dict())

        def cast(self, x, y):

            fallen = self.get_stat("fallen")
            health = self.get_stat('minion_health')
            shields = self.get_stat('shields')
            duration = self.get_stat('minion_duration')
            heal = self.get_stat('heal')
            radius = self.get_stat('radius')
            cacophony_damage = self.get_stat("minion_damage", base=7)
            hellfire_damage = self.get_stat("minion_damage", base=4)
            minion_range = self.get_stat("minion_range", base=4)

            for _ in range(self.get_stat('num_summons')):
                angel = AngelicSinger()
                angel.name = "Angelic Singer"
                angel.max_hp = health
                angel.shields = shields
                angel.buffs.append(AngelSongBuff(heal, radius))

                angel.flying = True
                angel.tags = [Tags.Holy]
                angel.resists[Tags.Holy] = 100
                angel.resists[Tags.Fire] = 100
                angel.resists[Tags.Poison] = 100
                
                if fallen:
                    angel.name = "Fallen Angelic Singer"
                    angel.asset_name = "fallen_angel"
                    angel.resists[Tags.Dark] = 100
                    angel.tags.append(Tags.Demon)
                    cacophony = WailOfPain()
                    cacophony.damage = cacophony_damage
                    cacophony.radius = radius
                    angel.spells = [cacophony, SimpleRangedAttack(name="Hellfire", damage=hellfire_damage, damage_type=Tags.Fire, range=minion_range)]

                angel.turns_to_death = duration

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
            self.upgrades["clinging"] = (1, 4, "Clinging Darkness", "When affecting an enemy, this spell now inflicts [blind] for [2_turns:duration], which stacks in duration with pre-existing [blind] it has.")
            self.upgrades["holy"] = (1, 4, "Holy Night", "While Darkness is active and you are [blind], [demon] and [undead] enemies take [2_holy:holy] damage each turn.\nThis damage is fixed, and cannot be increased using shrines, skills, or buffs.", "night")
            self.upgrades["conceal"] = (1, 6, "Concealing Night", "While Darkness is active and you are [blind], whenever you or one of your [demon] or [undead] minions is about to be dealt damage, it has a 50% chance to negate that damage.\nDamage negation activates before [SH:shields].", "night")
            self.upgrades["fractal"] = (1, 7, "Fractal Night", "While Darkness is active and you are [blind], half of all [dark] damage dealt to enemies is redealt as [dark] damage.\nThis uses damage values before resistances, and triggers itself, but rounds down, stopping at 1 damage.", "night")

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
            self.upgrades["rot"] = (1, 4, "Mind Rot", "If the target takes [arcane] damage from this spell and dies, summon a void imp and an insanity imp near it.\nIf the target takes [dark] damage from this spell and dies, summon a rot imp near it.")

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

            self.damage = 40

            self.upgrades['max_charges'] = (2, 2)
            self.upgrades['damage'] = (40, 3)
            self.upgrades['check_cur_hp'] = (1, 4, 'Brute Force', 'Dominate enemies based on current HP instead of maximum HP.')
            self.upgrades["mass"] = (1, 6, "Mass Dominate", "When cast, Dominate now also affects all eligible units with the same name as the target within [{radius}_tiles:radius].")
            self.upgrades["heal"] = (1, 3, "Recruitment Bonus", "The target enemy is now healed to full HP after being dominated, and all of its debuffs are dispelled.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=3)
            return stats

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return False
            if unit.team == self.caster.team:
                return unit.has_buff(BerserkBuff)
            hp = unit.cur_hp if self.get_stat('check_cur_hp') else unit.max_hp
            return hp <= self.get_stat('damage')

        def get_impacted_tiles(self, x, y):
            points = [Point(x, y)]
            damage = self.get_stat("damage")
            check_cur_hp = self.get_stat("check_cur_hp")
            origin = self.caster.level.get_unit_at(x, y)
            if origin and self.get_stat("mass"):
                for unit in self.caster.level.get_units_in_ball(origin, self.get_stat("radius", base=3)):
                    if unit is origin or unit.name != origin.name:
                        continue
                    if unit.team == self.caster.team:
                        if unit.has_buff(BerserkBuff):
                            points.append(Point(unit.x, unit.y))
                        continue
                    if (unit.cur_hp if check_cur_hp else unit.max_hp) <= damage:
                        points.append(Point(unit.x, unit.y))
            return points

        def cast(self, x, y):
            heal = self.get_stat("heal")
            for point in self.get_impacted_tiles(x, y):
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if not unit:
                    continue
                if unit.team == self.caster.team:
                    buff = unit.get_buff(BerserkBuff)
                    if buff:
                        unit.remove_buff(buff)
                        self.caster.level.show_effect(unit.x, unit.y, Tags.Arcane)
                    continue
                self.caster.level.show_effect(unit.x, unit.y, Tags.Arcane)
                unit.team = self.caster.team
                unit.source = self
                unit.level.event_manager.raise_event(EventOnUnitPreAdded(unit), unit)
                unit.level.event_manager.raise_event(EventOnUnitAdded(unit), unit)
                if heal:
                    for buff in unit.buffs:
                        if buff.buff_type == BUFF_TYPE_CURSE:
                            unit.remove_buff(buff)
                    unit.deal_damage(-unit.max_hp, Tags.Heal, self)
            yield

        def get_description(self):
            return ("Target enemy unit with [{damage}:damage] max HP or lower becomes your minion. The HP threshold benefits from your bonuses to [damage].\n"
                    "This counts as summoning, and the dominated enemy counts as a minion summoned by this spell.\n"
                    "Allies with [berserk] can also be targeted, which removes [berserk] from them.").format(**self.fmt_dict())

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

            self.upgrades['meltflame'] = (1, 4, "Melting Flame", "Flame Burst now passes through walls, and melts walls on affected tiles.", "flame")
            self.upgrades['healflame'] = (1, 4, "Phoenix Flame", "Flame Burst heals allied units instead of damaging them.\nThe wizard cannot be healed this way.", "flame")
            self.upgrades['spreadflame'] = (1, 7, "Spreading Flame", "Each cast of Flame Burst consumes all remaining charges, counting as casting the spell once per charge consumed.\nFor each charge consumed, Flame Burst gets +1 radius and +1 damage.\nSlain enemies create additional explosions with half radius and damage.", "flame")

        def get_impacted_tiles(self, x, y):
            radius = self.get_stat('radius')
            if self.get_stat('spreadflame'):
                radius += self.cur_charges
            return [p for stage in Burst(self.caster.level, Point(x, y), radius, ignore_walls=self.get_stat("meltflame")) for p in stage]

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
                charges = self.cur_charges
                self.cur_charges = 0
                for _ in range(charges):
                    self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)

            to_melt = set([Point(self.caster.x, self.caster.y)])
            slain = []

            heal = self.get_stat("healflame")
            melt = self.get_stat("meltflame")

            stagenum = 0
            for stage in Burst(self.caster.level, Point(x, y), radius, ignore_walls=melt):
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
                        if self.caster.level.tiles[p.x][p.y].is_wall():
                            self.caster.level.make_floor(p.x, p.y)
                        
                yield

            if self.get_stat('spreadflame'):
                for unit in slain:
                    self.owner.level.queue_spell(self.cast(unit.x, unit.y, secondary=True, last_damage=damage, last_radius=radius))

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
            self.breath_damage = 7
            self.minion_health = 16

            # Only for the purpose of shrines.
            self.minion_damage = 7

            self.upgrades['minion_range'] = (6, 3)
            self.upgrades['breath_damage'] = (7, 4)
            self.upgrades["splitting"] = (1, 4, "Splitting", "Upon reaching 0 HP, the hydra splits into a frost hydra and a fire hydra.\nEach hydra inherits one of the frostfire hydra's elements and resistances. Its beam only deals damage of that element, and has a [2_turns:duration] cooldown.")
            self.upgrades["dragon_mage"] = (1, 6, "Dragon Mage", "The hydra will cast Melt on the target of its fire beam, and Freeze on the target of its ice beam.\nThese spells gains all of your upgrades and bonuses.")

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["beam_damage"] = self.get_stat("minion_damage") + self.get_stat("breath_damage", base=0)
            return stats

        def get_description(self):
            return ("Summon a frostfire hydra.\n"
                    "The hydra has [{minion_health}_HP:minion_health], and is stationary.\n"
                    "The hydra has a beam attack which deals [{breath_damage}_damage:damage] damage with a [{minion_range}_tile:minion_range] range. Its damage type alternates between [fire] and [ice] each turn.\n"
                    "The hydra's beam is considered a breath weapon.").format(**self.fmt_dict())

        def get_frost_hydra(self):
            unit = Unit()
            unit.source = self
            set_hydra_stats(self, unit, hydra_type=HYDRA_FROST)
            unit.spells = [IceHydraBeam(self, unit)]
            return unit

        def get_fire_hydra(self):
            unit = Unit()
            unit.source = self
            set_hydra_stats(self, unit, hydra_type=HYDRA_FIRE)
            unit.spells = [FireHydraBeam(self, unit)]
            return unit

        def set_hydra_stats(self, unit, hydra_type=HYDRA_FROSTFIRE):

            unit.max_hp = self.get_stat("minion_health")

            if hydra_type == HYDRA_FROST:
                unit.name = "Frost Hydra"
                unit.asset = ["UnderusedOptions", "Units", "frost_hydra"]
            elif hydra_type == HYDRA_FIRE:
                unit.name = "Fire Hydra"
                unit.asset = ["UnderusedOptions", "Units", "fire_hydra"]
            else:
                unit.name = "Frostfire Hydra"
                unit.asset_name = 'fire_and_ice_hydra'

            unit.stationary = True
            unit.tags = [Tags.Dragon]
            
            if hydra_type == HYDRA_FROSTFIRE or hydra_type == HYDRA_FROST:
                unit.tags.append(Tags.Ice)
                unit.resists[Tags.Ice] = 100
            
            if hydra_type == HYDRA_FROSTFIRE or hydra_type == HYDRA_FIRE:
                unit.tags.append(Tags.Fire)
                unit.resists[Tags.Fire] = 100

        def cast_instant(self, x, y):
            unit = Unit()
            set_hydra_stats(self, unit)
            beam = FrostfireHydraBeam(self, unit)
            unit.spells = [beam]
            unit.buffs = [FrostfireHydraBuff(beam)]
            if self.get_stat("splitting"):
                unit.buffs.extend([RespawnAs(lambda: get_frost_hydra(self)), RespawnAs(lambda: get_fire_hydra(self))])
            self.summon(unit, Point(x, y))

    if cls is CallSpirits:

        def on_init(self):
            self.tags = [Tags.Dark, Tags.Conjuration, Tags.Sorcery]
            self.name = "Ghostball"
            self.radius = 1
            self.minion_damage = 1
            self.minion_health = 4
            self.minion_duration = 14
            self.max_charges = 6
            self.level = 3
            self.damage = 11

            self.upgrades['radius'] = (1, 3)
            self.upgrades['minion_duration'] = (15, 2)
            self.upgrades['minion_damage'] = (3, 3)
            self.upgrades["possession"] = (1, 6, "Possession", "Units in the area of Ghostball are now possessed for a duration equal to this spell's [minion_duration:minion_duration], which can stack.\nIf the effect is removed prematurely, such as when the possessed unit dies, summon a ghost near it with duration equal to the remaining duration of possession.\nA possessed enemy takes [dark] damage each turn equal to this spell's [minion_damage:minion_damage].\nA possessed ally instead has melee retaliation dealing the same amount of [dark] damage to enemies.")
            self.upgrades['king'] = (1, 5, "Ghost King", "A Ghost King is summoned at the center of the ghost ball.\nIf you have the Possession upgrade, the central possessed unit will summon 2 ghost gates every [10_turns:cooldown], and summon a Ghost King if possession wears off prematurely.", "center summon")
            self.upgrades['mass'] = (1, 4, "Ghost Mass", "A Ghostly Mass is summoned at the center of the ghost ball.\nIf you have the Possession upgrade, the central possessed unit will summon a Ghostly Mass if possession wears off prematurely, and 8 ghosts if it wears off naturally.", "center summon")

        def cast_instant(self, x, y):

            king = self.get_stat('king')
            mass = self.get_stat('mass')
            possession = self.get_stat("possession")
            duration = self.get_stat('minion_duration')
            damage = self.get_stat('damage')
            points = self.caster.level.get_points_in_ball(x, y, self.get_stat('radius'))
            
            for point in points:
                
                if not self.caster.level.tiles[point.x][point.y].can_see:
                    continue
                unit = self.caster.level.get_unit_at(point.x, point.y)
                center = point.x == x and point.y == y
                
                if not unit:
                    ghost = Ghost()
                    if center:
                        if king:
                            ghost = GhostKing()
                        elif mass:
                            ghost = GhostMass()
                    ghost.turns_to_death = duration
                    apply_minion_bonuses(self, ghost)
                    self.summon(ghost, point)

                else:
                    if are_hostile(self.caster, unit):
                        if possession:
                            unit.apply_buff(PossessedEnemy(self, king=center and king, mass=center and mass), duration)
                        unit.deal_damage(damage, Tags.Dark, self)
                    else:
                        if possession:
                            unit.apply_buff(PossessedAlly(self, king=center and king, mass=center and mass), duration)
                        self.caster.level.show_effect(point.x, point.y, Tags.Dark)

    if cls is SummonGiantBear:

        def on_init(self):
            self.max_charges = 5
            self.name = "Giant Bear"
            self.minion_health = 65
            self.minion_damage = 10
            
            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 3

            self.minion_attacks = 1
            self.upgrades['minion_attacks'] = (1, 3)
            self.upgrades['venom'] = (1, 4, "Venom Bear", "Summons a venom bear instead of a giant bear.\nThe venom bear's melee attack inflicts [poison] for [{duration}_turns:duration], which stacks in duration with the target's existing [poison], and heals for [1_HP:heal] whenever any unit takes [poison] damage.", "species")
            self.upgrades['blood'] = (1, 5, "Blood Bear", "Summons a blood bear instead of a giant bear.\nThe blood bear is a [demon], and gains bloodrage for [{duration}_turns:duration] with each melee attack.", "species")
            self.upgrades["giant"] = (1, 7, "True Giant", "The bear grows to gargantuan size. Its HP is multiplied by 6, and its melee damage multiplied by 2.")

            self.must_target_walkable = True
            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration", base=10)
            return stats

        def cast(self, x, y):

            bear = Unit()
            bear.max_hp = self.get_stat('minion_health')
            
            bear.name = "Bear"
            bear.asset = ["UnderusedOptions", "Units", "bear"]
            bear.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))

            bear.tags = [Tags.Living, Tags.Nature]

            if self.get_stat('venom'):
                bear.name = "Venom Bear"
                bear.asset = ["UnderusedOptions", "Units", "venom_bear"]
                bear.resists[Tags.Poison] = 100
                bear.tags = [Tags.Living, Tags.Poison, Tags.Nature]
                melee = SimpleMeleeAttack(damage=self.get_stat('minion_damage'))
                def stack_poison(caster, target):
                    duration = caster.get_stat(self.get_stat("duration", base=10), melee, "duration")
                    existing = target.get_buff(Poison)
                    if existing:
                        existing.turns_left += duration
                    else:
                        target.apply_buff(Poison(), duration)
                melee.onhit = stack_poison
                melee.name = "Poison Bite"
                melee.description = ""
                melee.get_description = lambda: "Inflicts duration-stacking poison for %i turns with each attack.%s" % (bear.get_stat(self.get_stat("duration", base=10), melee, "duration"), (" Attacks %i times." % melee.attacks) if melee.attacks > 1 else "")
                bear.spells = [melee]
                bear.buffs = [VenomBeastHealing()]

            elif self.get_stat('blood'):
                bear = BloodBear()
                bear.asset = ["UnderusedOptions", "Units", "blood_bear"]
                melee = bear.spells[0]
                melee.onhit = lambda caster, target: caster.apply_buff(BloodrageBuff(3), caster.get_stat(self.get_stat("duration", base=10), melee, "duration"))
                melee.name = "Frenzy Bite"
                melee.description = ""
                melee.get_description = lambda: "Gain +3 damage for %i turns with each attack.%s" % (bear.get_stat(self.get_stat("duration", base=10), melee, "duration"), (" Attacks %i times." % melee.attacks) if melee.attacks > 1 else "")
                apply_minion_bonuses(self, bear)
            
            bear.spells[0].attacks = self.get_stat('minion_attacks')

            if self.get_stat("giant"):
                bear.max_hp *= 6
                bear.spells[0].damage *= 2
                bear.name = "Giant " + bear.name
                bear.asset[2] += "_giant"

            self.summon(bear, Point(x, y))
            yield

    if cls is VenomBeastHealing:

        def on_damage(self, evt):
            if evt.damage_type != Tags.Poison:
                return
            self.owner.deal_damage(-1, Tags.Heal, self)
        
        def get_tooltip(self):
            return "Heals for 1 HP whenever a unit takes poison damage."

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
            self.upgrades["fractal"] = (1, 6, "Fractal Cross", "Each tile in an affected horizontal line has a 10% chance to create a vertical line, and each tile in an affected vertical line has a 10% chance to create a horizontal line.\nEach line can create at most one additional line.")

            self.level = 3

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["length"] = self.get_stat("radius")*2 + 1
            return stats

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage and [{damage}_holy:holy] damage in a vertical line and in a horizontal line, each [{length}_tiles:radius] long. The caster is unaffected.\n"
                    "The lines intersect at the target point, which is hit by both lines.\n"
                    "[Stun] [demon] and [undead] units in the affected area for [{duration}_turns:duration].").format(**self.fmt_dict())

        def hit_line(self, x, y, horizontal):
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            rad = self.get_stat('radius')
            fractal = self.get_stat("fractal")
            branched = False

            if horizontal:
                line = range(x - rad, x + rad + 1)
            else:
                line = range(y - rad, y + rad + 1)
            
            for i in line:

                if horizontal:
                    p_x = i
                    p_y = y
                else:
                    p_x = x
                    p_y = i

                if not self.caster.level.is_point_in_bounds(Point(p_x, p_y)):
                    continue

                unit = self.caster.level.get_unit_at(p_x, p_y)
                if unit is self.caster:
                    self.caster.level.show_effect(p_x, p_y, Tags.Fire)
                    self.caster.level.show_effect(p_x, p_y, Tags.Holy)
                else:
                    self.caster.level.deal_damage(p_x, p_y, damage, Tags.Fire, self)
                    self.caster.level.deal_damage(p_x, p_y, damage, Tags.Holy, self)
                unit = self.caster.level.get_unit_at(p_x, p_y)
                if unit and [tag for tag in [Tags.Demon, Tags.Undead] if tag in unit.tags]:
                    unit.apply_buff(Stun(), duration)
                
                if fractal and not branched and random.random() < 0.1:
                    branched = True
                    self.caster.level.queue_spell(hit_line(self, p_x, p_y, not horizontal))
                
                yield

        def cast(self, x, y):
            self.caster.level.queue_spell(hit_line(self, x, y, True))
            self.caster.level.queue_spell(hit_line(self, x, y, False))
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
            self.upgrades["riposte"] = (1, 4, "Divine Riposte", "While Holy Armor is active, if you pass your turn, you will retaliate for [{damage}_holy:holy] damage whenever an enemy damages you, until the beginning of your next turn.")

            self.range = 0

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["damage"] = self.get_stat("damage", base=18)
            return stats

        def cast_instant(self, x, y):
            self.caster.apply_buff(HolyArmorBuff(self), self.get_stat('duration'))

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

            self.radius = 4
            self.upgrades['radius'] = (2, 2)
            self.upgrades['duration'] = (6, 3)
            self.upgrades['damage'] = (10, 3)
            self.upgrades["holy"] = (1, 5, "Divine Halo", "Lightning Halo also deals [holy] damage.")
            self.upgrades["repel"] = (1, 4, "Repelling Halo", "Enemies inside the halo are pushed away by [1_tile:radius] each turn until they are at the edge, before calculating whether they take damage.")

        def get_description(self):
            return ("Each turn, each enemy in a [{radius}_tile:radius] radius has a 1/[{radius}:radius] chance per tile away from you to take [{damage}_lightning:lightning] damage.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

    if cls is LightningHaloBuff:

        def __init__(self, spell):
            Buff.__init__(self)
            self.spell = spell
            self.name = "Lightning Halo"
            self.buff_type = BUFF_TYPE_BLESS
            self.asset = ['status', 'lightning_halo']
            self.stack_type = STACK_REPLACE
            self.damage = self.spell.get_stat("damage")
            self.holy = self.spell.get_stat("holy")
            self.repel = self.spell.get_stat("repel")

        def on_advance(self):
            if self.repel:
                for unit in self.owner.level.get_units_in_ball(self.owner, self.radius):
                    if not are_hostile(unit, self.owner) or distance(unit, self.owner) >= self.radius - 1:
                        continue
                    mods.Bugfixes.Bugfixes.push(unit, self.owner, 1)
            self.owner.level.show_effect(0, 0, Tags.Sound_Effect, 'sorcery_ally')
            for p in self.spell.get_impacted_tiles(self.owner.x, self.owner.y):
                self.owner.level.show_effect(p.x, p.y, Tags.Lightning)
                if self.holy:
                    self.owner.level.show_effect(p.x, p.y, Tags.Holy)
            for u in self.owner.level.get_units_in_ball(self.owner, self.radius):
                if not are_hostile(u, self.owner) or random.random() >= math.ceil(distance(u, self.owner))/self.radius:
                    continue
                u.deal_damage(self.damage, Tags.Lightning, self.spell)
                if self.holy:
                    u.deal_damage(self.damage, Tags.Holy, self.spell)

    if cls is MercurialVengeance:

        def on_init(self):
            self.owner_triggers[EventOnDeath] = self.on_death
            self.color = Tags.Metallic.color
            self.description = "If an enemy kills this unit, it is inflicted with Mercurize."

        def on_death(self, evt):
            if evt.damage_event and evt.damage_event.source and evt.damage_event.source.owner and are_hostile(evt.damage_event.source.owner, self.owner):
                evt.damage_event.source.owner.apply_buff(MercurizeBuff(self.spell), self.spell.get_stat("duration"))

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
            self.upgrades['noxious_aura'] = (1, 5, "Toxic Fumes", "Quicksilver Geists have a noxious aura that deals [1_poison:poison] damage to enemy units within [{radius}_tiles:radius] each turn.\nThis aura gains bonus [radius] equal to the square root of 10% of the geist's initial max HP, rounded up.")
            self.upgrades['vengeance'] = (1, 5, "Mercurial Vengeance", "When a Quicksilver Geist is killed by an enemy, its killer is affliected with Mercurize.")
            self.upgrades["friendly"] = (1, 2, "Mercurial Fortitude", "Mercurize now lasts indefinitely and is considered a buff if applied to one of your minions, instead healing it each turn by an amount equal to this spell's [damage] stat.\nThis still allows the minion to spawn a geist on death.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=2)
            return stats

        def cast_instant(self, x, y):
            for p in self.owner.level.get_points_in_line(self.caster, Point(x, y))[1:-1]:
                self.owner.level.show_effect(p.x, p.y, Tags.Dark, minor=True)
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                buff = MercurizeBuff(self)
                duration = self.get_stat('duration')
                if self.get_stat("friendly") and not are_hostile(unit, self.caster):
                    buff.buff_type = BUFF_TYPE_BLESS
                    duration = 0
                unit.apply_buff(buff, duration)

    if cls is MercurizeBuff:

        def __init__(self, spell):
            self.spell = spell
            self.damage = spell.get_stat("damage")
            self.dtypes = [Tags.Physical, Tags.Poison]
            if spell.get_stat("dark"):
                self.dtypes.append(Tags.Dark)
            Buff.__init__(self)

        def on_advance(self):
            if self.buff_type != BUFF_TYPE_CURSE:
                self.owner.deal_damage(-self.damage, Tags.Heal, self.spell)
                return
            for dtype in self.dtypes:
                self.owner.deal_damage(self.damage, dtype, self.spell)

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
                geist.buffs.append(DamageAuraBuff(damage=1, damage_type=Tags.Poison, radius=self.spell.get_stat("radius", base=2 + math.ceil(math.sqrt(geist.max_hp/10)))))
            if self.spell.get_stat('vengeance'):
                geist.buffs.append(MercurialVengeance(self.spell))
            self.owner.level.queue_spell(do_summon(self, geist))

        def do_summon(self, geist):
            self.spell.summon(geist, target=self.owner)
            yield

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

    if cls is NightmareSpell:

        def on_init(self):

            self.range = 0
            self.max_charges = 2
            self.name = "Nightmare Aura"
            self.aura_damage = 2
            self.radius = 7
            self.duration = 30

            self.stats.append('aura_damage')

            self.upgrades['radius'] = (3, 2)
            self.upgrades['duration'] = 15
            self.upgrades['max_charges'] = (4, 2)

            self.upgrades['dark_dream'] = (1, 5, "Dark Dream", "Upon ending, summon an old witch for every 25 damage dealt by the aura for [{minion_duration}_turns:minion_duration].\nOld witches fly, have life-draining ranged attacks dealing [dark] damage, and can summon temporary ghosts.", "dream")
            self.upgrades['electric_dream'] = (1, 5, "Electric Dream", "Upon ending, summon an aelf for every 25 damage dealt by the aura for [{minion_duration}_turns:minion_duration].\nAelves have melee attacks dealing [dark] damage, and weak but very long-ranged attacks dealing [lightning] damage.", "dream")
            self.upgrades['fever_dream'] = (1, 5, "Fever Dream", "Upon ending, summon a flame rift for every 25 damage dealt by the aura for [{minion_duration}_turns:minion_duration].\nFlame rifts are stationary, randomly teleport, have ranged attacks dealing [fire] damage, and have a chance to summon fire bombers each turn.", "dream")
            self.upgrades["master"] = (1, 4, "Dream Master", "Nightmare Aura now begins with [{dream_bonus}:damage] damage already stored in its damage pool, for the purpose of its Dream upgrades.\nThis amount benefits 10 times from the [damage] bonuses of this spell.")

            self.tags = [Tags.Enchantment, Tags.Dark, Tags.Arcane]
            self.level = 3

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_duration"] = self.get_stat("minion_duration", base=9)
            stats["dream_bonus"] = self.get_stat("damage", base=10)*10
            return stats

    if cls is NightmareBuff:

        def __init__(self, spell):
            self.spell = spell
            DamageAuraBuff.__init__(self, damage=self.spell.aura_damage, radius=self.spell.get_stat('radius'), damage_type=[Tags.Arcane, Tags.Dark], friendly_fire=False)
            if spell.get_stat("master"):
                self.damage_dealt += spell.get_stat("damage", base=10)*10

        def on_unapplied(self):
            spawner = None

            if self.spell.get_stat("electric_dream"):
                spawner = Elf
            if self.spell.get_stat("dark_dream"):
                spawner = OldWitch
            if self.spell.get_stat("fever_dream"):
                spawner = FireSpawner
            if not spawner:
                return

            for _ in range(self.damage_dealt//25):
                unit = spawner()
                unit.turns_to_death = 9
                apply_minion_bonuses(self.spell, unit)
                self.spell.summon(unit, sort_dist=False, radius=self.radius)

    if cls is PainMirrorSpell:

        def on_init(self):
            self.name = "Pain Mirror"
            self.range = 0
            self.duration = 10

            self.level = 3

            self.max_charges = 5

            self.upgrades['duration'] = (10, 2)
            self.upgrades["false"] = (1, 6, "False Pain", "Pain Mirror now counts incoming damage twice. The first time counts the raw incoming damage before resistances and [SH:shields], and the second time counts actual damage taken.\nThe first count will trigger even if all of the incoming damage is resisted or blocked.")
            self.upgrades["masochism"] = (1, 3, "Masochism", "Damage inflicted by allies will cause Pain Mirror to deal double damage.")
            self.upgrades["deep"] = (1, 5, "Deep Pain", "Pain Mirror penetrates enemy [dark] resistances by a percentage equal to your percentage of missing HP.")

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
                    self.owner_triggers[EventOnPreDamaged] = self.on_damage
                self.masochism = self.source.get_stat("masochism")
                self.deep = self.source.get_stat("deep")
            self.owner_triggers[EventOnDamaged] = self.on_damage
            self.color = Tags.Dark.color
            self.stack_type = STACK_REPLACE

        def on_damage(self, event):
            damage = event.damage
            if damage <= 0:
                return
            if self.masochism and not(isinstance(event.source, Buff) and event.source.buff_type == BUFF_TYPE_CURSE) and event.source.owner and not are_hostile(event.source.owner, self.owner):
                damage *= 2
            self.owner.level.queue_spell(self.reflect(damage))

        def reflect(self, damage):
            penetration = math.ceil((self.owner.max_hp - self.owner.cur_hp)/self.owner.max_hp*100) if self.deep else 0
            for u in self.owner.level.get_units_in_los(self.owner):
                if are_hostile(self.owner, u):
                    u.deal_damage(damage, Tags.Dark, self.source or self, penetration=penetration)
            yield

    if cls is SealFate:

        def on_init(self):
            self.name = "Seal Fate"
            self.range = 8
            self.max_charges = 13
            self.tags = [Tags.Enchantment, Tags.Dark]
            self.level = 3
            self.can_target_empty = False

            self.damage = 160
            self.upgrades['range'] = 7
            self.upgrades['requires_los'] = (-1, 2, "Blindcasting", "Seal Fate can be cast without line of sight.")
            self.upgrades['damage'] = (80, 2)
            self.upgrades['spreads'] = (1, 4, "Spreading Curse", "When the curse is removed, it jumps to a random enemy in line of sight, prioritizing targets without Sealed Fate.\nIf its timer has reached 0, the timer of the new curse starts at 4 again; otherwise it retains its current timer.")
            self.upgrades["haste"] = (1, 2, "Hasten Doom", "When applying the curse to a target that already has Sealed Fate, the existing curse's timer is reduced by 1 turn.")

        def get_description(self):
            return ("Permanently curse the target with Sealed Fate.\n"
                    "The curse has a timer that starts at 4 and ticks down by 1 per turn. When it reaches 0, the debuff removes itself to deal [{damage}_dark:dark] damage to the target.\n"
                    "The timer is treated as a per-turn effect rather than the curse's remaining duration, and cannot be refreshed.\n").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(SealedFateBuff(self, 4))

    if cls is SealedFateBuff:

        def __init__(self, spell, timer):
            Buff.__init__(self)
            self.spell = spell
            self.timer = timer
            self.name = "Sealed Fate (%i)" % self.timer
            self.buff_type = BUFF_TYPE_CURSE
            self.asset = ['status', 'sealed_fate']

        def on_attempt_apply(self, owner):
            existing = owner.get_buff(SealedFateBuff)
            if existing and self.spell.get_stat("haste"):
                existing.on_advance()
            return not existing

        def on_advance(self):
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 4
                self.owner.deal_damage(self.spell.get_stat("damage"), Tags.Dark, self.spell)
                self.owner.remove_buff(self)
            self.name = "Sealed Fate (%i)" % self.timer

        def on_unapplied(self):
            if not self.spell.get_stat("spreads"):
                return
            possible_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if u is not self.owner and are_hostile(u, self.spell.owner)]
            uncursed_targets = [u for u in possible_targets if not u.has_buff(SealedFateBuff)]
            if uncursed_targets:
                targets = uncursed_targets
            else:
                targets = possible_targets
            if targets:
                target = random.choice(targets)
                target.apply_buff(SealedFateBuff(self.spell, self.timer))

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
            self.upgrades["golem"] = (1, 7, "Shrapnel Golem", "Shrapnel Blast instead summons a shrapnel golem on the target tile, which is a [fire] [metallic] [construct] minion with [{minion_health}_HP:minion_health].\nThe golem can fire shards that deal [physical] damage, which counts as damage dealt by this spell and inherits all of this spell's stats.\nIt can fire the same number of shards as this spell otherwise can before dying, which will then deal [fire] damage from this spell to all enemies in the radius of the initial explosion of Shrapnel Blast.\nThe golem has a 75% chance to immediately act again after firing a shard.", "behavior")
            self.upgrades['homing'] = (1, 7, "Magnetized Shards", "The shrapnel shards now only target enemies.\nIf no enemies are in the affected area, no more shards will be fired.\nThe initial explosion also no longer damages allies.", "behavior")
            self.upgrades["chasm"] = (1, 4, "Unearth", "This spell can now be cast on chasms.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_health"] = self.get_stat("minion_health", base=50)
            return stats

        def get_description(self):
            return ("Detonate target wall tile.\n"
                    "All units in a [{radius}_tile:radius] radius take [{damage}_fire:fire] damage.\n"
                    "The explosion fires [{num_targets}_shards:num_targets] at random tiles in the same radius.\n"
                    "Each shard deals [{damage}_physical:physical] damage.").format(**self.fmt_dict())

        def can_cast(self, x, y):
            if not Spell.can_cast(self, x, y):
                return False
            if not self.caster.level.tiles[x][y].is_wall():
                return self.get_stat("chasm") and self.caster.level.tiles[x][y].is_chasm
            return True

        def cast(self, x, y):
            
            damage = self.get_stat('damage')
            homing = self.get_stat("homing")
            num_shards = self.get_stat('num_targets')
            radius = self.get_stat('radius')
            self.caster.level.make_floor(x, y)

            if not self.get_stat("golem"):
                possible_targets = list(self.caster.level.get_points_in_ball(x, y, radius))
                for p in possible_targets:
                    unit = self.caster.level.get_unit_at(p.x, p.y)
                    if not unit or (homing and not are_hostile(unit, self.caster)):
                        self.caster.level.show_effect(p.x, p.y, Tags.Fire)
                    else:
                        unit.deal_damage(damage, Tags.Fire, self)
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
                        self.caster.level.deal_damage(target.x, target.y, damage, Tags.Physical, self)
                        yield
            else:
                golem = Unit()
                golem.name = "Shrapnel Golem"
                golem.asset_name = "golem_spike"
                golem.tags = [Tags.Fire, Tags.Metallic, Tags.Construct]
                golem.max_hp = self.get_stat("minion_health", base=50)
                golem.spells = [ShrapnelSpell(self)]
                golem.buffs = [ShrapnelGolemExplosion(self)]
                self.summon(golem, target=Point(x, y))

        def get_impacted_tiles(self, x, y):
            if self.get_stat("golem"):
                return [Point(x, y)]
            return Spell.get_impacted_tiles(self, x, y)

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
            self.upgrades["eternity"] = (1, 7, "Eternity", "Suspend Mortality now adds reincarnations as a passive effect, which is permanent and cannot be dispelled.")

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
            self.upgrades["seeker"] = (1, 3, "Underworld Seeker", "You can now spend 1 extra charge to cast this spell even if you are not next to a chasm, counting as casting the spell an additional time.")
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
                self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)
            self.caster.level.act_move(self.caster, x, y, teleport=True)
            if self.get_stat("fauna"):
                unit_type = random.choice([DisplacerBeastGhost, MantisGhost, GhostToad, WormBallGhostly, GoatHeadGhost])
                if unit_type != WormBallGhostly:
                    unit = unit_type()
                    apply_minion_bonuses(self, unit)
                else:
                    unit = WormBallGhostly(self.get_stat("minion_health", base=10))
                self.summon(unit, radius=5)

    if cls is VoidBeamSpell:

        def on_init(self):
            self.range = 15
            self.max_charges = 7
            self.name = "Void Beam"
            self.requires_los = False
            self.damage = 25
            
            self.tags = [Tags.Arcane, Tags.Sorcery]
            self.level = 3

            self.upgrades['damage'] = (21, 5)
            self.upgrades['range'] = (5, 2)
            self.upgrades['max_charges'] = (3, 2)
            self.upgrades["sniper"] = (1, 4, "Void Sniper", "Void Beam deals additional damage to targets equal to twice their distances from the caster, rounded down.")

        def cast(self, x, y):
            damage = self.get_stat('damage')
            sniper = self.get_stat("sniper")
            
            for point in self.aoe(x, y):
                # Kill walls
                if not self.caster.level.tiles[point.x][point.y].can_see:
                    self.caster.level.make_floor(point.x, point.y)
                # Deal damage
                self.caster.level.deal_damage(point.x, point.y, damage + (math.floor(2*distance(point, self.caster)) if sniper else 0), Tags.Arcane, self)
            yield

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

            self.upgrades['range'] = (5, 2)
            self.upgrades['minion_damage'] = (9, 3)
            self.upgrades['orb_walk'] = (1, 3, "Void Walk", "Targeting an existing Void Orb with another detonates it, dealing its damage and melting walls in a radius equal to twice the orb's radius.\nYou are then teleported to that location if possible.\nThis has a chance to refund a charge of Void Orb, equal to the orb's remaining duration divided by maximum duration.")
            self.add_upgrade(VoidOrbRedGiant())
            self.upgrades["dark"] = (1, 5, "Black Hole", "Each turn, Void Orb pulls all nearby enemies [1_tile:range] toward itself before dealing damage; the pull range is three times the orb's radius.\nVoid Orb also deals [dark] damage.")

        def on_orb_walk(self, existing):

            if random.random() < existing.turns_to_death/(self.get_stat("range") - 1):
                self.cur_charges = min(self.cur_charges + 1, self.get_stat("max_charges"))

            # Burst
            x = existing.x
            y = existing.y
            damage = self.get_stat('minion_damage')
            radius = self.get_stat("radius")

            dtypes = [Tags.Arcane]
            if self.get_stat("fire"):
                dtypes.append(Tags.Fire)
            if self.get_stat("dark"):
                dtypes.append(Tags.Dark)

            for stage in Burst(self.caster.level, Point(x, y), radius*2, ignore_walls=True):
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
            if self.get_stat("dark"):
                dtypes.append(Tags.Dark)
                units = [self.caster.level.get_unit_at(p.x, p.y) for stage in Burst(self.caster.level, next_point, radius*3, ignore_walls=True) for p in stage]
                units = [u for u in units if u and are_hostile(u, self.caster)]
                random.shuffle(units)
                for unit in units:
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
            return [p for stage in Burst(self.caster.level, orb, self.get_stat("radius")*2, ignore_walls=True) for p in stage]

        def get_description(self):
            return ("Summon a void orb next to the caster.\n"
                    "The orb melts deals [{minion_damage}_arcane:arcane] damage each turn and melts walls in a radius of [{radius}_tiles:radius].\n"
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
            self.upgrades["hailstorm"] = (1, 6, "Hailstorm", "If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt [ice] damage equal to twice the damage of this spell, and [frozen:freeze] for [1_turn:duration].")

        def cast(self, x, y):
            duration = self.get_stat('duration')
            damage = self.get_stat('damage')
            hailstorm = self.get_stat("hailstorm")
            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
                for p in stage:
                    if hailstorm:
                        existing = self.caster.level.tiles[p.x][p.y].cloud
                        if isinstance(existing, BlizzardCloud) or isinstance(existing, StormCloud):
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
            self.requires_los = False

            self.upgrades["range"] = (RANGE_GLOBAL, 3)
            self.upgrades["regrowth"] = (1, 5, "Bone Regrowth", "Each ally damaged by Bone Barrage gains regeneration for [{duration}_turns:duration], each turn recovering HP equal to 25% of the HP lost.")
            self.upgrades["ghost"] = (1, 5, "Ghost Bones", "Each ally also deals [{damage}_dark:dark] damage to the target, regardless of the amount of damage the ally took; this damage benefits from bonuses to [damage].\nAllies not in line of sight of the target will now also deal this additional [dark] damage to the target.")
            self.upgrades['animation'] = (1, 7, "Shambler Assembly", "Bone Barrage can target empty tiles.\nIf it does, it creates a bone shambler at that tile with HP equal to the total damage dealt to your minions.\nThe bone shambler splits into two bone shamblers with half its max HP when destroyed if its initial max HP is at least 8, and has a melee attack dealing [physical] damage equal to 1/4 of its initial max HP.\nIf you have the Bone Regrowth upgrade, the bone shambler has a passive regeneration that heals each turn for 1/8 of its initial max HP.\nIf you have the Ghost Bones upgrade, the bone shambler's melee attack deals additional [dark] damage equal to your number of minions at the time of casting this spell, plus [minion_damage:minion_damage] bonuses.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["damage"] = self.get_stat("damage", base=4)
            stats["duration"] = self.get_stat("duration", base=4)
            return stats

        def bolt(self, source, target, damage, bone, ghost):

            for point in Bolt(self.caster.level, source, target, find_clear=False):
                if bone:
                    self.caster.level.show_effect(point.x, point.y, Tags.Physical, minor=True)
                if ghost:
                    self.caster.level.show_effect(point.x, point.y, Tags.Dark, minor=True)
                yield True

            if bone:
                self.caster.level.deal_damage(target.x, target.y, damage, Tags.Physical, self)
            if ghost:
                self.caster.level.deal_damage(target.x, target.y, self.get_stat("damage", base=4), Tags.Dark, self)
            yield False

        def cast(self, x, y):
            bolts = []
            target = Point(x, y)
            unit = self.caster.level.get_unit_at(x, y)
            ghost = self.get_stat("ghost")
            regrowth = self.get_stat("regrowth")
            duration = self.get_stat("duration", base=4)

            total_damage = 0
            num_minions = 0
            for u in (self.caster.level.units):
                if u is self.caster:
                    continue
                if are_hostile(u, self.caster):
                    continue
                damage = 0
                num_minions += 1
                in_los = self.caster.level.can_see(x, y, u.x, u.y)
                if in_los:
                    damage = u.deal_damage(u.cur_hp//2, Tags.Physical, self)
                    total_damage += damage
                    if regrowth:
                        u.apply_buff(RegenBuff(damage//4), duration)
                elif not ghost:
                    continue

                bolts.append(self.bolt(u, target, damage, bone=in_los, ghost=ghost))

            while bolts:
                bolts = [b for b in bolts if next(b)]
                yield

            if not unit and self.get_stat('animation') and total_damage:
                monster = BoneBarrageBoneShambler(self, total_damage, num_minions)
                self.summon(monster, target=Point(x, y))

    if cls is ChimeraFarmiliar:

        def on_init(self):
            self.name = "Chimera Familiar"
            self.tags = [Tags.Chaos, Tags.Conjuration]
            self.level = 4
            self.max_charges = 4
            self.minion_health = 26
            self.minion_damage = 5
            self.minion_range = 5

            self.upgrades['resists'] = (1, 3, "Resistances", "The chimera gains [25_fire:fire] and [25_lightning:lightning] resistances. The fire lion and lightning snake it splits into gain [50_lightning:lightning] and [50_fire:fire] resistances respectively.\nAll minions summoned by this spell gain [100_physical:physical] resistance.")
            self.upgrades["casts"] = (1, 7, "Doublecast", "The chimera now copies two of your spells per turn.\nThe fire lion and lightning snake that the chimera transforms into upon reaching 0 HP can now also copy your spells.\nThe fire lion can only copy your [fire] and [chaos] spells.\nThe lightning snake can only copy your [lightning] and [chaos] spells.\nThe lion and snake can only copy one spell per turn.")
            self.add_upgrade(WildMetamorphosis())

            self.casts = 1
            self.must_target_walkable = True
            self.must_target_empty = True

        def get_description(self):
            return ("Summon a Chimera Familiar, which has [{minion_health}_HP:minion_health], [75_fire:fire] resistance, [75_lightning:lightning] resistance, and [fire] and [lightning] ranged attacks with [{minion_damage}:minion_damage] damage and [{minion_range}:minion_range] range.\n"
                    "Each turn, the chimera automatically copies [{casts}:sorcery] of your [fire], [lightning], or [chaos] [sorcery] spells that can be cast from its tile, preferring spells with the highest [max_charges:max_charges], consuming 1 charge from the spells copied. This counts as you casting the spell.\n"
                    "The chimera cannot channel different copies of the same spell simultaneously.").format(**self.fmt_dict())

        def get_lion(self):
            unit = RedLion()
            unit.name = "Lion Familiar"
            if self.get_stat("casts") > 1:
                unit.buffs.append(SpellConduitBuff(lightning=False))
            if self.get_stat("resists"):
                unit.resists[Tags.Lightning] = 50
                unit.resists[Tags.Physical] = 100
            return unit

        def get_snake(self):
            unit = GoldenSnake()
            unit.name = "Snake Familiar"
            if self.get_stat("casts") > 1:
                unit.buffs.append(SpellConduitBuff(fire=False))
            if self.get_stat("resists"):
                unit.resists[Tags.Fire] = 50
                unit.resists[Tags.Physical] = 100
            return unit

        def cast_instant(self, x, y):
            chimera = ChaosChimera()
            chimera.asset_name = "chaos_chimera"
            chimera.name = "Chimera Familiar"
            apply_minion_bonuses(self, chimera)
            chimera.buffs.append(SpellConduitBuff(casts=self.get_stat("casts")))
            if self.get_stat("resists"):
                chimera.resists[Tags.Fire] = 100
                chimera.resists[Tags.Lightning] = 100
                chimera.resists[Tags.Physical] = 100
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
            self.strikechance = 50
            self.can_target_empty = False

            self.upgrades['cascade_range'] = (4, 4)
            self.upgrades['resistance_debuff'] = (50, 2)
            self.upgrades['duration'] = (10, 3)
            self.upgrades["strikechance"] = (25, 6, "Strikechance")

        def can_cast(self, x, y):
            return Spell.can_cast(self, x, y)

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(curr_module.ConductanceBuff(self), self.get_stat("duration"))

        def get_description(self):
            return ("The target enemy loses [{resistance_debuff}_lightning:lightning] resistance.\n"
                    "Whenever [lightning] damage is dealt to a target with conductance, there is a [{strikechance}%:strikechance] chance to redeal the raw incoming damage, before counting resistances, to another random enemy in a [{cascade_range}_tile:cascade_range] burst, and apply conductance to that enemy for the same duration as the remaining duration of conductance on the original target.\n"
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

    if cls is DispersionFieldSpell:

        def on_init(self):
            self.name = "Dispersion Field"
            self.level = 4
            self.tags = [Tags.Enchantment, Tags.Arcane, Tags.Translocation]

            self.max_charges = 3
            self.duration = 7
            self.num_targets = 3

            self.range = 0
            self.radius = 6

            self.upgrades['num_targets'] = (2, 2)
            self.upgrades['duration'] = (5, 1)
            self.upgrades['max_charges'] = (5, 4)
            self.upgrades["channel"] = (1, 3, "Channeling Guard", "If you are channeling a spell, Dispersion Field will [stun] each affected enemy for [1_turn:duration] before teleporting it away.\nThe [stun] duration is fixed and unaffected by bonuses.")

    if cls is DispersionFieldBuff:

        def on_init(self):
            self.name = "Dispersion Field"
            self.description = "Teleport nearby enemies away each turn"
            self.color = Tags.Translocation.color
            self.stack_type = STACK_REPLACE
            self.radius = self.spell.get_stat("radius")
            self.channel = self.spell.get_stat("channel")

        def on_advance(self):
            tped = 0
            has_channel = self.owner.has_buff(ChannelBuff) if self.channel else False
            units = self.owner.level.get_units_in_ball(self.owner, self.radius)
            random.shuffle(units)
            for u in units:
                if not are_hostile(self.owner, u):
                    continue
                if has_channel:
                    u.apply_buff(Stun(), 1)

                possible_points = []
                for i in range(len(self.owner.level.tiles)):
                    for j in range(len(self.owner.level.tiles[i])):
                        if self.owner.level.can_stand(i, j, u):
                            possible_points.append(Point(i, j))

                if not possible_points:
                    continue

                target_point = random.choice(possible_points)

                self.owner.level.show_effect(u.x, u.y, Tags.Translocation)
                self.owner.level.act_move(u, target_point.x, target_point.y, teleport=True)
                self.owner.level.show_effect(u.x, u.y, Tags.Translocation)

                tped += 1
                if tped > self.spell.get_stat('num_targets'):
                    break

    if cls is EssenceFlux:

        def on_init(self):
            self.name = "Essence Flux"
            self.tags = [Tags.Arcane, Tags.Chaos, Tags.Enchantment]

            self.max_charges = 6
            self.level = 3
            self.range = 9
            self.radius = 4
            self.requires_los = False

            self.upgrades['radius'] = (3, 3)
            self.upgrades["imbalance"] = (1, 5, "Imbalanced Flux", "After affecting an enemy, the higher resistance of each pair will instead be set to the average of the pair.\nAfter affecting an ally, the lower resistance of each pair will instead be set to the average of the pair.")

        def get_impacted_tiles(self, x, y):
            return Spell.get_impacted_tiles(self, x, y)

        def get_description(self):
            return ("Swap the polarity of the resistances of all units in a [{radius}_tile:radius] radius except the caster.\n"
                    "[Fire] resistance is swapped with [ice].\n"
                    "[Lightning] resistance is swapped with [physical].\n"
                    "[Dark] resistance is swapped with [holy].\n"
                    "[Poison] resistance is swapped with [arcane].").format(**self.fmt_dict())

        def cast(self, x, y):
            imbalance = self.get_stat("imbalance")
            for unit in self.caster.level.get_units_in_ball(Point(x, y), self.get_stat("radius")):

                if unit is self.caster:
                    continue
                
                old_resists = unit.resists.copy()
                for e1, e2 in [
                    (Tags.Fire, Tags.Ice),
                    (Tags.Lightning, Tags.Physical),
                    (Tags.Dark, Tags.Holy),
                    (Tags.Poison, Tags.Arcane)]:

                    if old_resists[e1] == old_resists[e2]:
                        continue

                    if not imbalance:
                        unit.resists[e1] = old_resists[e2]
                        unit.resists[e2] = old_resists[e1]
                        color = e1.color if old_resists[e1] > old_resists[e2] else e2.color
                        self.caster.level.show_effect(unit.x, unit.y, Tags.Debuff_Apply, fill_color=color)
                    else:
                        average = math.ceil((old_resists[e1] + old_resists[e2])/2)
                        if are_hostile(unit, self.caster):
                            unit.resists[e1] = min(old_resists[e2], average)
                            unit.resists[e2] = min(old_resists[e1], average)
                            color = e1.color if old_resists[e1] > old_resists[e2] else e2.color
                            self.caster.level.show_effect(unit.x, unit.y, Tags.Debuff_Apply, fill_color=color)
                        else:
                            unit.resists[e1] = max(old_resists[e2], average)
                            unit.resists[e2] = max(old_resists[e1], average)
                            color = e1.color if old_resists[e1] < old_resists[e2] else e2.color
                            self.caster.level.show_effect(unit.x, unit.y, Tags.Buff_Apply, fill_color=color)
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
            self.upgrades["relentless"] = (1, 3, "Relentless Torment", "The tormentor gains a teleport attack that deals the same damage as its soul suck, with range equal to its soul suck range plus torment radius.")
            self.add_upgrade(FieryTormentorRemorse())

            self.must_target_walkable = True
            self.must_target_empty = True

        def cast_instant(self, x, y):

            if self.get_stat('frostfire'):
                unit = FrostfireTormentor()
            elif self.get_stat('ghostfire'):
                unit = GhostfireTormentor()
            else:
                unit = FieryTormentor()

            apply_minion_bonuses(self, unit)
            unit.max_hp = self.get_stat('minion_health')

            for s in unit.spells:
                if 'Torment' in s.name:
                    s.radius = self.get_stat('radius')

            unit.turns_to_death = self.get_stat('minion_duration')

            if self.get_stat("relentless"):
                leap = LeapAttack(damage=self.get_stat("minion_damage", base=2), damage_type=Tags.Dark, is_ghost=True, range=self.get_stat("minion_range") + self.get_stat("radius"))
                leap.name = "Soul Rush"
                unit.spells.append(leap)
            
            self.summon(unit, Point(x, y))

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
            self.upgrades["swap"] = (1, 3, "Lightning Swap", "Lightning Form will now cause you to swap places with the target unit if possible, when targeting an occupied tile.")
            self.upgrades["rod"] = (1, 4, "Lightning Rod", "While Lightning Form is active and your [lightning] resistance is at least 100, any attempt to deal [lightning] damage to you will cause this spell to deal the same damage to a random enemy in line of sight.\nThis upgrade cannot trigger itself.")

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
            self.upgrades["twice"] = (1, 5, "Strike Twice", "If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt [lightning] damage equal to the damage of this spell.\nIf you have the Strikechance upgrade, there is a 50% chance to deal damage again.")

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
                        if isinstance(existing, BlizzardCloud) or isinstance(existing, StormCloud):
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
            self.upgrades['range'] = (5, 2)
            self.upgrades["beam"] = (1, 5, "Anti-Particle Beam", "When casting this spell, every allied [orb] will shoot a beam at the target tile.\nEach beam deals damage of each damage type the orb is not immune to, multiplied by 100% minus the orb's resistance to that damage type. The base damage is equal to 4 times the orb's level, and does not harm allies.\nA beam melts through walls if its corresponding orb can melt through walls; otherwise it is stopped by the first wall it encounters.")

        def cast_instant(self, x, y, channel_cast=False):

            beam = self.get_stat("beam")
            dest = Point(x, y)

            units = list(self.caster.level.units)
            random.shuffle(units)

            for u in units:

                if u.team != self.caster.team:
                    continue
                buff = u.get_buff(OrbBuff)
                if not buff:
                    continue

                if beam:
                    if all(u.resists[tag] >= 100 for tag in u.resists.keys() if tag != Tags.Heal):
                        continue
                    melt = buff.spell.get_stat('melt_walls')
                    path = self.caster.level.get_points_in_line(u, dest)[1:]
                    for p in path:
                        if self.caster.level.tiles[p.x][p.y].is_wall():
                            if melt:
                                self.caster.level.make_floor(p.x, p.y)
                            else:
                                break
                        for tag in u.resists.keys():
                            if tag == Tags.Heal:
                                continue
                            if u.resists[tag] >= 100:
                                continue
                            unit = self.caster.level.get_unit_at(p.x, p.y)
                            if not unit or not are_hostile(unit, self.caster):
                                self.caster.level.show_effect(p.x, p.y, tag)
                            else:
                                unit.deal_damage(math.ceil(buff.spell.level*4*(100 - u.resists[tag])/100), tag, self)

                path = self.caster.level.get_points_in_line(u, dest)[1:]
                u.turns_to_death = len(path)
                buff.dest = dest

    if cls is Permenance:

        def on_init(self):
            self.max_charges = 4
            self.duration = 20
            self.name = "Permanence"
            self.tags = [Tags.Enchantment]
            self.level = 4
            self.range = 0
            self.upgrades['duration'] = (20, 3)
            self.upgrades["minion"] = (1, 5, "Minion Permanence", "Each turn, each of your temporary minions that has only 1 turn remaining has a 25% chance to become permanent.\nDoes not work on [orb] minions.")
            self.upgrades["max_charges"] = (4, 3)

        def cast_instant(self, x, y):
            buff = PermenanceBuff()
            buff.stack_type = STACK_REPLACE
            def make_permanent():
                for unit in self.caster.level.units:
                    if are_hostile(unit, self.caster) or unit.turns_to_death != 1 or unit.has_buff(OrbBuff) or random.random() >= 0.25:
                        continue
                    self.caster.level.show_effect(unit.x, unit.y, Tags.Translocation)
                    unit.turns_to_death = None
            if self.get_stat("minion"):
                buff.on_advance = make_permanent
            self.caster.apply_buff(buff, self.get_stat('duration'))

    if cls is PurityBuff:

        def on_init(self):
            self.name = "Purity"
            self.description = "Immune to debuffs."
            self.color = Tags.Holy.color
            self.asset = ['status', 'purity']
            self.stack_type = STACK_REPLACE
            self.aura = False
        
        def on_advance(self):
            if not self.aura:
                return
            units = [unit for unit in self.owner.level.units if unit.team == TEAM_PLAYER]
            if not units:
                return
            random.shuffle(units)
            for unit in list(units):
                debuffs = [buff for buff in unit.buffs if buff.buff_type == BUFF_TYPE_CURSE]
                if not debuffs:
                    continue
                unit.remove_buff(random.choice(debuffs))
                return

    if cls is PuritySpell:

        def on_init(self):
            self.name = "Purity"

            self.duration = 6
            self.level = 4
            self.max_charges = 4

            self.upgrades['duration'] = (6, 3)
            self.upgrades['max_charges'] = (4, 3)
            self.upgrades["aura"] = (1, 2, "Pure Aura", "Each turn, remove a random debuff from a random ally.")
            self.range = 0

            self.tags = [Tags.Holy, Tags.Enchantment]

        def cast_instant(self, x, y):
            buffs = list(self.caster.buffs)
            for b in buffs:
                if b.buff_type == BUFF_TYPE_CURSE:
                    self.caster.remove_buff(b)
            buff = PurityBuff()
            if self.get_stat("aura"):
                buff.aura = True
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
            self.upgrades["annihilation"] = (1, 7, "Annihilation Pulse", "Pyrostatic Pulse also deals [physical], [arcane], and [dark] damage.\nEach cast of Pyrostatic Pulse consumes an additional charge and counts as casting the spell twice.")

        def get_description(self):
            return ("Deal [{damage}_fire:fire] damage and [{damage}_lightning:lightning] damage in a beam and tiles adjacent to the beam.").format(**self.fmt_dict())

        def cast_instant(self, x, y):
            damage = self.get_stat("damage")
            dtypes = [Tags.Fire, Tags.Lightning]
            if self.get_stat("annihilation"):
                dtypes.extend([Tags.Physical, Tags.Arcane, Tags.Dark])
                self.cur_charges = max(0, self.cur_charges - 1)
                self.caster.level.event_manager.raise_event(EventOnSpellCast(self, self.caster, x, y), self.caster)
            for p in self.get_impacted_tiles(x, y):
                for dtype in dtypes:
                    self.caster.level.deal_damage(p.x, p.y, damage, dtype, self)

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
            self.bloodrage_bonus = 2

            self.upgrades['duration'] = (15, 3)
            self.upgrades["shot_cooldown"] = (-1, 4)
            self.upgrades["bloodrage_bonus"] = (1, 3)
            self.upgrades["feeding_frenzy"] = (1, 2, "Feeding Frenzy", "On each activation, each allied unit in line of sight of the target that has [bloodrage:demon] has a chance to gain another stack of [bloodrage:demon] for [{bloodrage_duration}_turns:duration].\nThe chance is equal to the percentage of the target's missing HP.\nThe strength of this bloodrage stack is equal to the strength of the strongest bloodrage stack on the unit.")
            self.upgrades["unending"] = (1, 5, "Unending Bloodrage", "When the target dies, the curse is applied to another random enemy in line of sight for its remaining duration.")
            
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

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["bloodrage_duration"] = self.get_stat("duration", base=10)
            return stats

        def get_description(self):
            return ("Curse a target in line of sight to attract bloodthirsty predators for [{duration}_turns:duration].\n"
                    "Every [{shot_cooldown}_turns:shot_cooldown], summon a blood vulture near the target, which is a [nature] [demon] minion with [{minion_health}_HP:minion_health] and attacks that deal [{minion_damage}_physical:physical] damage.\n"
                    "The blood vulture's melee attack grants itself [{bloodrage_duration}_turns:duration] of [bloodrage:demon] on hit, which increases all of its damage by [{bloodrage_bonus}:minion_damage]. It also has a dive attack with [{minion_range}_range:minion_range] and [3_turns:cooldown] cooldown.\n"
                    "This curse is not considered an [eye] buff, but its activation interval uses the [shot_cooldown:shot_cooldown] stat of [eye] spells.").format(**self.fmt_dict())

    if cls is ShieldSiphon:

        def on_init(self):
            self.name = "Siphon Shields"

            self.max_charges = 3
            self.level = 4

            self.tags = [Tags.Arcane, Tags.Enchantment]
            self.range = 0

            self.shield_steal = 1

            self.upgrades['shield_burn'] = (1, 4, "Shield Burn", "Deal [{damage}_fire:fire] damage per shield stolen as a separate hit.")
            self.upgrades['shield_steal'] = (4, 1, "Shield Steal", "Up to 4 more [SH:shields] are stolen from each enemy.")
            self.upgrades["mirage"] = (1, 3, "Shield Mirage", "If you already have [20_SH:shields], then every additional [3_SH:shields] stolen will summon a shield mirage near you.\nShield mirages are stationary, flying [arcane] minions with fixed 1 HP, [3_SH:shields], and no resistances.")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["damage"] = self.get_stat("damage", base=5)
            return stats

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
            self.upgrades['clouds'] = (1, 4, "Cloud Nova", "The nova leaves storm clouds and blizzards behind, chosen at random per tile.\nIf a tile already contains a blizzard cloud, [lightning] damage is dealt to that tile again.\nIf a tile already contains a thunderstorm cloud, [ice] damage is dealt to that tile again.")
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
                        existing = self.caster.level.tiles[p.x][p.y].cloud
                        if isinstance(existing, BlizzardCloud):
                            self.caster.level.deal_damage(p.x, p.y, damage, Tags.Lightning, self)
                        elif isinstance(existing, StormCloud):
                            self.caster.level.deal_damage(p.x, p.y, damage, Tags.Ice, self)
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
            self.upgrades["surge"] = (1, 3, "Cloud Surge", "If an affected tile already has a blizzard or thunderstorm cloud, the unit on that tile is dealt [lightning] damage equal to the storm drake's breath damage.\nIf you have the Strikechance upgrade, there is a 50% chance to deal damage again.")
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
            self.upgrades["mirror"] = (1, 4, "Ice Mirror", "When an ice elemental is damaged by an enemy, that enemy has a chance to be [frozen] for [1_turn:duration], equal to the ice elemental's percentage of missing HP.")
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
            mirror = self.get_stat("mirror")

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
                if mirror:
                    elemental.buffs = [IceMirrorBuff()]

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
            self.buff_type = BUFF_TYPE_BLESS
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
            self.instinct = self.spell.get_stat("instinct")

        def on_applied(self, owner):
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
            
            if not self.instinct:
                return
            spells = [spell for spell in self.owner.spells if Tags.Sorcery in spell.tags]
            lightning_spells = [spell for spell in spells if Tags.Lightning in spell.tags and spell.can_pay_costs()]
            random.shuffle(lightning_spells)
            for spell in lightning_spells:
                target = spell.get_ai_target()
                if not target:
                    continue
                self.owner.level.act_cast(self.owner, spell, target.x, target.y)
                break
            arcane_spells = [spell for spell in spells if Tags.Arcane in spell.tags and spell.can_pay_costs()] if self.arcane else []
            random.shuffle(arcane_spells)
            for spell in arcane_spells:
                target = spell.get_ai_target()
                if not target:
                    continue
                self.owner.level.act_cast(self.owner, spell, target.x, target.y)
                break

        def shoot(self, target):
            points = self.owner.level.get_points_in_line(Point(self.owner.x, self.owner.y), Point(target.x, target.y), find_clear=not self.arcane)[1:]
            for p in points:
                self.owner.level.deal_damage(p.x, p.y, self.damage, Tags.Lightning, self.spell)
                if self.arcane:
                    if self.owner.level.tiles[p.x][p.y].is_wall():
                        self.owner.level.make_floor(p.x, p.y)
                    self.owner.level.deal_damage(p.x, p.y, self.damage//2, Tags.Arcane, self.spell)
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
            self.upgrades["arcane"] = (1, 5, "Void Watcher", "Watcher Form also grants [100_arcane:arcane] resist.\nWatcher Form now instead targets the furthest unit from the caster regardless of line of sight, melts through walls, and also deals half [arcane] damage.")
            self.upgrades["instinct"] = (1, 6, "Watcher's Instinct", "While in Watcher Form, each turn you will automatically cast a random one of your [lightning] [sorcery] spells at a random valid enemy target, consuming charges as usual.\nIf you have the Void Watcher upgrade, you will also cast an [arcane] [sorcery] spell each turn.")

        def cast_instant(self, x, y):
            self.caster.apply_buff(WatcherFormBuff(self), self.get_stat('duration'))

        def get_description(self):
            return ("Each turn, fire a lightning bolt at the farthest enemy in line of sight dealing [{damage}_lightning:lightning] damage in a beam.\n"
                    "Gain [100_fire:fire], [100_lightning:lightning], [100_physical:physical], and [100_poison:poison] resist.\n"
                    "The uer cannot move or cast spells for the duration. If the caster is not you, this spell only deals 20% damage.\n"
                    "Lasts [{duration}_turns:duration].\n").format(**self.fmt_dict())

    if cls is WheelOfFate:

        def on_init(self):
            self.name = "Wheel of Death"
            self.damage = 200
            self.range = 0
            self.tags = [Tags.Dark, Tags.Sorcery]
            self.element = Tags.Dark
            self.level = 4
            self.max_charges = 5

            self.upgrades['max_charges'] = (3, 4)
            self.upgrades['cascade'] = (1, 7, "Death Roulette", "On kill, gain a Roulette stack for [{duration}_turns:duration].\nWheel of Death hits an additional enemy for each Roulette stack you have at cast time.", "fate")
            self.upgrades["annihilate"] = (1, 7, "Royal Flush", "Wheel of Death now deals an additional hit of [fire], [lightning], [physical], and [arcane] damage, each targeting a random enemy.\nThe same enemy can be hit more than once.", "fate")

        def cast(self, x, y):
            
            num_targets = 1 + len([b for b in self.owner.buffs if isinstance(b, DeathrouletteStack)])
            prev_hit = set()
            damage = self.get_stat('damage')
            cascade = self.get_stat('cascade')
            duration = self.get_stat('duration', 10)
            iter = range(num_targets)
            annihilate = self.get_stat("annihilate")
            if annihilate:
                iter = [Tags.Dark, Tags.Fire, Tags.Lightning, Tags.Physical, Tags.Arcane]

            for i in iter:
                valid_targets = [u for u in self.caster.level.units if self.caster.level.are_hostile(self.caster, u) and (annihilate or u not in prev_hit)]
                if not valid_targets:
                    return
                target = random.choice(valid_targets)
                prev_hit.add(target)
                target.deal_damage(damage, i if isinstance(i, Tag) else Tags.Dark, self)
                if cascade and not target.is_alive():
                    self.owner.apply_buff(DeathrouletteStack(), duration)
                for _ in range(3):
                    yield

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
            self.upgrades["focus"] = (1, 4, "Focused Cascade", "Each cantrip has a chance to be cast an additional time, equal to 1 divided by the number of enemies in the affected area at the time of casting this spell.")
            self.upgrades["specialize"] = (1, 4, "Cantrip Specialization", "Each cantrip has a chance to be cast an additional time, equal to 1 divided by your number of cantrips.")
            self.add_upgrade(CantripCleanup())

        def cast_instant(self, x, y):
            units = [self.caster.level.get_unit_at(p.x, p.y) for p in self.get_impacted_tiles(x, y)]
            enemies = [u for u in units if u and are_hostile(u, self.caster)]
            if not enemies:
                return
            spells = [s for s in self.caster.spells if s.level == 1 and Tags.Sorcery in s.tags]
            if not spells:
                return

            focus_chance = 1/len(enemies) if self.get_stat("focus") else 0
            specialize_chance = 1/len(spells) if self.get_stat("specialize") else 0

            pairs = list(itertools.product(enemies, spells))

            random.shuffle(pairs)

            for enemy, spell in pairs:
                num = 1
                if random.random() < focus_chance:
                    num += 1
                if random.random() < specialize_chance:
                    num += 1
                for _ in range(num):
                    self.caster.level.act_cast(self.caster, spell, enemy.x, enemy.y, pay_costs=False)

    if cls is IceWind:

        def on_init(self):
            self.name = "Chill Wind"

            self.level = 5
            self.tags = [Tags.Ice, Tags.Sorcery]

            self.max_charges = 2

            self.damage = 21
            self.duration = 6

            self.range = RANGE_GLOBAL
            self.requires_los = False

            self.upgrades['max_charges'] = (2, 3)
            self.upgrades['damage'] = (14, 2)
            self.upgrades["vortex"] = (1, 4, "Chill Vortex", "Each tile containing a thunderstorm or blizzard cloud that is affected by the wind current has a 50% chance to create a [{radius}_tile:radius] burst that deals the same damage and applies the same duration of [freeze].")

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["radius"] = self.get_stat("radius", base=2)
            return stats

        def cast(self, x, y):
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            vortex = self.get_stat("vortex")
            radius = self.get_stat("radius", base=2)
            for p in self.get_impacted_tiles(x, y):
                hit(self, p, damage, duration)
                if vortex:
                    cloud = self.caster.level.tiles[p.x][p.y].cloud
                    if isinstance(cloud, StormCloud) or isinstance(cloud, BlizzardCloud):
                        if random.random() < 0.5:
                            for stage in Burst(self.caster.level, p, radius):
                                for q in stage:
                                    hit(self, q, damage, duration)
                                yield
                if random.random() < .4:
                    yield

        def hit(self, p, damage, duration):
            self.caster.level.deal_damage(p.x, p.y, damage, Tags.Ice, self)
            unit = self.caster.level.get_unit_at(p.x, p.y)
            if unit:
                unit.apply_buff(FrozenBuff(), duration)

    if cls is DeathCleaveBuff:

        def on_init(self):
            self.name = "Death Cleave"
            self.description = "Spells will cleave to nearby targets if they kill their main target"
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.global_triggers[EventOnDeath] = lambda evt: on_death(self, evt)
            self.tried_cleaves = set()

        def on_spell_cast(self, evt):
            unit = self.owner.level.get_unit_at(evt.x, evt.y)
            if not unit or unit is self.owner:
                return
            self.tried_cleaves.add((unit, evt.spell))
        
        def on_death(self, evt):
            if not evt.damage_event or not evt.damage_event.source:
                return
            reach = self.spell.get_stat("reach")
            indiscriminate = self.spell.get_stat("indiscriminate")
            for pair in list(self.tried_cleaves):
                if pair[0] is not evt.unit:
                    continue
                if indiscriminate or pair[1] is evt.damage_event.source:
                    if reach:
                        self.owner.apply_buff(HungeringReachBuff(type(pair[1])))
                    self.owner.level.queue_spell(self.effect(pair[1], pair[0]))
                self.tried_cleaves.discard(pair)
        
        def effect(self, spell, unit):
            def can_cleave(t):
                if not are_hostile(t, self.owner):
                    return False
                if not spell.can_cast(t.x, t.y):
                    return False
                if distance(t, unit) > self.spell.get_stat('cascade_range'):
                    return False
                return True
            cleave_targets = [u for u in self.owner.level.units if can_cleave(u)]
            if not cleave_targets:
                return
            target = random.choice(cleave_targets)
            for p in Bolt(self.owner.level, unit, target):
                self.owner.level.show_effect(p.x, p.y, Tags.Dark, minor=True)
                yield
            self.owner.level.act_cast(self.owner, spell, target.x, target.y, pay_costs=False)

        def on_pre_advance(self):
            self.tried_cleaves = set()
            for buff in list(self.owner.buffs):
                if isinstance(buff, HungeringReachBuff):
                    self.owner.remove_buff(buff)

        def on_unapplied(self):
            for buff in list(self.owner.buffs):
                if isinstance(buff, HungeringReachBuff):
                    self.owner.remove_buff(buff)

        def on_advance(self):
            pass

    if cls is DeathCleaveSpell:

        def on_init(self):
            self.name = "Death Cleave"
            self.duration = 2
            self.upgrades['duration'] = (3, 3)
            self.upgrades['max_charges'] = (4, 2)
            self.upgrades['cascade_range'] = (3, 4)
            self.upgrades["reach"] = (1, 4, "Hungering Reach", "Each time your spell kills its primary target while Death Cleave is active, that spell gains a stacking range bonus of [2_tiles:range] until the beginning of your next turn.")
            self.upgrades["indiscriminate"] = (1, 6, "Indiscriminate Slaughter", "Now whenever your spell's target dies for any reason before the start of your next turn, that spell will cleave from that target.\nIf you targeted the dead unit with the same spell multiple times in one turn, the spell will only cleave once.\nIf you targeted the dead unit with multiple different spells in one turn, all of them will cleave.")
            self.max_charges = 4
            self.cascade_range = 5
            self.range = 0
            self.level = 4
            self.tags = [Tags.Enchantment, Tags.Arcane, Tags.Dark]

        def get_description(self):
            return ("Whenever a spell you cast kills its primary target with damage before the start of your next turn, that spell is recast on a randomly selected nearby valid enemy target up to [{cascade_range}_tiles:cascade_range] away.\n"
                    "This process repeats until the target survives the spell, or there are no nearby valid targets.\n"
                    "Lasts [{duration}_turns:duration].").format(**self.fmt_dict())

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
            self.upgrades["independent"] = (1, 3, "Independent Eye", "The floating eye now has an attack with unlimited range that deals [{minion_damage}_arcane:arcane] damage.")
            self.upgrades["eternal"] = (1, 2, "Eternal Gaze", "When the floating eye loses a non-stacking [eye] buff, that buff will be reapplied with unlimited duration.")

            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["minion_damage"] = self.get_stat("minion_damage", base=2)
            return stats

        def cast_instant(self, x, y):
            eye = FloatingEye()
            if not self.get_stat("independent"):
                eye.spells = []
            apply_minion_bonuses(self, eye)
            eye.buffs.append(FloatingEyeBuff(self))

            self.summon(eye, Point(x, y))

    if cls is FloatingEyeBuff:

        def on_init(self):
            if self.spell.get_stat("eternal"):
                self.owner_triggers[EventOnBuffRemove] = lambda evt: on_buff_remove(self, evt)

        def on_buff_remove(self, evt):
            if not isinstance(evt.buff, Spells.ElementalEyeBuff) or evt.buff.stack_type == STACK_INTENSITY:
                return
            self.owner.apply_buff(evt.buff)

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
            self.upgrades["ravens"] = (1, 5, "White Ravens", "Summon white ravens instead of eagles.\nWhite ravens resist [dark] damage, and their melee attacks inflict [{duration}_turns:duration] of [blind].", "species")

            self.range = 0

            self.level = 5
            self.tags = [Tags.Conjuration, Tags.Nature, Tags.Holy]

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration", base=3)
            return stats

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
                    eagle.spells[0] = SimpleMeleeAttack(damage=minion_damage, buff=BlindBuff, buff_duration=self.get_stat("duration", base=3))
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
            self.upgrades["quillmaker"] = (1, 6, "Quillmaker", "On death, the ice phoenix now summons a cerulean quill for [{minion_duration}_turns:minion_duration].\nThe cerulean quill can summon living scrolls of Icicle and Heavenly Blast, which gain all of your upgrades and bonuses.")
            self.add_upgrade(IcePhoenixFreeze())
            self.add_upgrade(IcePhoenixIcyJudgment())

            self.must_target_empty = True

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["explosion_damage"] = self.get_stat("minion_damage", base=25)
            stats["minion_duration"] = self.get_stat("minion_duration", base=18)
            return stats

        def get_quill(self):
            unit = Unit()
            unit.name = "Cerulean Quill"
            unit.asset = ["UnderusedOptions", "Units", "cerulean_quill"]
            unit.turns_to_death = 18

            unit.max_hp = 15
            unit.shields = 6

            spell = WriteCeruleanScrolls()
            spell.num_summons = self.get_stat("num_summons")
            unit.spells.append(spell)

            unit.resists[Tags.Ice] = 75
            unit.resists[Tags.Holy] = 75
            unit.resists[Tags.Arcane] = 100

            unit.stationary = True
            unit.flying = True
            unit.tags = [Tags.Ice, Tags.Holy, Tags.Arcane, Tags.Construct]
            unit.buffs.append(TeleportyBuff(chance=.1, radius=5))
            unit.source = self
            return unit

        def cast_instant(self, x, y):
            phoenix = Unit()
            phoenix.max_hp = self.get_stat('minion_health')
            phoenix.name = "Ice Phoenix"

            phoenix.tags = [Tags.Ice, Tags.Holy]

            buff = IcePhoenixBuff()
            buff.radius = self.get_stat("radius")
            buff.damage = self.get_stat("minion_damage", base=25)
            phoenix.buffs.append(buff)
            phoenix.buffs.append(ReincarnationBuff(self.get_stat('lives')))
            if self.get_stat("quillmaker"):
                phoenix.buffs.append(SpawnOnDeath(lambda: get_quill(self), 1))

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

            self.upgrades['cascade'] =  (1, 3, 'Cascade', 'Hits from Annihilate will jump to targets up to [{cascade_range}_tiles:cascade_range] away if the main target is killed or if targeting an empty tile. This ignores line of sight.')
            self.upgrades['dark'] =  (1, 2, 'Dark Annihilation', 'Mega Annihilate also deals [dark] damage.')
            self.upgrades['arcane'] =  (1, 2, 'Arcane Annihilation', 'Mega Annihilate also deals [arcane] damage.')
            self.upgrades["inescapable"] = (1, 7, "Inescapable Annihilation", "Mega Annihilate will now remove all [SH:shields] and buffs from the target before dealing damage.")
            self.upgrades['damage'] = (99, 4)

    if cls is PyrostaticHexSpell:

        def on_init(self):
            self.name = "Pyrostatic Curse"

            self.tags = [Tags.Fire, Tags.Lightning, Tags.Enchantment]
            self.level = 5
            self.max_charges = 7

            self.radius = 5
            self.range = 9
            self.duration = 6
            self.num_targets = 2
            self.requires_los = False
            self.can_target_self = True

            self.upgrades['radius'] = (3, 2)
            self.upgrades['duration'] = (6, 3)
            self.upgrades["num_targets"] = (2, 4)
            self.upgrades['beam'] = (1, 5, "Linear Conductance", "Redealt [lightning] damage is dealt to enemies along a beam instead of just to one target.")
            self.upgrades["ignition"] = (1, 5, "Hex Ignition", "Targets that are already inflicted with Pyrostatic Hex will also take [fire] damage when you cast this spell.\nThis damage is equal to the target's remaining Pyrostatic Hex duration plus this spell's bonuses to [damage].")

        def cast_instant(self, x, y):
            duration = self.get_stat('duration')
            ignition = self.get_stat("ignition")
            damage = self.get_stat("damage", base=0)
            for p in self.owner.level.get_points_in_ball(x, y, self.get_stat('radius')):
                u = self.owner.level.get_unit_at(p.x, p.y)
                if u and are_hostile(u, self.caster):
                    if ignition:
                        existing = u.get_buff(PyroStaticHexBuff)
                        if existing:
                            u.deal_damage(existing.turns_left + damage, Tags.Fire, self)
                    u.apply_buff(PyroStaticHexBuff(self), duration)

    if cls is PyroStaticHexBuff:

        def __init__(self, spell):
            self.spell = spell
            Buff.__init__(self)

        def on_init(self):
            self.name = "Pyrostatic Hex"
            self.beam = self.spell.get_stat("beam")
            self.buff_type = BUFF_TYPE_CURSE
            self.stack_type = STACK_REPLACE
            self.color = Tags.Fire.color
            self.owner_triggers[EventOnDamaged] = self.on_damage
            self.asset = ['status', 'pyrostatic_hex']

        def deal_damage(self, evt):

            redeal_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if are_hostile(u, self.spell.owner) and u != self.owner]
            random.shuffle(redeal_targets)

            damage = evt.damage//2
            for t in redeal_targets[:self.spell.get_stat("num_targets")]:
                for p in self.owner.level.get_points_in_line(self.owner, t)[1:-1]:
                    if self.beam:
                        unit = self.owner.level.get_unit_at(p.x, p.y)
                        if not unit or not are_hostile(self.spell.caster, unit):
                            self.owner.level.show_effect(p.x, p.y, Tags.Lightning)
                        else:
                            unit.deal_damage(damage, Tags.Lightning, self.spell)
                    else:
                        self.owner.level.show_effect(p.x, p.y, Tags.Lightning, minor=True)
                t.deal_damage(damage, Tags.Lightning, self.spell)
            yield

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

            self.upgrades['damage'] = (32, 2, "Damage", "Deal [poison] damage to the target tile if it contains an enemy.")
            self.upgrades['minion_health'] = (10, 3)
            self.upgrades["tunneling"] = (1, 4, "Tunneling", "Walls and chasms in the affected area will now be turned into floors before summoning.")
            self.upgrades['aether_spiders'] = (1, 6, "Aether Spiders", "Summon aether spiders instead of regular spiders.", "species")
            self.upgrades['steel_spiders'] = (1, 6, "Steel Spiders", "Summon steel spiders instead of regular spiders.", "species")

            self.tags = [Tags.Nature, Tags.Conjuration]

        def get_impacted_tiles(self, x, y):
            points = self.caster.level.get_points_in_rect(x - 2, y - 2, x + 2, y + 2)
            tunneling = self.get_stat("tunneling")
            return [p for p in points if tunneling or not self.caster.level.tiles[p.x][p.y].is_wall()]

        def get_description(self):
            return ("Summons a ring of giant spiders at the target, surrounded by a ring of webs.\n"
                    "Enemies blocking the spider ring are [poisoned] for [{duration}_turns:duration], and enemies blocking the web ring are [stunned] for [1_turn:duration].\n"
                    "Giant spiders have [{minion_health}_HP:minion_health] and spin webs.\n"
                    "Giant spiders have a melee attack which deals [{minion_damage}_physical:physical] and inflicts [10_turns:duration] of [poison].\n"
                    "Webs [stun] non spider units which step on them for [1_turn:duration].\n"
                    + text.poison_desc + " " + text.stun_desc).format(**self.fmt_dict())

        def cast(self, x, y):
            
            aether = self.get_stat('aether_spiders')
            steel = self.get_stat("steel_spiders")
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            tunneling = self.get_stat("tunneling")

            for p in self.get_impacted_tiles(x, y):
                
                if tunneling:
                    self.owner.level.make_floor(p.x, p.y)
                unit = self.caster.level.get_unit_at(p.x, p.y)

                rank = max(abs(p.x - x), abs(p.y - y))

                if rank == 0 and unit and are_hostile(unit, self.caster):
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
                        apply_minion_bonuses(self, spider)
                        self.summon(spider, p)
                    if unit and are_hostile(unit, self.caster):
                        unit.apply_buff(Poison(), duration)
                else:
                    if not unit and not self.caster.level.tiles[p.x][p.y].is_wall():
                        cloud = SpiderWeb()
                        cloud.owner = self.caster
                        self.caster.level.add_obj(cloud, *p)
                    if unit and are_hostile(unit, self.caster):
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

            self.minion_health = 8
            self.max_charges = 3
            self.level = 6
            self.range = 9

            self.tags = [Tags.Fire, Tags.Orb, Tags.Conjuration]

            self.upgrades['range'] = (5, 2)
            self.upgrades['melt_walls'] = (1, 4, "Matter Melting", "Searing Orb can melt and be cast through walls")
            self.upgrades["safety"] = (1, 2, "Safety", "Searing Orb no longer damages your minions.")
            self.upgrades["poison"] = (3, 6, "Radioactive Orb", "Searing Orb also deals [poison] damage.")

        def get_description(self):
            return ("Summon a searing orb next to the caster.\n"
                    "The orb deals [3_fire:fire] damage each turn to all units in line of sight. This damage is fixed, and cannot be increased using shrines, skills, or buffs.\n"
                    "The caster is immune to this damage.\n"
                    "The orb has no will of its own, each turn it will float one tile towards the target.\n"
                    "The orb can be destroyed by ice damage.").format(**self.fmt_dict())

        def on_orb_move(self, orb, next_point):
            dtypes = [Tags.Fire]
            if self.get_stat("poison"):
                dtypes.append(Tags.Poison)
            safety = self.get_stat("safety")
            for u in orb.level.get_units_in_los(next_point):
                if u is self.caster or u is orb:
                    continue
                if safety and not are_hostile(u, self.caster):
                    continue
                for dtype in dtypes:
                    u.deal_damage(3, dtype, self)

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

            self.upgrades['void_court'] = (1, 5, "Void Court", "Instead summon a void champion and [{num_summons}:num_summons] void knights.", "court")
            self.upgrades['storm_court'] = (1, 5, "Storm Court", "Instead summon a storm champion and [{num_summons}:num_summons] storm knights.", "court")
            self.upgrades['chaos_court'] = (1, 5, "Chaos Court", "Instead summon a chaos champion and [{num_summons}:num_summons] chaos knights.", "court")
            self.upgrades["promotion"] = (1, 6, "Promotion", "Each non-champion knight will be promoted to a champion after [20_turns:duration].")
            self.upgrades['max_charges'] = (1, 3)
            self.add_upgrade(KnightlyOathUndyingOath())

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["num_summons"] = self.get_stat("num_summons", base=3)
            return stats

        def get_description(self):
            return ("Summon a void knight, a chaos knight, and a storm knight.\n"
                    "Each knight has [{minion_health}_HP:minion_health], various resistances, and an arsenal of unique magical abilities.\n"
                    "Whenever a knight is about to die to damage, the caster takes [40_holy:holy] damage to fully heal the knight, restore all [SH:shields], and remove all debuffs.").format(**self.fmt_dict())

        def cast(self, x, y):

            knights = [VoidKnight(), ChaosKnight(), StormKnight()]
            num_summons = self.get_stat("num_summons", base=3)
            if self.get_stat('void_court'):
                knights = [Champion(VoidKnight())]
                for _ in range(num_summons):
                    knights.append(VoidKnight())
            if self.get_stat('storm_court'):
                knights = [Champion(StormKnight())]
                for _ in range(num_summons):
                    knights.append(StormKnight())
            if self.get_stat('chaos_court'):
                knights = [Champion(ChaosKnight())]
                for _ in range(num_summons):
                    knights.append(ChaosKnight())

            promotion = self.get_stat("promotion")
            def promote(knight):
                unit = Champion(knight)
                unit.buffs.append(KnightlyOathBuff(self))
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
                u.buffs.append(KnightlyOathBuff(self))
                self.summon(u)
                yield

    if cls is MeteorShower:

        def on_init(self):
            self.name = "Meteor Shower"

            self.damage = 23
            self.num_targets = 7
            self.storm_radius = 7
            self.stats.append('storm_radius')
            self.radius = 2
            self.range = RANGE_GLOBAL
            self.requires_los = False
            self.duration = 5
            self.can_target_self = True

            self.max_charges = 2

            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 7

            self.max_channel = 10

            self.upgrades['num_targets'] = (3, 4)
            self.upgrades["radius"] = (1, 4)
            self.upgrades['large'] = (1, 4, "Large Meteors", "The [physical] damage and [stun] radius of each meteor now gains a radius equal to half of this spell's [radius] stat, with a 50% chance to round up or down per meteor.")
            self.upgrades['max_channel'] = (5, 2)

        def cast(self, x, y, channel_cast=False):

            if not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat('max_channel'))
                return

            points_in_ball = list(self.caster.level.get_points_in_ball(x, y, self.get_stat('storm_radius')))

            large = self.get_stat('large')
            damage = self.get_stat('damage')
            duration = self.get_stat('duration')
            radius = self.get_stat('radius')

            for _ in range(self.get_stat('num_targets')):
                target = random.choice(points_in_ball)

                rock_size = random.choice([math.ceil, math.floor])(radius/2) if large else 0
                for stage in Burst(self.caster.level, target, rock_size, ignore_walls=True):
                    for point in stage:
                        self.caster.level.make_floor(point.x, point.y)
                        self.caster.level.deal_damage(point.x, point.y, damage, Tags.Physical, self)
                        unit = self.caster.level.get_unit_at(point.x, point.y)
                        if unit:
                            unit.apply_buff(Stun(), duration)
                    yield

                self.caster.level.show_effect(0, 0, Tags.Sound_Effect, 'hit_enemy')
                yield

                for stage in Burst(self.caster.level, target, radius):
                    for point in stage:
                        self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)
                    yield
                yield

    if cls is MulticastBuff:

        def on_init(self):
            self.name = "Multicast"
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

        def on_pre_advance(self):
            self.can_copy = True

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

        def get_description(self):
            return ("The first [sorcery] spell you cast each turn is copied [{copies}:sorcery] times. This is reset before the beginning of your turn.\n"
                    "Lasts [{duration}_turns:duration]").format(**self.fmt_dict())

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
            self.upgrades["damage"] = (30, 5)

        def cast(self, x, y):
            units = [u for u in self.caster.level.units if are_hostile(u, self.caster)]
            random.shuffle(units)
            duration = self.get_stat("duration")
            damage = self.get_stat('damage')
            for u in units:
                if u.cur_hp < damage:
                    u.apply_buff(FrozenBuff(), duration)
                if Tags.Fire in u.tags:
                    u.deal_damage(damage, Tags.Ice, self)
                if random.random() < .3:
                    yield

        def get_description(self):
            return ("All non [ice] immune enemies under [{damage}:damage] current HP are [frozen] for [{duration}_turns:duration]. The HP threshold benefits from your bonuses to [damage].\n"
                    "Deals [{damage}_ice:ice] damage to all [fire] units.").format(**self.fmt_dict())

    if cls is ArcaneCredit:

        def on_init(self):
            self.name = "Arcane Credit"
            self.owner_triggers[EventOnSpellCast] = self.on_cast
            self.color = Tags.Arcane.color
            self.description = "Every non [arcane] spell has a 50% chance to refund 1 charge on cast."

        def on_cast(self, evt):
            if Tags.Arcane not in evt.spell.tags and random.random() < 0.5:
                evt.spell.cur_charges = min(evt.spell.cur_charges + 1, evt.spell.get_stat('max_charges'))

    if cls is ArcaneAccountant:

        def on_init(self):
            self.tags = [Tags.Arcane]
            self.level = 5
            self.name = "Arcane Accounting"
            self.duration = 2
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def get_description(self):
            return "Whenever you cast an [arcane] spell, you have a chance to gain Arcane Credit for [%i_turns:duration], equal to the spell's percentage of missing charges.\nWhile you have Arcane Credit, all non-arcane spells have a 50%% chance to refund a charge on cast.\nCannot be triggered by spells that have no max charges." % self.get_stat("duration")

        def on_spell_cast(self, evt):
            if Tags.Arcane in evt.spell.tags:
                max_charges = evt.spell.get_stat("max_charges")
                if not max_charges:
                    return
                if random.random() < (max_charges - evt.spell.cur_charges)/max_charges:
                    self.owner.apply_buff(ArcaneCredit(), self.get_stat("duration") + 1)

    if cls is Faestone:

        def on_init(self):
            self.name = "Faestone"
            self.level = 4
            self.tags = [Tags.Arcane, Tags.Nature, Tags.Conjuration]
            self.minion_damage = 20
            self.minion_health = 120
            self.owner_triggers[EventOnUnitAdded] = self.on_unit_added
            self.owner_triggers[EventOnSpellCast] = lambda evt: on_spell_cast(self, evt)

        def get_description(self):
            return ("Whenever you enter a new level, summon a Fae Stone nearby.\n"
                    "The Fae Stone has [{minion_health}_HP:minion_health], and is flying and stationary. It has a melee attack that deals [{minion_damage}_physical:physical] damage.\n"
                    "Whenever you cast a [nature] or [arcane] spell, the Fae Stone heals for [10_HP:heal], gains [1_SH:shields], teleports near the target, and immediately acts once.\n"
                    "The Fae Stone will always teleport next to the target if possible, and can swap places with your other minions if the triggering spell is not a [conjuration] spell.\n"
                    "If the Fae Stone is dead, using a mana potion will resurrect it.").format(**self.fmt_dict())

        def on_unit_added(self, evt):
            summon_faestone(self)

        def on_spell_cast(self, evt):
            if not isinstance(evt.spell, SpellCouponSpell):
                return
            for unit in self.owner.level.units:
                if unit.source is self:
                    return
            summon_faestone(self)

        def summon_faestone(self):

            faestone = Unit()
            faestone.unique = True
            faestone.name = "Fae Stone"

            faestone.max_hp = self.minion_health
            faestone.shields = 1

            faestone.spells.append(SimpleMeleeAttack(self.minion_damage))
            buff = FaestoneBuff()
            buff.master = self.owner
            faestone.buffs.append(buff)

            faestone.stationary = True
            faestone.flying = True

            faestone.resists[Tags.Physical] = 50
            faestone.resists[Tags.Fire] = 50
            faestone.resists[Tags.Lightning] = 50
            faestone.resists[Tags.Arcane] = 100
            faestone.resists[Tags.Poison] = 100
            faestone.tags = [Tags.Nature, Tags.Arcane]

            apply_minion_bonuses(self, faestone)

            self.summon(faestone, sort_dist=False)

    if cls is FaestoneBuff:

        def get_tooltip(self):
            return "Whenever its master casts a nature or arcane spell, teleport near the target, heal 10 HP, gain 1 SH, and immediately act once."

        def on_cast(self, evt):
            if evt.caster is not self.master:
                return
            if Tags.Arcane in evt.spell.tags or Tags.Nature in evt.spell.tags:
                self.owner.level.queue_spell(self.teleport(evt, Tags.Conjuration not in evt.spell.tags))

        def teleport(self, target, should_swap):
            dest = None
            if distance(self.owner, target) < 2:
                dest = self.owner
            else:
                points = [p for p in self.owner.level.get_points_in_ball(target.x, target.y, 4) if not self.owner.level.tiles[p.x][p.y].is_wall()]
                def can_swap(point):
                    unit = self.owner.level.get_unit_at(point.x, point.y)
                    if not unit or unit is self.owner:
                        return True
                    return should_swap and not are_hostile(unit, self.owner) and not unit.is_player_controlled and self.owner.level.can_stand(self.owner.x, self.owner.y, unit, check_unit=False)
                points = [p for p in points if can_swap(p)]
                if points:
                    random.shuffle(points)
                    dest = min(points, key=lambda p: distance(p, target))
            if dest:
                if dest.x == self.owner.x and dest.y == self.owner.y:
                    self.owner.level.event_manager.raise_event(EventOnMoved(self.owner, dest.x, dest.y, teleport=True), self.owner)
                    self.owner.level.show_effect(dest.x, dest.y, Tags.Translocation)
                else:
                    self.owner.level.show_effect(self.owner.x, self.owner.y, Tags.Translocation)
                    self.owner.level.act_move(self.owner, dest.x, dest.y, teleport=True, force_swap=True)
                    self.owner.level.show_effect(self.owner.x, self.owner.y, Tags.Translocation)
            self.owner.add_shields(1)
            self.owner.deal_damage(-self.healing, Tags.Heal, self)
            self.owner.level.queue_spell(free_action(self))
            yield

        def free_action(self):
            if not self.owner.is_alive():
                return
            self.owner.advance()
            yield

    if cls is GhostfireUpgrade:

        def do_summon(self, x, y):
            unit = GhostFire()
            unit.resists[Tags.Dark] = 100
            apply_minion_bonuses(self, unit)
            self.summon(unit, target=Point(x, y))
            yield

        def get_description(self):
            return ("Whenever an enemy takes [dark] damage and [fire] damage in the same turn, summon a fire ghost near that enemy.\n"
                    "Fire ghosts fly, have [100_fire:fire] resist and [100_dark:dark] resist, and passively blink.\n"
                    "Fire ghosts have a ranged attack which deals [{minion_damage}_fire:fire] damage with a [{minion_range}_tile:minion_range] range.\n"
                    "The ghosts vanish after [{minion_duration}_turns:minion_duration].").format(**self.fmt_dict())

    if cls is Hibernation:

        def on_unit_add(self, evt):
            if are_hostile(self.owner, evt.unit):
                return
            if self.owner is evt.unit:
                return
            if not(Tags.Living in evt.unit.tags or Tags.Nature in evt.unit.tags or Tags.Ice in evt.unit.tags):
                return
            evt.unit.apply_buff(HibernationBuff(self))

        def on_advance(self):
            for unit in [unit for unit in self.owner.level.units if unit is not self.owner and not are_hostile(self.owner, unit)]:
                if Tags.Living in unit.tags or Tags.Nature in unit.tags or Tags.Ice in unit.tags:
                    unit.apply_buff(HibernationBuff(self))

        def get_description(self):
            return ("Your [living], [nature], and [ice] minions gain [75_ice:ice] resistance.\n"
                    "Whenever [ice] damage is attempted to be dealt to one of those minions, that minion is [frozen] for [{duration}_turns:duration] and gains hibernation for the same duration, during which it heals for [15_HP:heal] per turn.\n"
                    "Hibernation is removed if [fire] or [physical] damage is attempted to be dealt to the minion.\n"
                    "If the minion is immune to [ice] and is not [frozen], then gaining or losing hibernation will trigger the same effects as gaining or losing [freeze].").format(**self.fmt_dict())

    if cls is HibernationBuff:

        def on_init(self):
            self.buff_type = BUFF_TYPE_PASSIVE
            self.resists[Tags.Ice] = 75
            self.owner_triggers[EventOnPreDamaged] = self.on_damaged

        def on_pre_advance(self):
            if not [tag for tag in self.owner.tags if tag in [Tags.Living, Tags.Nature, Tags.Ice]]:
                self.owner.remove_buff(self)

        def on_damaged(self, evt):
            if evt.damage_type != Tags.Ice:
                return
            duration = self.upgrade.get_stat("duration")
            self.owner.apply_buff(FrozenBuff(), duration)
            self.owner.apply_buff(HibernationRegen(self.upgrade), duration)

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
            return "Whenever you cast a [fire] spell, if there is an enemy on the target tile, it loses [100_fire:fire] resistance, which is removed at the beginning of your next turn.\nThen deal [%d_fire:fire] damage to that enemy." % self.get_stat('damage')

        def on_pre_advance(self):
            for unit in list(self.owner.level.units):
                for buff in list(unit.buffs):
                    if isinstance(buff, WhiteFlameDebuff):
                        unit.remove_buff(buff)

        def on_spell_cast(self, evt):
            if Tags.Fire not in evt.spell.tags:
                return
            unit = self.owner.level.get_unit_at(evt.x, evt.y)
            if not unit or not are_hostile(unit, self.owner):
                return
            unit.apply_buff(WhiteFlameDebuff())
            self.owner.level.queue_spell(deal_damage(self, unit))

        def deal_damage(self, unit):
            unit.deal_damage(self.get_stat('damage'), Tags.Fire, self)
            yield

    if cls is AcidFumes:

        def on_init(self):
            self.name = "Acid Fumes"
            self.tags = [Tags.Nature, Tags.Dark]
            self.description = "Each turn, the closest unacidified enemy is [acidified:poison].\n[Acidified:poison] units lose [100_poison:poison] resistance."
            self.level = 5

        def on_advance(self):
            candidates = [u for u in self.owner.level.units if are_hostile(u, self.owner) and not u.has_buff(Acidified)]
            if candidates:
                target = min(candidates, key=lambda unit: distance(unit, self.owner))
                target.apply_buff(Acidified())

    if cls is FrozenFragility:

        def get_description(self):
            return ("Whenever an enemy is [frozen:freeze], inflict fragility for the same duration, which reduces [ice] and [physical] resistances by 100.\n"
                    "Whenever the remaining duration of [freeze] on an enemy is refreshed or extended, the remaining duration of fragility will be lengthened to match if it is shorter.\nIf fragility is removed prematurely and the enemy is still [frozen], it will automatically reapply itself.").format(**self.fmt_dict())

        def on_frozen(self, evt):
            if not isinstance(evt.buff, FrozenBuff):
                return
            if not are_hostile(self.owner, evt.unit):
                return
            evt.unit.apply_buff(curr_module.FragilityBuff(), evt.buff.turns_left)

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

    if cls is Houndlord:

        def on_init(self):
            self.name = "Houndlord"
            self.level = 5
            self.tags = [Tags.Fire, Tags.Conjuration]
            self.minion_damage = 6
            self.minion_health = 19
            self.minion_range = 4

            self.owner_triggers[EventOnUnitAdded] = self.on_unit_added
            self.owner_triggers[EventOnSpellCast] = lambda evt: on_spell_cast(self, evt)

        def get_description(self):
            return ("Begin each level surrounded by friendly hell hounds.\n"
                    "Hell hounds have [{minion_health}_HP:minion_health], [100_fire:fire] resist, [50_dark:dark] resist, and [-50_ice:ice] resist.\n"
                    "Hell hounds have fiery bodies which deal [4_fire:fire] damage to melee attackers.\n"
                    "Hell hounds a melee attack which deals [{minion_damage}_fire:fire] damage.\n"
                    "Hell hounds have a leap attack which deals [{minion_damage}_fire:fire] damage with a range of [{minion_range}_tiles:minion_range].\n"
                    "You attempt to replenish missing hell hounds whenever you use a mana potion.").format(**self.fmt_dict())

        def on_spell_cast(self, evt):
            if not isinstance(evt.spell, SpellCouponSpell):
                return
            missing_hounds = 8
            for unit in self.owner.level.units:
                if unit.source is not self:
                    continue
                missing_hounds -= 1
            if missing_hounds:
                summon_hounds(self, missing_hounds)

        def on_unit_added(self, evt):
            summon_hounds(self, 8)

        def summon_hounds(self, num):
            for p in self.owner.level.get_adjacent_points(self.owner, check_unit=False):
                if num <= 0:
                    return
                existing = self.owner.level.tiles[p.x][p.y].unit
                if existing:
                    if not is_conj_skill_summon(existing):
                        continue
                    p = self.owner.level.get_summon_point(self.owner.x, self.owner.y)
                unit = HellHound()
                apply_minion_bonuses(self, unit)
                self.summon(unit, p)
                num -= 1

    if cls is Hypocrisy:

        def on_spell_cast(self, evt):
            if evt.spell.level < 1:
                return
            for tag in [Tags.Dark, Tags.Holy]:
                if tag not in evt.spell.tags:
                    continue
                btag = Tags.Holy if tag == Tags.Dark else Tags.Dark
                self.owner.apply_buff(HypocrisyStack(btag, evt.spell.level), 2)

        def get_description(self):
            return ("Whenever you cast a [holy] spell, you gain Dark Hypocrisy of that spell's level for [1_turn:duration], which gives all your [dark] spells and skills a [damage] bonus equal to twice its level while you have it. Whenever you cast a [dark] spell whose level is less than that, Dark Hypocrisy is immediately consumed to refund 1 charge of this spell.\n"
                    "Whenever you cast a [dark] spell, you gain Holy Hypocrisy of that spell's level for [1_turn:duration], which has similar effects.\n"
                    "The duration of Hypocrisy is fixed and unaffected by bonuses.").format(**self.fmt_dict())

    if cls is HypocrisyStack:

        def on_init(self):
            self.name = "%s Hypocrisy %d" % (self.tag.name, self.level)
            self.color = self.tag.color
            self.tag_bonuses[self.tag]["damage"] = self.level*2
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def on_spell_cast(self, evt):
            if self.tag in evt.spell.tags and evt.spell.level <= self.level:
                evt.spell.cur_charges += 1
                evt.spell.cur_charges = min(evt.spell.cur_charges, evt.spell.get_stat('max_charges'))
                self.owner.remove_buff(self)

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
            self.owner_triggers[EventOnSpellCast] = lambda evt: on_spell_cast(self, evt)

        def get_description(self):
            return ("Begin each level accompanied by [{num_summons}:num_summons] bone knights and a bone archer, all of which have 1 reincarnation.\n"
                    "Bone knights have [{minion_health}_HP:minion_health], [1_SH:shields], [100_dark:dark] resist, and [50_ice:ice] resist.\n"
                    "Bone knights have a melee attack which deals [{minion_damage}_dark:dark] damage and drains 2 max HP, instantly killing those with less; this counts as killing with [dark] damage.\n"
                    "The bone archer has a ranged attack with the same damage and [{minion_range}_range:minion_range], which drains 1 max HP similarly.\n"
                    "Missing knights and archers are automatically replenished when you use a mana potion.").format(**self.fmt_dict())

        def on_unit_added(self, evt):
            summon_knights(self, self.get_stat("num_summons"))
            summon_archer(self)

        def on_spell_cast(self, evt):
            if not isinstance(evt.spell, SpellCouponSpell):
                return
            missing_knights = self.get_stat("num_summons")
            missing_archer = True
            for unit in self.owner.level.units:
                if unit.source is not self:
                    continue
                if unit.name == "Bone Knight":
                    missing_knights -= 1
                elif unit.name == "Bone Archer":
                    missing_archer = False
            if missing_knights:
                summon_knights(self, missing_knights)
            if missing_archer:
                summon_archer(self)

        def summon_knights(self, num):
            for _ in range(num):
                unit = BoneKnight()
                melee = unit.spells[0]
                melee.onhit = lambda caster, target: drain_max_hp_kill(target, 2, melee)
                melee.description = "Drains 2 max HP."
                melee.can_redeal = lambda unit, already_checked: True
                apply_minion_bonuses(self, unit)
                unit.buffs.append(ReincarnationBuff(1))
                self.summon(unit, target=self.owner, radius=5)

        def summon_archer(self):
            unit = BoneKnightArcher()
            bow = unit.spells[0]
            bow.onhit = lambda caster, target: drain_max_hp_kill(target, 1, bow)
            bow.description = "Drains 1 max HP."
            bow.can_redeal = lambda unit, already_checked: True
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
            return ("Whenever an enemy is [frozen:freeze], inflict frostbite for the same duration, which deals [{damage}_dark:dark] damage per turn.\n"
                    "Whenever the remaining duration of [freeze] on an enemy is refreshed or extended, the remaining duration of frostbite will be lengthened to match if it is shorter.\nIf frostbite is removed prematurely and the enemy is still [frozen], it will automatically reapply itself.").format(**self.fmt_dict())

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

    if cls is LightningWarp:

        def on_init(self):
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.damage = 12
            self.name = "Lightning Warp"
            self.level = 6
            self.radius = 3
            self.tags = [Tags.Lightning, Tags.Translocation]

        def get_description(self):
            return ("Whenever you cast a [lightning] spell, all enemy units within [{radius}_tiles:radius] of the target are inflicted with Warp Lightning.\n"
                    "Then teleport all enemies with Warp Lightning to random spaces up to [12_tiles:range] away and deal [{damage}_lightning:lightning] damage to them.\n"
                    "Warp Lightning is removed from all units before the beginning of your turn.").format(**self.fmt_dict())

        def on_pre_advance(self):
            for unit in list(self.owner.level.units):
                for buff in list(unit.buffs):
                    if isinstance(buff, WarpLightningBuff):
                        unit.remove_buff(buff)

        def do_teleports(self, evt):
            for unit in self.owner.level.get_units_in_ball(evt, self.get_stat("radius")):
                if not are_hostile(unit, self.owner):
                    continue
                unit.apply_buff(WarpLightningBuff())
            yield
            self.owner.level.queue_spell(zap(self, evt))

        def zap(self, evt):
            damage = self.get_stat('damage')
            for unit in list(self.owner.level.units):
                if not are_hostile(unit, self.owner) or not unit.has_buff(WarpLightningBuff):
                    continue
                randomly_teleport(unit, 12)
                unit.deal_damage(damage, Tags.Lightning, self)
            yield

    if cls is OrbLord:

        def on_init(self):
            self.name = "Orb Lord"
            self.tags = [Tags.Orb]
            self.tag_bonuses[Tags.Orb]['max_charges'] = 3
            self.tag_bonuses[Tags.Orb]['range'] = 4
            self.tag_bonuses[Tags.Orb]['minion_health'] = 35
            self.tag_bonuses[Tags.Orb]["minion_damage"] = 4
            self.tag_bonuses[Tags.Orb]["radius"] = 1
            self.level = 7

    if cls is DragonScalesSkill:

        def get_description(self):
            return "Whenever an allied [dragon] uses a breath weapon, all your minions gain 100 resistance to that breath weapon's element for [{duration}_turns:duration].\nIf a minion's resistance to that element is still less than 100, it gains enough additional resistance to that element to make it 100.\nYou will also gain the same effect, but it expires at the end of the dragon's turn.".format(**self.fmt_dict())

        def on_spell_cast(self, evt):
            
            if not isinstance(evt.spell, BreathWeapon) or Tags.Dragon not in evt.caster.tags:
                return
            if are_hostile(evt.caster, self.owner):
                return
            if evt.caster is self.owner:
                return
            
            duration = self.get_stat('duration')
            for u in list(self.owner.level.units):
                if are_hostile(u, self.owner):
                    continue
                buff = DragonScalesBuff(evt.spell.damage_type)
                buff.show_effect = not u.is_player_controlled
                u.apply_buff(buff, duration if not u.is_player_controlled else 0)
                if u.is_player_controlled and buff.applied:
                    evt.caster.apply_buff(TempScalespinnerRemoval(buff))

    if cls is DragonScalesBuff:

        def __init__(self, damage_type):
            Buff.__init__(self)
            self.element = damage_type
            self.name = "%s Scales" % damage_type.name
            self.color = damage_type.color
        
        def on_applied(self, owner):
            self.resists[self.element] = 100 + (-self.owner.resists[self.element] if self.owner.resists[self.element] < 0 else 0)

    if cls is SilverSpearSpell:

        def on_init(self):
            self.name = "Silver Spear"
            self.level = 3
            self.max_charges = 25
            self.tags = [Tags.Holy, Tags.Metallic, Tags.Sorcery]

            self.damage = 27

            self.range = 11
            self.radius = 1

            self.upgrades['radius'] = (1, 3)
            self.upgrades['damage'] = (15, 3)
            self.upgrades['max_charges'] = (12, 3)
            self.upgrades["blessed"] = (1, 4, "Blessed Silver", "The [holy] area damage of Silver Spear now also applies to [undead] and [demon] enemies.")

        def get_description(self):
            return ("Deals [{damage}_physical:physical] damage to the target.\n"
                    "Deals [{damage}_holy:holy] damage to [dark] and [arcane] enemies within a [{radius}_tile:radius] away from the projectile's path.".format(**self.fmt_dict()))

        def cast(self, x, y):

            damage = self.get_stat("damage")
            radius = self.get_stat('radius')
            hits = set()
            tags = [Tags.Dark, Tags.Arcane]
            if self.get_stat("blessed"):
                tags.extend([Tags.Undead, Tags.Demon])
            
            # todo- holy sparkles randomly around projectile?
            for p in self.caster.level.get_points_in_line(self.caster, Point(x, y))[1:]:
                self.caster.level.projectile_effect(p.x, p.y, proj_name='silver_spear', proj_origin=self.caster, proj_dest=Point(x, y))
                units = self.owner.level.get_units_in_ball(p, radius)
                for unit in units:
                    if unit in hits or not are_hostile(unit, self.caster):
                        continue
                    hits.add(unit)
                    if [tag for tag in unit.tags if tag in tags]:
                        unit.deal_damage(damage, Tags.Holy, self)
                yield

            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.deal_damage(damage, Tags.Physical, self)

    if cls is ChaosBarrage:

        def on_init(self):
            self.name = "Chaos Barrage"
            self.range = 7
            self.damage = 9
            self.num_targets = 8
            self.angle = math.pi / 6
            self.max_charges = 8
            self.tags = [Tags.Chaos, Tags.Sorcery]

            self.level = 2

            self.upgrades['max_charges'] = (4, 1)
            self.upgrades['damage'] = (4, 5)
            self.upgrades['num_targets'] = (5, 4, "Extra Bolts")
            self.upgrades["siege"] = (1, 5, "Chaos Siege", "Chaos Barrage becomes a channeled spell.\nEach turn you channel this spell, you randomly take [4_fire:fire], [4_lightning:lightning], or [4_physical:physical] damage per siege stack you have, and gain a siege stack, which causes Chaos Barrage to fire 2 more shards.\nSiege stacks are lost when you stop channeling, or if you cast this spell manually again.\nIf you never channel beyond the initial cast, you will never take damage from this upgrade.")

        def cast(self, x, y, channel_cast=False):

            siege = self.get_stat('siege')
            if siege and not channel_cast:
                self.caster.remove_buffs(ChaosSiegeBuff)
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)))
                return

            possible_targets = [self.caster.level.get_unit_at(p.x, p.y) for p in self.get_cone_burst(x, y)]
            possible_targets = [t for t in possible_targets if t and t != self.caster]
            damage = self.get_stat('damage')

            for _ in range(self.get_stat('num_targets')):
                
                possible_targets = [t for t in possible_targets if t.is_alive()]
                if not possible_targets:
                    break

                cur_enemy = random.choice(possible_targets)
                cur_element = random.choice([Tags.Fire, Tags.Lightning, Tags.Physical])

                start = Point(self.caster.x, self.caster.y)
                target = Point(cur_enemy.x, cur_enemy.y)
                path = Bolt(self.caster.level, start, target)
                for p in path:
                    self.caster.level.show_effect(p.x, p.y, cur_element, minor=True)
                    yield

                self.caster.level.deal_damage(target.x, target.y, damage, cur_element, self)
            
            if siege:
                for _ in range(self.caster.get_buff_stacks(ChaosSiegeBuff)):
                    self.caster.deal_damage(4, random.choice([Tags.Fire, Tags.Lightning, Tags.Physical]), self)
                self.caster.apply_buff(ChaosSiegeBuff())

    if cls is SummonVoidDrakeSpell:

        def on_init(self):
            self.name = "Void Drake"
            self.range = 4
            self.max_charges = 2
            self.tags = [Tags.Arcane, Tags.Conjuration, Tags.Dragon]
            self.level = 4

            self.minion_health = 45
            self.minion_damage = 8
            self.breath_damage = VoidDrake().spells[0].damage
            self.minion_range = 7
            self.upgrades['minion_health'] = (25, 2)
            self.upgrades['shield_regen'] = (1, 3, "Shield Regen", "The Void Drake gains [1_SH:shields] every [3_turns:duration], to a max of [2_SH:shields].")
            self.upgrades['dragon_mage'] = (1, 5, "Dragon Mage", "Summoned Void Drakes can cast Magic Missile with a 3 turn cooldown.\nThis Magic Missile gains all of your upgrades and bonuses.")
            self.upgrades['essence'] = (1, 4, "Essence Breath", "The Void Drake's breath no longer damages allies, and instead increases temporary allies' remaining durations by [1_turn:minion_duration].")

            self.must_target_empty = True

        def cast_instant(self, x, y):
            drake = VoidDrake()
            drake.max_hp = self.get_stat('minion_health')
            drake.spells[0] = SummonedVoidDrakeBreath()
            drake.spells[0].damage = self.get_stat('breath_damage')
            drake.spells[0].range = self.get_stat('minion_range')
            if self.get_stat("essence"):
                drake.spells[0].essence = True
            drake.spells[1].damage = self.get_stat('minion_damage')
            if self.get_stat("shield_regen"):
                drake.buffs = [ShieldRegenBuff(2, 3)]

            if self.get_stat('dragon_mage'):
                mmiss = MagicMissile()
                mmiss.statholder = self.caster
                mmiss.max_charges = 0
                mmiss.cur_charges = 0
                mmiss.cool_down = 3
                drake.spells.insert(1, mmiss)

            self.summon(drake, Point(x, y))

    if cls is MetalLord:

        def on_init(self):
            self.name = "Metal Lord"
            self.tags = [Tags.Metallic]
            self.tag_bonuses[Tags.Metallic]['max_charges'] = 3
            self.tag_bonuses[Tags.Metallic]['duration'] = 5
            self.tag_bonuses[Tags.Metallic]['range'] = 4
            self.tag_bonuses[Tags.Metallic]["minion_health"] = 20

            self.level = 7
            self.resists[Tags.Physical] = 25

    if cls is SummonSpiderQueen:

        def on_init(self):
            self.name = "Spider Queen"
            self.tags = [Tags.Nature, Tags.Conjuration]

            self.max_charges = 2
            self.level = 5

            self.upgrades["aether"] = (1, 3, "Aether Queen", "Summon an aether spider queen instead.", "species")
            self.upgrades["steel"] = (1, 3, "Steel Queen", "Summon a steel spider queen instead.", "species")
            self.upgrades["minion_health"] = (10, 3)
            self.upgrades["hatchery"] = (1, 4, "Corpse Hatchery", "The spider queen now spawns an arachnid abomination on death, which will spawn a number of fully grown spiders on death equal to twice the queen's normal spawning amount.")

            self.must_target_walkable = True
            self.must_target_empty = True

            self.minion_damage = GiantSpider().spells[0].damage
            self.minion_health = 14

            self.num_summons = 4

        def cast_instant(self, x, y):

            spawner = GiantSpider

            if self.get_stat('aether'):
                spawner = PhaseSpider
            if self.get_stat('steel'):
                spawner = SteelSpider

            unit = spawner()
            unit.max_hp = 96
            apply_minion_bonuses(self, unit)

            unit.name = "%s Queen" % unit.name
            unit.asset_name += '_mother'

            def babyspider():
                unit = spawner()
                unit.max_hp = 3
                unit.name = "Baby %s" % unit.name
                unit.asset_name += '_child'
                
                for s in unit.spells:
                    if hasattr(s, 'damage'):
                        s.damage = 1

                unit.is_coward = True
                unit.buffs = [b for b in unit.buffs if not isinstance(b, SpiderBuff)]
                unit.buffs.append(MatureInto(spawner, 8))
                unit.source = self
                return unit

            unit.spells.insert(0, SimpleSummon(babyspider, num_summons=self.get_stat('num_summons'), cool_down=12))

            if self.get_stat("hatchery"):
                def abomination():
                    unit = spawner()
                    unit.asset_name += "_mass"
                    unit.name = "Arachnid Abomination"
                    if spawner == PhaseSpider:
                        unit.name = "Aether " + unit.name
                    elif spawner == SteelSpider:
                        unit.name = "Steel " + unit.name
                    unit.max_hp *= 2
                    unit.spells[0].damage += 3
                    unit.buffs.append(SpawnOnDeath(spawner, 2*self.get_stat("num_summons")))
                    return unit
                unit.buffs.append(SpawnOnDeath(abomination, 1))

            self.summon(unit, target=Point(x, y))

    if cls is DeathChill:

        def on_init(self):

            self.name = "Death Chill"
            
            self.level = 3
            self.tags = [Tags.Enchantment, Tags.Dark, Tags.Ice]

            self.duration = 5
            self.radius = 3
            self.damage = 11

            self.range = 9

            self.max_charges = 12

            self.can_target_empty = False

            self.upgrades['radius'] = (1, 2)
            self.upgrades['damage'] = (6, 2)
            self.upgrades['duration'] = (4, 3)
            self.upgrades["friendly"] = (1, 2, "Soothing Chill", "Death Chill now lasts indefinitely and is considered a buff if applied to one of your minions, instead healing it each turn by an amount equal to this spell's [damage] stat.\nThis still allows the minion to release a freezing explosion on death.")

        def get_impacted_tiles(self, x, y):
            return [Point(x, y)]

        def cast_instant(self, x, y):
            unit = self.caster.level.get_unit_at(x, y)
            if not unit:
                return

            buff = DeathChillDebuff(self)
            duration = self.get_stat("duration")
            if self.get_stat("friendly") and not are_hostile(unit, self.caster):
                buff.buff_type = BUFF_TYPE_BLESS
                duration = 0
            unit.apply_buff(buff, duration)

    if cls is DeathChillDebuff:

        def on_advance(self):
            if self.buff_type == BUFF_TYPE_BLESS:
                self.owner.deal_damage(-self.spell.get_stat('damage'), Tags.Heal, self.spell)
            else:
                self.owner.deal_damage(self.spell.get_stat('damage'), Tags.Dark, self.spell)

    if cls is ThornyPrisonSpell:

        def on_init(self):
            self.max_charges = 6
            self.name = "Prison of Thorns"
            self.range = 10
            self.minion_damage = 3
            self.minion_health = 7
            
            self.upgrades['minion_damage'] = (3, 2)
            self.upgrades['minion_health'] = (7, 2)
            self.upgrades['iron'] = (1, 5, "Iron Prison", "Summon iron thorns instead, which deal 3 more damage and are resistant to many forms of damage.", 'prison')
            self.upgrades['icy'] = (1, 6, "Icy Prison", "Summon icy thorns instead, which have a ranged [ice] attack in addition to [physical] melee.", 'prison')
            
            self.minion_duration = 15

            self.tags = [Tags.Nature, Tags.Conjuration]
            self.level = 3

        def cast(self, x, y):
            target_points = self.get_impacted_tiles(x, y)

            random.shuffle(target_points)

            for p in target_points:
                
                unit = Unit()
                unit.name = "Thorny Plant"
                unit.max_hp = self.get_stat('minion_health')
                unit.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))
                unit.stationary = True
                unit.turns_to_death = self.get_stat('minion_duration')
                unit.tags = [Tags.Nature]

                if self.get_stat('iron'):
                    unit.name = "Iron Thorn"
                    unit.asset_name = "fae_thorn_iron"
                    unit.tags.append(Tags.Metallic)
                    unit.spells[0].damage += 3
                if self.get_stat('icy'):
                    unit.name = "Icy Thorn"
                    unit.asset_name = "spriggan_bush_icy"
                    unit.spells.insert(0, SimpleRangedAttack(damage=self.get_stat('minion_damage'), range=3 + self.get_stat('minion_range'), damage_type=Tags.Ice))
                    
                self.summon(unit, p, radius=0)

                yield

    if cls is SummonBlueLion:

        def on_init(self):
            self.name = "Blue Lion"
            self.tags = [Tags.Nature, Tags.Holy, Tags.Conjuration, Tags.Arcane]
            self.max_charges = 2
            self.level = 5
            self.minion_health = 28
            self.minion_damage = 7
            self.shield_max = 2
            self.shield_cooldown = 3

            self.upgrades['shield_max'] = (2, 4)
            self.upgrades['shield_cooldown'] = (-1, 2)
            self.upgrades['minion_damage'] = (9, 2)
            self.upgrades['holy_bolt'] = (1, 4, "Holy Bolt", "The Blue Lion gains a [{minion_range}_range:minion_range] [holy] bolt attack.")

        def cast_instant(self, x, y):
            lion = Unit()
            lion.name = "Blue Lion"
            lion.team = self.caster.team
            lion.sprite.char = 'L'
            lion.sprite.color = Color(100, 120, 255)
            lion.max_hp = self.get_stat('minion_health')

            lion.flying = True

            sheen_spell = ShieldSightSpell(self.get_stat('shield_cooldown'), self.get_stat('shield_max'))
            sheen_spell.name = "Blue Lion Sheen"

            lion.spells.append(sheen_spell)
            lion.spells.append(SimpleMeleeAttack(self.get_stat('minion_damage')))

            if self.get_stat('holy_bolt'):
                bolt = SimpleRangedAttack(damage=self.get_stat('minion_damage'), damage_type=Tags.Holy, range=6 + self.get_stat('minion_range'))
                bolt.name = "Blue Lion Bolt"
                lion.spells.insert(1, bolt)

            lion.tags = [Tags.Nature, Tags.Arcane, Tags.Holy]
            lion.resists[Tags.Arcane] = 50
            lion.resists[Tags.Physical] = 50
            
            self.summon(lion, Point(x, y))

    if cls is FlameGateSpell:

        def on_init(self):
            self.range = 0
            self.max_charges = 4
            self.name = "Flame Gate"
            self.minion_duration = 9
            self.tags = [Tags.Fire, Tags.Enchantment, Tags.Conjuration]
            self.level = 3

            self.minion_damage = 7
            self.minion_health = 22
            self.minion_range = 4

            self.upgrades['minion_range'] = (2, 2)
            self.upgrades['minion_duration'] = (7, 2)
            self.upgrades['minion_damage'] = (7, 4)
            self.upgrades["remnant"] = (1, 3, "Gate Remnant", "When Flame Gate expires, or if you cast this spell again when it's active, you summon a fire elemental gate next to yourself, which automatically summons a fire elemental from this spell every 7 to 10 turns.")

    if cls is FlameGateBuff:

        def __init__(self, spell):
            Buff.__init__(self)
            self.name = "Flame Gate"
            self.spell = spell
            self.buff_type = BUFF_TYPE_BLESS
            self.stack_type = STACK_REPLACE
            self.asset = ['status', 'flame_gate']
            self.cast = True
            self.description = "Whenever you cast a fire spell, temporarily summon a fire elemental near the target.\n\nThis enchantment ends if you move or cast a non fire spell."

        def on_unapplied(self):
            if not self.spell.get_stat("remnant"):
                return
            def FireElemental():
                elemental = Unit()
                elemental.name = 'Fire Elemental'
                elemental.spells.append(SimpleRangedAttack("Elemental Fire", self.spell.minion_damage, Tags.Fire, self.spell.minion_range))
                elemental.resists[Tags.Fire] = 100
                elemental.resists[Tags.Physical] = 50
                elemental.resists[Tags.Ice] = -100
                elemental.turns_to_death = self.spell.minion_duration
                elemental.max_hp = self.spell.minion_health
                elemental.tags = [Tags.Elemental, Tags.Fire]
                return elemental
            gate = MonsterSpawner(FireElemental)
            apply_minion_bonuses(self.spell, gate)
            gate.turns_to_death = None
            self.spell.summon(gate, target=self.spell.caster, radius=5)

    if cls is ArcaneShield:

        def get_description(self):
            return "Whenever you cast an [arcane] spell, you gain [1_SH:shields], up to a max of [2_SH:shields]."

        def on_spell_cast(self, evt):
            if Tags.Arcane in evt.spell.tags:
                if self.owner.shields < 2:
                    self.owner.add_shields(1)

    if cls is MarchOfTheRighteous:

        def get_description(self):
            return "Whenever an enemy dies to [holy] damage, allies witnessing it gain [1_SH:shields] if they are not already shielded, and each enemy witnessing it has a 50% chance to take [1_holy:holy] damage.\nThis damage is fixed, and cannot be increased using shrines, skills, or buffs."

        def trigger(self, target):
            for u in self.owner.level.get_units_in_los(target):
                if not are_hostile(u, self.owner):
                    if u.shields < 1:
                        u.add_shields(1)
                elif random.random() < 0.5:
                    u.deal_damage(1, Tags.Holy, self)
            yield

    if cls is PlagueOfFilth:

        def on_init(self):

            self.tags = [Tags.Nature, Tags.Dark, Tags.Conjuration]
            self.name = "Plague of Filth"
            self.minion_health = 18
            self.minion_damage = 2
            self.minion_range = 4

            self.minion_duration = 7
            self.num_summons = 2

            self.max_channel = 40

            self.level = 4
            self.max_charges = 5

            self.upgrades['num_summons'] = (2, 4)
            self.upgrades['minion_duration'] = (4, 3)
            self.upgrades['minion_damage'] = (3, 3)
            self.upgrades["fire"] = (1, 7, "Fiery Vermin", "Instead summon flame toads and fire fly swarms, which are [fire] minions.\nFlame toads have more HP, damage, and range, and can no longer pull enemies, but instead shoot fireballs that deal [fire] damage in a [1_tile:radius] burst.\nFire fly swarms have their melee attacks replaced by ranged attacks dealing [fire] damage.", "vermin")
            self.upgrades["arcane"] = (1, 7, "Void Vermin", "Instead summon void toads and brain fly swarms, which are [arcane] minions.\nVoid toads have more HP, damage, and range, and their pull attacks are now beams that deal [arcane] damage and melt through walls.\nBrain flies' melee attacks deal [arcane] damage and increase the cooldown of a random one of the target's abilities by [1_turn:cooldown] if possible (does not work on units that can gain clarity); otherwise the target takes the same damage again.", "vermin")
            self.upgrades["giant"] = (1, 7, "Giant Vermin", "Each toad now has a 50% chance to be a towering toadbeast, and each fly swarm a bag of bugs.\nTowering toadbeasts have significantly more HP, damage, and range, and regenerate HP each turn.\nBags of bugs are [construct] minions that spawn fly swarms on death and have a chance to spawn fly swarms each turn.", "vermin")

        def get_description(self):
            return ("Summon a group of [{num_summons}:num_summons] toads and fly swarms.\n"
                    "Toads have [{minion_health}_HP:minion_health], and a ranged tongue attack which deals [{minion_damage}_physical:physical] damage and pulls enemies towards it. They can hop up to [{minion_range}_tiles:range] away.\n"
                    "Fly swarms have [{fly_health}_HP:minion_health], [75_dark:dark] resist, [75_physical:physical] resist, [-50_ice:ice] resist, and can fly. They have a melee attack which deals [{fly_damage}_physical:physical] damage.\n"
                    "The summons vanish after [{minion_duration}_turns:minion_duration].\n"
                    "This spell can be channeled for up to [{max_channel}_turns:duration].").format(**self.fmt_dict())

        def cast(self, x, y, channel_cast=False):

            if not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat('max_channel'))
                return

            damage_bonus = self.get_stat('minion_damage', base=0)
            health_bonus = self.get_stat('minion_health', base=0)
            range_bonus = self.get_stat("minion_range", base=0)
            duration = self.get_stat('minion_duration')
            fire = self.get_stat("fire")
            arcane = self.get_stat("arcane")
            giant = self.get_stat("giant")

            for _ in range(self.get_stat('num_summons')):

                if random.random() < .5:
                    if fire:
                        unit = FlameToad()
                    elif arcane:
                        unit = VoidToad()
                    else:
                        if giant and random.random() < 0.5:
                            unit = GiantToad()
                        else:
                            unit = HornedToad()
                    apply_minion_bonuses(self, unit)
                
                else:
                    def buff_fly(unit):
                        unit.turns_to_death = duration
                        unit.source = self
                        unit.max_hp += health_bonus//2
                        for s in unit.spells:
                            if hasattr(s, 'damage'):
                                s.damage += damage_bonus//2
                            if s.range >= 2:
                                s.range += range_bonus
                        return unit
                    if fire:
                        unit = FireFlies()
                    elif arcane:
                        unit = BrainFlies()
                        melee = unit.spells[0]
                        melee.onhit = lambda caster, target: increase_cooldown(caster, target, melee)
                        melee.description = "On hit, increase a random ability cooldown by 1 turn if possible; otherwise deal damage again."
                    else:
                        if giant and random.random() < 0.5:
                            unit = BagOfBugs(lambda: buff_fly(FlyCloud()))
                            unit.buffs[1].apply_bonuses = False
                        else:
                            unit = FlyCloud()
                    buff_fly(unit)
                
                unit.turns_to_death = duration
                self.summon(unit, Point(x, y), radius=5)
            yield

    if cls is IgnitePoison:

        def on_init(self):
            self.name = "Combust Poison"
            self.level = 3
            self.tags = [Tags.Sorcery, Tags.Fire, Tags.Nature]		

            self.max_charges = 9

            self.multiplier = 1
            self.radius = 2

            self.upgrades['radius'] = (1, 3)
            self.upgrades['max_charges'] = (9, 2)
            self.upgrades['multiplier'] = (1, 4)
            self.upgrades["afterburn"] = (1, 4, "Afterburn", "Instead of removing [poison], this spell now sets remaining [poison] duration to [{duration}_turns:duration].")
            self.add_upgrade(SpontaneousCombustion())

            self.range = 0

        def fmt_dict(self):
            stats = Spell.fmt_dict(self)
            stats["duration"] = self.get_stat("duration", base=10)
            return stats

        def cast(self, x, y):
            multiplier = self.get_stat('multiplier')
            radius = self.get_stat('radius')
            afterburn = self.get_stat("afterburn")
            duration = self.get_stat("duration", base=10)
            
            for u in list(self.caster.level.units):

                if not are_hostile(u, self.caster):
                    continue
                buff = u.get_buff(Poison)
                if not buff:
                    continue
                
                damage = buff.turns_left*multiplier
                for stage in Burst(self.caster.level, u, radius):
                    for point in stage:
                        self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)
                    yield

                if not afterburn:
                    u.remove_buff(buff)
                else:
                    buff.turns_left = duration

    if cls is LightningBoltSpell:

        def on_init(self):
            self.damage = 12
            self.range = 10
            self.name = "Lightning Bolt"
            self.max_charges = 18

            self.tags = [Tags.Lightning, Tags.Sorcery]
            self.level = 1

            self.upgrades['damage'] = (9, 3)
            self.upgrades['range'] = (5, 2)
            self.upgrades['max_charges'] = (12, 2)
            self.upgrades['channel'] = (1, 3, "Channeling", "Lightning bolt can be channeled for up to [{max_channel}_turns:duration].")

            self.upgrades['judgement'] = (1, 6, "Judgement Bolt", "Lightning Bolt also deals [holy] and [dark] damage to enemies.", "bolt")
            self.upgrades['energy'] = (1, 6, "Energy Bolt", "Lightning Bolt also deals [fire] and [arcane] damage to enemies.", "bolt")

        def cast(self, x, y, channel_cast=False):

            if self.get_stat('channel') and not channel_cast:
                self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat("max_channel", base=10))
                return

            dtypes = []
            if self.get_stat('judgement'):
                dtypes = [Tags.Holy, Tags.Dark]
            if self.get_stat('energy'):
                dtypes = [Tags.Fire, Tags.Arcane]

            damage = self.get_stat('damage')
            for point in Bolt(self.caster.level, self.caster, Point(x, y)):
                self.caster.level.deal_damage(point.x, point.y, damage, Tags.Lightning, self)
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit and are_hostile(unit, self.caster):
                    for dtype in dtypes:
                        unit.deal_damage(damage, dtype, self)
                else:
                    for dtype in dtypes:
                        self.caster.level.show_effect(point.x, point.y, dtype)

            yield

    if cls is Iceball:

        def on_init(self):
            self.tags = [Tags.Sorcery, Tags.Ice]
            self.level = 3
            self.name = "Iceball"

            self.damage = 14
            self.duration = 3
            self.radius = 2

            self.range = 7

            self.max_charges = 11

            self.upgrades['radius'] = (1, 2)
            self.upgrades['duration'] = (2, 2)
            self.upgrades['damage'] = (10, 2)
            self.upgrades['icecrush'] = (1, 4, "Ice Crush", "Enemies inside of the area of effect which are already [frozen] take [physical] damage before being subjected to the normal effects of this spell.")

        def cast(self, x, y):

            damage = self.get_stat('damage')
            crush = self.get_stat('icecrush')
            duration = self.get_stat('duration')

            for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
                for point in stage:
                    unit = self.caster.level.get_unit_at(point.x, point.y)
                    
                    if crush:
                        if unit and are_hostile(unit, self.caster) and unit.has_buff(FrozenBuff):
                            unit.deal_damage(damage, Tags.Physical, self)

                    self.caster.level.deal_damage(point.x, point.y, damage, Tags.Ice, self)

                    if unit:
                        unit.apply_buff(FrozenBuff(), duration)
                yield

    if cls is ToxinBurst:

        def cast(self, x, y):
            points = list(self.caster.level.get_points_in_ball(x, y, self.get_stat('radius')))
            random.shuffle(points)
            for p in points:

                unit = self.caster.level.get_unit_at(p.x, p.y)
                if unit:
                    unit.apply_buff(Poison(), self.get_stat('duration'))
                
                self.caster.level.deal_damage(p.x, p.y, self.get_stat('damage'), Tags.Poison, self)

                if random.random() < .3:
                    yield

        def get_description(self):
            return ("Apply [{duration}_turns:duration] of [poison] and deal [{damage}_poison:poison] damage to all units in a [{radius}_tile:radius] radius.\n"
                    + text.poison_desc).format(**self.fmt_dict())

    if cls is IceTap:

        def on_init(self):
            self.name = "Ice Tap"
            self.tags = [Tags.Ice, Tags.Arcane]
            self.level = 6
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
            self.global_triggers[EventOnBuffApply] = lambda evt: on_buff_apply(self, evt)
            self.copying = False

        def get_description(self):
            return ("Whenever a unit other than you is [frozen], inflict ice tap for the same duration.\n"
                    "The first [arcane] spell you cast each turn that targets an ice tapped unit will also be cast onto every valid ice tapped enemy target. Remove [freeze] and ice tap from all affected units.\n"
                    "Whenever the remaining duration of [freeze] on a unit is refreshed or extended, the remaining duration of ice tap will be lengthened to match if it is shorter.\nIf ice tap is removed prematurely and the unit is still [frozen], it will automatically reapply itself.").format(**self.fmt_dict())

        def on_buff_apply(self, evt):
            if not isinstance(evt.buff, FrozenBuff):
                return
            if evt.unit is self.owner:
                return
            buff = IceTapBuff()
            if not are_hostile(evt.unit, self.owner):
                buff.buff_type = BUFF_TYPE_BLESS
            evt.unit.apply_buff(buff, evt.buff.turns_left)

        def on_pre_advance(self):
            self.copying = False

        def on_spell_cast(self, evt):
            if self.copying or Tags.Arcane not in evt.spell.tags:
                return False

            unit = self.owner.level.get_unit_at(evt.x, evt.y)
            if not unit:
                return

            buff = unit.get_buff(IceTapBuff)
            if not buff:
                return
            unit.remove_buffs(FrozenBuff)
            unit.remove_buff(buff)

            self.copying = True

            for u in [u for u in self.owner.level.get_units_in_ball(self.owner, evt.spell.get_stat("range")) if are_hostile(self.owner, u) and u != unit]:
                b = u.get_buff(IceTapBuff)
                if not b:
                    continue
                if not evt.spell.can_cast(u.x, u.y):
                    continue
                self.owner.level.act_cast(self.owner, evt.spell, u.x, u.y, pay_costs=False)
                u.remove_buffs(FrozenBuff)
                u.remove_buff(b)

    if cls is Crystallographer:

        def on_init(self):
            self.name = "Crystal Power"
            self.tags = [Tags.Ice, Tags.Arcane, Tags.Sorcery]
            self.level = 4
            self.global_triggers[EventOnBuffApply] = lambda evt: on_buff_apply(self, evt)

        def on_applied(self, owner):
            for unit in self.owner.level.units:
                if not are_hostile(unit, self.owner):
                    continue
                for buff in unit.buffs:
                    if not isinstance(buff, GlassPetrifyBuff):
                        continue
                    change_buff(buff)

        def change_buff(buff):
            buff.owner.resists[Tags.Ice] -= 100
            buff.resists[Tags.Ice] = 0

        def get_description(self):
            return ("[Glassify] no longer increases enemies' [ice] resistance.\n"
                    "Whenever a unit is [frozen], inflict ice resonance for the same duration.\n"
                    "Your [sorcery] spells gain [2_damage:damage] for each [glassified] unit and each unit with ice resonance.\n"
                    "Whenever the remaining duration of [freeze] on a unit is refreshed or extended, the remaining duration of ice resonance will be lengthened to match if it is shorter.\nIf ice resonance is removed prematurely and the unit is still [frozen], it will automatically reapply itself.").format(**self.fmt_dict())

        def on_buff_apply(self, evt):
            if isinstance(evt.buff, GlassPetrifyBuff):
                if not are_hostile(evt.unit, self.owner):
                    return
                change_buff(evt.buff)
            elif isinstance(evt.buff, FrozenBuff):
                buff = IceResonanceBuff()
                if not are_hostile(evt.unit, self.owner):
                    buff.buff_type = BUFF_TYPE_BLESS
                evt.unit.apply_buff(buff, evt.buff.turns_left)

        def buff(self):
            amt = 0
            for u in self.owner.level.units:
                if u.has_buff(IceResonanceBuff) or u.has_buff(GlassPetrifyBuff):
                    amt += 2
            if amt:
                self.owner.apply_buff(CrystallographerActiveBuff(amt))
            yield

        def on_pre_advance(self):
            self.owner.remove_buffs(CrystallographerActiveBuff)
            if all([u.team == TEAM_PLAYER for u in self.owner.level.units]):
                return
            self.owner.level.queue_spell(buff(self))

    if cls is RegenAuraSpell:

        def on_init(self):
            self.name = "Regeneration Aura"
            self.heal = 4
            self.duration = 8
            self.range = 0
            self.radius = 10

            self.max_charges = 4
            self.level = 2

            self.tags = [Tags.Enchantment, Tags.Nature]
            self.upgrades['heal'] = (4, 2)
            self.upgrades['duration'] = (8, 1)
            self.upgrades['radius'] = (5, 3)
            self.upgrades["growth"] = (1, 5, "Growth", "Minions in the radius now gain max and current HP each turn equal to 1/4 of this spell's heal amount.\n[Slime] units are instead healed a second time each turn.")

        def cast_instant(self, x, y):
            self.caster.apply_buff(RegenAuraBuff(self), self.get_stat('duration'))

    for func_name, func in [(key, value) for key, value in locals().items() if callable(value)]:
        if hasattr(cls, func_name):
            setattr(cls, func_name, func)

for cls in [DeathBolt, FireballSpell, MagicMissile, PoisonSting, SummonWolfSpell, AnnihilateSpell, Blazerip, BloodlustSpell, DispersalSpell, FireEyeBuff, EyeOfFireSpell, IceEyeBuff, EyeOfIceSpell, LightningEyeBuff, EyeOfLightningSpell, RageEyeBuff, EyeOfRageSpell, Flameblast, Freeze, HealMinionsSpell, HolyBlast, HallowFlesh, mods.Bugfixes.Bugfixes.RotBuff, VoidMaw, InvokeSavagerySpell, MeltSpell, MeltBuff, PetrifySpell, SoulSwap, TouchOfDeath, ToxicSpore, VoidRip, CockatriceSkinSpell, BlindingLightSpell, Teleport, BlinkSpell, AngelicChorus, Darkness, MindDevour, Dominate, EarthquakeSpell, FlameBurstSpell, SummonFrostfireHydra, CallSpirits, SummonGiantBear, HolyFlame, HolyShieldSpell, ProtectMinions, LightningHaloSpell, LightningHaloBuff, MercurialVengeance, MercurizeSpell, MercurizeBuff, ArcaneVisionSpell, NightmareSpell, NightmareBuff, PainMirrorSpell, PainMirror, SealedFateBuff, SealFate, ShrapnelBlast, BestowImmortality, UnderworldPortal, VoidBeamSpell, VoidOrbSpell, BlizzardSpell, BoneBarrageSpell, ChimeraFarmiliar, ConductanceSpell, ConjureMemories, DeathGazeSpell, DispersionFieldSpell, DispersionFieldBuff, EssenceFlux, SummonFieryTormentor, SummonIceDrakeSpell, LightningFormSpell, StormSpell, OrbControlSpell, Permenance, PurityBuff, PuritySpell, PyrostaticPulse, SearingSealSpell, SearingSealBuff, SummonSiegeGolemsSpell, FeedingFrenzySpell, ShieldSiphon, StormNova, SummonStormDrakeSpell, IceWall, WatcherFormBuff, WatcherFormSpell, WheelOfFate, BallLightning, CantripCascade, IceWind, DeathCleaveBuff, DeathCleaveSpell, FaeCourt, SummonFloatingEye, FloatingEyeBuff, FlockOfEaglesSpell, SummonIcePhoenix, MegaAnnihilateSpell, PyrostaticHexSpell, PyroStaticHexBuff, RingOfSpiders, SlimeformSpell, DragonRoarSpell, SummonGoldDrakeSpell, ImpGateSpell, MysticMemory, SearingOrb, SummonKnights, MeteorShower, MulticastBuff, MulticastSpell, SpikeballFactory, WordOfIce, ArcaneCredit, ArcaneAccountant, Faestone, FaestoneBuff, GhostfireUpgrade, Hibernation, HibernationBuff, HolyWater, UnholyAlliance, WhiteFlame, AcidFumes, FrozenFragility, Teleblink, Houndlord, StormCaller, Boneguard, Frostbite, InfernoEngines, LightningWarp, OrbLord, DragonScalesSkill, DragonScalesBuff, SilverSpearSpell, HypocrisyStack, Hypocrisy, VenomBeastHealing, ChaosBarrage, SummonVoidDrakeSpell, MagnetizeSpell, MetalLord, SummonSpiderQueen, DeathChill, DeathChillDebuff, ThornyPrisonSpell, SummonBlueLion, FlameGateBuff, FlameGateSpell, ArcaneShield, MarchOfTheRighteous, MagnetizeBuff, PlagueOfFilth, IgnitePoison, LightningBoltSpell, Iceball, ToxinBurst, IceTap, Crystallographer, RegenAuraSpell, MinionRepair]:
    modify_class(cls)