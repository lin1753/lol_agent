"""Tests for Memory V2 (P4-T1)."""

import pytest

from memory.hero_memory import HeroMemoryV2
from memory.objective_memory import ObjectiveMemory
from memory.fight_memory import FightMemory
from perception.minimap_parser import MinimapDetection


class TestHeroMemoryV2:
    def test_empty(self):
        mem = HeroMemoryV2()
        assert mem.get_missing_enemies() == []
        assert mem.get_jungler_missing_duration() == 0.0

    def test_update_tracks_heroes(self):
        mem = HeroMemoryV2()
        dets = [
            MinimapDetection(x=100, y=50, team="enemy"),
            MinimapDetection(x=200, y=150, team="ally"),
        ]
        mem.update(dets, current_time=100.0)
        assert len(mem.get_all_tracked()) == 2

    def test_missing_duration(self):
        mem = HeroMemoryV2()
        mem.update([MinimapDetection(x=100, y=50, team="enemy")], current_time=100.0)
        mem.update([], current_time=130.0)  # enemy gone
        missing = mem.get_missing_enemies()
        assert len(missing) == 1
        assert missing[0]["missing_seconds"] == 30.0

    def test_hero_reappears(self):
        mem = HeroMemoryV2()
        dets = [MinimapDetection(x=100, y=50, team="enemy")]
        mem.update(dets, current_time=100.0)
        mem.update([], current_time=130.0)  # gone
        assert len(mem.get_missing_enemies()) == 1
        mem.update(dets, current_time=140.0)  # back
        assert len(mem.get_missing_enemies()) == 0

    def test_lane_classification(self):
        mem = HeroMemoryV2()
        mem.update([MinimapDetection(x=100, y=30, team="enemy")], current_time=100.0)
        record = list(mem.get_all_tracked().values())[0]
        assert record.last_lane == "top"

    def test_proximity_matching(self):
        """Same position across frames should match the same hero."""
        mem = HeroMemoryV2()
        mem.update([MinimapDetection(x=100, y=50, team="enemy")], current_time=100.0)
        mem.update([MinimapDetection(x=105, y=52, team="enemy")], current_time=101.0)
        assert len(mem.get_all_tracked()) == 1  # Same hero matched

    def test_clear(self):
        mem = HeroMemoryV2()
        mem.update([MinimapDetection(x=100, y=50, team="enemy")], current_time=100.0)
        mem.clear()
        assert len(mem.get_all_tracked()) == 0


class TestObjectiveMemory:
    def test_default_timers(self):
        mem = ObjectiveMemory()
        timers = mem.get_spawn_timers(current_time=0)
        assert timers["dragon_spawn_in"] == 300  # 5 min to first spawn
        assert timers["baron_spawn_in"] == 1200  # 20 min to first spawn

    def test_record_kill(self):
        mem = ObjectiveMemory()
        mem.record_kill("dragon", game_time=600)
        obj = mem.get_objective("dragon")
        assert obj.alive is False
        assert obj.last_killed_time == 600
        assert obj.kill_count == 1

    def test_respawn_after_kill(self):
        mem = ObjectiveMemory()
        mem.record_kill("dragon", game_time=600)
        timers = mem.get_spawn_timers(current_time=650)
        assert timers["dragon_spawn_in"] == 250  # 300 - 50 = 250s remaining

    def test_herald_window(self):
        mem = ObjectiveMemory()
        timers = mem.get_spawn_timers(current_time=900)  # 15 min, past 11:00 despawn
        assert timers["herald_spawn_in"] == -1.0

    def test_record_spawn(self):
        mem = ObjectiveMemory()
        mem.record_kill("dragon", game_time=600)
        mem.record_spawn("dragon")
        obj = mem.get_objective("dragon")
        assert obj.alive is True

    def test_clear(self):
        mem = ObjectiveMemory()
        mem.record_kill("dragon", game_time=600)
        mem.clear()
        obj = mem.get_objective("dragon")
        assert obj.alive is True
        assert obj.kill_count == 0


class TestFightMemory:
    def test_empty(self):
        mem = FightMemory()
        assert mem.get_recent_fights() == []
        assert mem.get_recent_deaths() == []
        assert mem.get_fight_win_rate() == 0.5

    def test_record_fight(self):
        mem = FightMemory()
        mem.record_fight(time=600, result="won", ally_count=4, enemy_count=3)
        fights = mem.get_recent_fights()
        assert len(fights) == 1
        assert fights[0].result == "won"

    def test_record_death(self):
        mem = FightMemory()
        mem.record_death(time=600, killer="enemy_mid", location="mid")
        deaths = mem.get_recent_deaths()
        assert len(deaths) == 1
        assert deaths[0].killer == "enemy_mid"

    def test_win_rate(self):
        mem = FightMemory()
        mem.record_fight(time=100, result="won")
        mem.record_fight(time=200, result="won")
        mem.record_fight(time=300, result="lost")
        assert mem.get_fight_win_rate() == pytest.approx(2 / 3)

    def test_death_count_since(self):
        mem = FightMemory()
        mem.record_death(time=100)
        mem.record_death(time=200)
        mem.record_death(time=300)
        assert mem.get_death_count_since(since_time=150) == 2

    def test_max_limit(self):
        mem = FightMemory(max_fights=3, max_deaths=3)
        for i in range(10):
            mem.record_fight(time=i * 100, result="won")
            mem.record_death(time=i * 100)
        assert len(mem.get_recent_fights(100)) == 3
        assert len(mem.get_recent_deaths(100)) == 3

    def test_clear(self):
        mem = FightMemory()
        mem.record_fight(time=100, result="won")
        mem.record_death(time=100)
        mem.clear()
        assert len(mem.get_recent_fights()) == 0
        assert len(mem.get_recent_deaths()) == 0
