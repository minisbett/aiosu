from __future__ import annotations

import abc

from ..classes import Score


class AbstractAccuracyCalculator(abc.ABC):
    @abc.abstractstaticmethod
    def calculate(score: Score) -> float:
        ...

    @abc.abstractstaticmethod
    def calculate_weighted(score: Score) -> float:
        ...


class OsuAccuracyCalculator(AbstractAccuracyCalculator):
    @staticmethod
    def calculate(score: Score) -> float:
        total_hits = (
            score.statistics.count_300
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )

        accuracy = 0.0
        if score.beatmap.count_objects > 0:
            accuracy = max(
                (
                    score.statistics.count_300 * 6
                    + score.statistics.count_100 * 2
                    + score.statistics.count_50
                )
                / (total_hits * 6),
                0,
            )

        return accuracy

    @staticmethod
    def calculate_weighted(score: Score) -> float:
        total_hits = (
            score.statistics.count_300
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )
        amount_hit_objects_with_accuracy = score.beatmap.count_circles

        better_accuracy_percentage = 0.0
        if amount_hit_objects_with_accuracy > 0:
            better_accuracy_percentage = max(
                (
                    (
                        score.statistics.count_300
                        - (total_hits - amount_hit_objects_with_accuracy)
                    )
                    * 6
                    + score.statistics.count_100 * 2
                    + score.statistics.count_50
                )
                / (amount_hit_objects_with_accuracy * 6),
                0,
            )

        return better_accuracy_percentage


class TaikoAccuracyCalculator(AbstractAccuracyCalculator):
    @staticmethod
    def calculate(score: Score) -> float:
        total_hits = (
            score.statistics.count_300
            + score.statistics.count_100
            + score.statistics.count_50
            + score.statistics.count_miss
        )

        accuracy = 0.0
        if total_hits > 0:
            accuracy = (
                score.statistics.count_300 * 2.0 + score.statistics.count_100
            ) / (total_hits * 2.0)

        return accuracy

    @classmethod
    def calculate_weighted(cls, score: Score) -> float:
        return cls.calculate(score)


class ManiaAccuracyCalculator(AbstractAccuracyCalculator):
    @staticmethod
    def calculate(score: Score) -> float:
        count_perfect = score.statistics.count_geki
        count_great = score.statistics.count_300
        count_good = score.statistics.count_katu
        count_ok = score.statistics.count_100
        count_meh = score.statistics.count_50
        count_miss = score.statistics.count_miss

        total_hits = (
            count_perfect + count_ok + count_great + count_good + count_meh + count_miss
        )

        accuracy = 0.0
        if total_hits > 0:
            accuracy = (
                +((count_perfect + count_great) * 300)
                + (count_good * 200)
                + (count_ok * 100)
                + (count_meh * 50)
            ) / (total_hits * 300)

        return accuracy

    @staticmethod
    def calculate_weighted(score: Score) -> float:
        count_perfect = score.statistics.count_geki
        count_great = score.statistics.count_300
        count_good = score.statistics.count_katu
        count_ok = score.statistics.count_100
        count_meh = score.statistics.count_50
        count_miss = score.statistics.count_miss

        total_hits = (
            count_perfect + count_ok + count_great + count_good + count_meh + count_miss
        )

        accuracy = 0.0
        if total_hits > 0:
            accuracy = (
                +(count_perfect * 320)
                + (count_great * 300)
                + (count_good * 200)
                + (count_ok * 100)
                + (count_meh * 50)
            ) / (total_hits * 320)

        return accuracy


class CatchAccuracyCalculator(AbstractAccuracyCalculator):
    @staticmethod
    def calculate(score: Score) -> float:
        fruits_hit = score.statistics.count_300
        ticks_hit = score.statistics.count_100
        tiny_ticks_hit = score.statistics.count_50
        tiny_ticks_missed = score.statistics.count_katu
        misses = score.statistics.count_miss

        total_combo_hits = misses + ticks_hit + fruits_hit
        total_hits = (
            tiny_ticks_hit + ticks_hit + fruits_hit + misses + tiny_ticks_missed
        )
        successful_hits = tiny_ticks_hit + ticks_hit + fruits_hit

        accuracy = 0.0
        if total_hits != 0:
            accuracy = float(successful_hits) / total_hits

        return accuracy

    @classmethod
    def calculate_weighted(cls, score: Score) -> float:
        return cls.calculate(score)