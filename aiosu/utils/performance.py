from __future__ import annotations

import abc
import math
from typing import Callable

from ..classes import BeatmapDifficultyAttributes
from ..classes import CatchPerformanceAttributes
from ..classes import ManiaPerformanceAttributes
from ..classes import Mod
from ..classes import OsuPerformanceAttributes
from ..classes import PerformanceAttributes
from ..classes import Score
from ..classes import TaikoPerformanceAttributes
from .accuracy import CatchAccuracyCalculator
from .accuracy import ManiaAccuracyCalculator
from .accuracy import OsuAccuracyCalculator
from .accuracy import TaikoAccuracyCalculator

__all__ = [
    "OsuPerformanceCalculator",
    "TaikoPerformanceCalculator",
    "ManiaPerformanceCalculator",
    "CatchPerformanceCalculator",
]

OSU_BASE_MULTIPLIER = 1.14
TAIKO_BASE_MULTIPLIER = 1.13
MANIA_BASE_MULTIPLIER = 8.0
CATCH_BASE_MULTIPLIER = 1

clamp: Callable[[float, float, float], float] = (
    lambda x, l, u: l if x < l else u if x > u else x
)


class AbstractPerformanceCalculator(abc.ABC):
    def __init__(self, difficulty_attributes: BeatmapDifficultyAttributes):
        self.difficulty_attributes = difficulty_attributes

    @abc.abstractmethod
    def calculate(self, score: Score) -> PerformanceAttributes:
        ...


class OsuPerformanceCalculator(AbstractPerformanceCalculator):
    def calculate(self, score: Score) -> OsuPerformanceAttributes:
        effective_miss_count = self._calculate_effective_miss_count(score)
        total_hits = (
            score.statistics.count_300
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )

        multiplier = OSU_BASE_MULTIPLIER

        if Mod.NoFail in score.mods:
            multiplier *= max(0.9, 1.0 - 0.02 * effective_miss_count)

        if Mod.SpunOut in score.mods and total_hits > 0:
            multiplier *= 1.0 - math.pow(
                (self.score.beatmap.count_spinners / total_hits),
                0.85,
            )

        aim_value = self._compute_aim_value(score, effective_miss_count, total_hits)
        speed_value = self._compute_speed_value(score, effective_miss_count, total_hits)
        accuracy_value = self._compute_accuracy_value(score, total_hits)
        flashlight_value = self._compute_flashlight_value(
            score,
            effective_miss_count,
            total_hits,
        )

        total_value = (
            math.pow(
                math.pow(aim_value, 1.1)
                + math.pow(speed_value, 1.1)
                + math.pow(accuracy_value, 1.1)
                + math.pow(flashlight_value, 1.1),
                1.0 / 1.1,
            )
            * multiplier
        )

        return OsuPerformanceAttributes(
            total=total_value,
            aim=aim_value,
            speed=speed_value,
            accuracy=accuracy_value,
            flashlight=flashlight_value,
            effective_miss_count=effective_miss_count,
        )

    def _compute_aim_value(
        self,
        score: Score,
        effective_miss_count: float,
        total_hits: int,
    ) -> float:
        aim_value = (
            math.pow(
                5.0 * max(1.0, self.difficulty_attributes.aim_difficulty / 0.0675)
                - 4.0,
                3.0,
            )
            / 100000.0
        )

        length_bonus = (
            0.95
            + 0.4 * min(1.0, total_hits / 2000.0)
            + ((math.log10(total_hits / 2000.0) * 0.5) * int(total_hits > 2000))
        )
        aim_value *= length_bonus

        if effective_miss_count > 0:
            aim_value *= 0.97 * math.pow(
                1 - math.pow(effective_miss_count / total_hits, 0.775),
                effective_miss_count,
            )

        aim_value *= self._get_combo_scaling_factor(score)

        approach_rate_factor = 0.0
        if self.difficulty_attributes.approach_rate > 10.33:
            approach_rate_factor = 0.3 * (
                self.difficulty_attributes.approach_rate - 10.33
            )
        elif self.difficulty_attributes.approach_rate < 8.0:
            approach_rate_factor = 0.05 * (
                8.0 - self.difficulty_attributes.approach_rate
            )

        aim_value *= 1.0 + approach_rate_factor * length_bonus

        if Mod.Hidden in score.mods:
            aim_value *= 1.0 + 0.04 * (12.0 - self.difficulty_attributes.approach_rate)

        if score.beatmap.count_sliders > 0:
            estimate_difficult_sliders = score.beatmap.count_sliders * 0.15

            estimate_slider_ends_dropped = clamp(
                min(
                    score.statistics.count_100
                    + score.statistics.count_50
                    + score.statistics.count_miss,
                    self.difficulty_attributes.max_combo - score.max_combo,
                ),
                0,
                estimate_difficult_sliders,
            )

            slider_nerf_factor = (
                1 - self.difficulty_attributes.slider_factor
            ) * math.pow(
                1 - estimate_slider_ends_dropped / estimate_difficult_sliders,
                3,
            ) + self.difficulty_attributes.slider_factor

            aim_value *= slider_nerf_factor

        accuracy = score.accuracy if score.accuracy <= 1.0 else score.accuracy / 100
        aim_value *= accuracy
        aim_value *= (
            0.98 + math.pow(self.difficulty_attributes.overall_difficulty, 2) / 2500
        )

        return aim_value

    def _compute_speed_value(
        self,
        score: Score,
        effective_miss_count: float,
        total_hits: int,
    ) -> float:
        speed_value = (
            math.pow(
                5.0 * max(1.0, self.difficulty_attributes.speed_difficulty / 0.0675)
                - 4.0,
                3.0,
            )
            / 100000.0
        )

        length_bonus = (
            0.95
            + 0.4 * min(1.0, total_hits / 2000.0)
            + ((math.log10(total_hits / 2000.0) * 0.5) * int(total_hits > 2000))
        )
        speed_value *= length_bonus

        if effective_miss_count > 0:
            speed_value *= 0.97 * math.pow(
                1 - math.pow(effective_miss_count / total_hits, 0.775),
                math.pow(effective_miss_count, 0.875),
            )

        speed_value *= self._get_combo_scaling_factor(score)

        approach_rate_factor = 0.0
        if self.difficulty_attributes.approach_rate > 10.33:
            approach_rate_factor = 0.3 * (
                self.difficulty_attributes.approach_rate - 10.33
            )

        speed_value *= 1.0 + approach_rate_factor * length_bonus

        if Mod.Hidden in score.mods:
            speed_value *= 1.0 + 0.04 * (
                12.0 - self.difficulty_attributes.approach_rate
            )

        relevant_total_diff = total_hits - self.difficulty_attributes.speed_note_count
        relevant_count_great = max(0, score.statistics.count_300 - relevant_total_diff)
        relevant_count_ok = max(
            0,
            score.statistics.count_100
            - max(0, relevant_total_diff - score.statistics.count_300),
        )
        relevant_count_meh = max(
            0,
            score.statistics.count_50
            - max(
                0,
                relevant_total_diff
                - score.statistics.count_300
                - score.statistics.count_100,
            ),
        )

        relevant_accuracy = 0
        if self.difficulty_attributes.speed_note_count > 0:
            relevant_accuracy = (
                relevant_count_great * 6.0
                + relevant_count_ok * 2.0
                + relevant_count_meh
            ) / (self.difficulty_attributes.speed_note_count * 6.0)

        accuracy = score.accuracy if score.accuracy <= 1.0 else score.accuracy / 100

        speed_value *= (
            0.95 + math.pow(self.difficulty_attributes.overall_difficulty, 2) / 750
        ) * math.pow(
            (accuracy + relevant_accuracy) / 2.0,
            (14.5 - max(self.difficulty_attributes.overall_difficulty, 8)) / 2,
        )

        speed_value *= math.pow(
            0.99,
            (score.statistics.count_50 - total_hits / 500.0)
            * int(score.statistics.count_50 > total_hits / 500.0),
        )

        return speed_value

    def _compute_accuracy_value(
        self,
        score: Score,
        total_hits: int,
    ) -> float:
        accuracy_calculator = OsuAccuracyCalculator()
        better_accuracy_percentage = accuracy_calculator.calculate_weighted(score)

        accuracy_value = (
            math.pow(1.52163, self.difficulty_attributes.overall_difficulty)
            * math.pow(better_accuracy_percentage, 24)
            * 2.83
        )

        accuracy_value *= min(
            1.15,
            math.pow(score.beatmap.count_circles / 1000.0, 0.3),
        )

        if Mod.Hidden in score.mods:
            accuracy_value *= 1.08

        if Mod.Flashlight in score.mods:
            accuracy_value *= 1.02

        return accuracy_value

    def _compute_flashlight_value(
        self,
        score: Score,
        effective_miss_count: float,
        total_hits: int,
    ) -> float:
        if Mod.Flashlight not in score.mods:
            return 0.0

        flashlight_value = (
            math.pow(self.difficulty_attributes.flashlight_difficulty, 2.0) * 25.0
        )

        if effective_miss_count > 0:
            flashlight_value *= 0.97 * math.pow(
                1 - math.pow(effective_miss_count / total_hits, 0.775),
                math.pow(effective_miss_count, 0.875),
            )

        flashlight_value *= self._get_combo_scaling_factor(score)

        flashlight_value *= (
            0.7
            + 0.1 * min(1.0, total_hits / 200.0)
            + 0.2 * (min(1.0, (total_hits - 200) / 200.0) * int(total_hits > 200))
        )

        accuracy = score.accuracy if score.accuracy <= 1.0 else score.accuracy / 100
        flashlight_value *= 0.5 + accuracy / 2.0
        flashlight_value *= (
            0.98 + math.pow(self.difficulty_attributes.overall_difficulty, 2) / 2500.0
        )

        return flashlight_value

    def _calculate_effective_miss_count(self, score: Score) -> float:
        combo_based_miss_count = 0.0

        if score.beatmap.count_sliders > 0:
            full_combo_threshold = (
                self.difficulty_attributes.max_combo - 0.1 * score.beatmap.count_sliders
            )

            if score.max_combo < full_combo_threshold:
                combo_based_miss_count = full_combo_threshold / max(
                    1.0,
                    score.max_combo,
                )

        combo_based_miss_count = min(
            combo_based_miss_count,
            score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss,
        )

        return max(score.statistics.count_miss, combo_based_miss_count)

    def _get_combo_scaling_factor(self, score: Score) -> float:
        if self.difficulty_attributes.max_combo <= 0:
            return 1.0

        return min(
            math.pow(score.max_combo, 0.8)
            / math.pow(self.difficulty_attributes.max_combo, 0.8),
            1.0,
        )


class TaikoPerformanceCalculator(AbstractPerformanceCalculator):
    def calculate(self, score: Score) -> TaikoPerformanceAttributes:
        accuracy_calculator = TaikoAccuracyCalculator()
        accuracy = accuracy_calculator.calculate_weighted(score)

        effective_miss_count = self._calculate_effective_miss_count(score)
        total_hits = (
            score.statistics.count_300
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )

        multiplier = TAIKO_BASE_MULTIPLIER

        if Mod.Hidden in score.mods:
            multiplier *= 1.075

        if Mod.Easy in score.mods:
            multiplier *= 0.975

        difficulty_value = self._compute_difficulty_value(
            score,
            total_hits,
            effective_miss_count,
            accuracy,
        )
        accuracy_value = self._compute_accuracy_value(
            score,
            total_hits,
            accuracy,
        )
        total_value = (
            math.pow(
                math.pow(difficulty_value, 1.1) + math.pow(accuracy_value, 1.1),
                1.0 / 1.1,
            )
            * multiplier
        )

        total = (
            math.pow(
                math.pow(difficulty_value, 1.1) + math.pow(accuracy_value, 1.1),
                1.0 / 1.1,
            )
        ) * multiplier

        return TaikoPerformanceAttributes(
            total=total_value,
            difficulty=difficulty_value,
            accuracy=accuracy_value,
            effective_miss_count=effective_miss_count,
        )

    def _compute_difficulty_value(
        self,
        score: Score,
        total_hits: int,
        effective_miss_count: float,
        accuracy: float,
    ) -> float:
        difficulty_value = (
            math.pow(
                5 * max(1.0, self.difficulty_attributes.star_rating / 0.115) - 4.0,
                2.25,
            )
            / 1150.0
        )

        length_bonus = 1 + 0.1 * min(1.0, total_hits / 1500.0)
        difficulty_value *= length_bonus

        difficulty_value *= math.pow(0.986, effective_miss_count)

        if Mod.Easy in score.mods:
            difficulty_value *= 0.985

        if Mod.Hidden in score.mods:
            difficulty_value *= 1.025

        if Mod.HardRock in score.mods:
            difficulty_value *= 1.050

        if Mod.Flashlight in score.mods:
            difficulty_value *= 1.050 * length_bonus

        difficulty_value *= math.pow(accuracy, 2.0)
        return difficulty_value

    def _compute_accuracy_value(
        self,
        score: Score,
        total_hits: int,
        accuracy: float,
    ) -> float:
        if self.difficulty_attributes.great_hit_window <= 0:
            return 0

        accuracy_value = (
            math.pow(60.0 / self.difficulty_attributes.great_hit_window, 1.1)
            * math.pow(accuracy, 8.0)
            * math.pow(self.difficulty_attributes.star_rating, 0.4)
            * 27.0
        )

        length_bonus = min(1.15, math.pow(total_hits / 1500.0, 0.3))
        accuracy_value *= length_bonus

        if Mod.Hidden in score.mods and Mod.Flashlight in score.mods:
            accuracy_value *= max(1.050, 1.075 * length_bonus)

        return accuracy_value

    def _calculate_effective_miss_count(self, score: Score) -> float:
        return (
            max(
                1.0,
                1000.0
                / (
                    score.statistics.count_300
                    + score.statistics.count_100
                    + score.statistics.count_50
                ),
            )
            * score.statistics.count_miss
        )


class ManiaPerformanceCalculator(AbstractPerformanceCalculator):
    def calculate(self, score: Score) -> ManiaPerformanceAttributes:
        accuracy_calculator = ManiaAccuracyCalculator()
        accuracy = ManiaAccuracyCalculator().calculate_weighted(score)

        total_hits = (
            score.statistics.count_geki
            + score.statistics.count_300
            + score.statistics.count_katu
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )

        multiplier = MANIA_BASE_MULTIPLIER

        if Mod.NoFail in score.mods:
            multiplier *= 0.75

        if Mod.Easy in score.mods:
            multiplier *= 0.5

        difficulty_value = self._compute_difficulty_value(accuracy, total_hits)
        total_value = difficulty_value * multiplier

        return ManiaPerformanceAttributes(
            total=total_value,
            difficulty=difficulty_value,
        )

    def _compute_difficulty_value(self, accuracy: float, total_hits: int) -> float:
        difficulty_value = (
            math.pow(max(self.difficulty_attributes.star_rating - 0.15, 0.05), 2.2)
            * max(0.0, 5.0 * accuracy - 4.0)
            * (1.0 + 0.1 * min(1.0, total_hits / 1500))
        )

        return difficulty_value


class CatchPerformanceCalculator(AbstractPerformanceCalculator):
    def calculate(self, score: Score) -> CatchPerformanceAttributes:
        accuracy_calculator = CatchAccuracyCalculator()
        accuracy = accuracy_calculator.calculate_weighted(score)

        total_combo_hits = (
            score.statistics.count_miss
            + score.statistics.count_100
            + score.statistics.count_300
        )
        total_value = (
            math.pow(
                5.0 * max(1.0, self.difficulty_attributes.star_rating / 0.0049) - 4.0,
                2.0,
            )
            / 100000.0
        )

        length_bonus = (
            0.95
            + 0.3 * min(1.0, total_combo_hits / 2500.0)
            + (
                (math.log10(total_combo_hits / 2500.0) * 0.475)
                * int(total_combo_hits > 2500)
            )
        )
        total_value *= length_bonus

        total_value *= math.pow(0.97, score.statistics.count_miss)

        if self.difficulty_attributes.max_combo > 0:
            total_value *= min(
                math.pow(score.max_combo, 0.8)
                / math.pow(self.difficulty_attributes.max_combo, 0.8),
                1.0,
            )

        approach_rate = self.difficulty_attributes.approach_rate
        approach_rate_factor = 1.0

        if approach_rate > 9.0:
            approach_rate_factor += 0.1 * (approach_rate - 9.0)

        if approach_rate > 10.0:
            approach_rate_factor += 0.1 * (approach_rate - 10.0)
        elif approach_rate < 8.0:
            approach_rate_factor += 0.025 * (8.0 - approach_rate)

        total_value *= approach_rate_factor

        if Mod.Hidden in score.mods:
            if approach_rate <= 10.0:
                total_value *= 1.05 + 0.075 * (10.0 - approach_rate)
            elif approach_rate > 10.0:
                total_value *= 1.01 + 0.04 * (11.0 - min(11.0, approach_rate))

        if Mod.Flashlight in score.mods:
            total_value *= 1.35 * length_bonus

        total_value *= math.pow(accuracy, 5.5)

        if Mod.NoFail in score.mods:
            total_value *= 0.90

        return CatchPerformanceAttributes(total=total_value)