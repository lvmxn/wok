def schedule_review(ease_factor, interval, learning, repetitions, lapses, quality):
    next_ease = ease_factor
    next_interval = interval
    next_learning = learning
    next_repetitions = repetitions
    next_lapses = lapses

    if quality == "forgot":
        next_ease = max(1.3, round(next_ease - 0.2, 2))
        next_learning = 2
        next_repetitions = 0
        next_lapses += 1
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(1800),
        )

    if learning == 2:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            next_learning = 2
            return (
                next_ease,
                next_interval,
                next_learning,
                next_repetitions + 1,
                next_lapses,
                calculate_next_review(1800),
            )

        next_learning = 1
        next_repetitions += 1
        if quality == "easy":
            next_ease = round(next_ease + 0.15, 2)
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(1800),
        )

    if learning == 1:
        if quality == "hard":
            next_ease = max(1.3, round(next_ease - 0.05, 2))
            return (
                next_ease,
                next_interval,
                1,
                next_repetitions + 1,
                next_lapses,
                calculate_next_review(1800),
            )

        if repetitions >= 10:
            next_interval = 5*24*60*60
        else:
            next_interval = 24*60*60
        next_learning = 0
        next_repetitions += 1
        if quality == "easy":
            next_ease = round(next_ease + 0.15, 2)
        return (
            next_ease,
            next_interval,
            next_learning,
            next_repetitions,
            next_lapses,
            calculate_next_review(next_interval),
        )

    if quality == "hard":
        next_ease = max(1.3, round(next_ease - 0.15, 2))
        next_interval = max(1, round((next_interval//(24*60*60)) * 1.2))*24*60*60
    elif quality == "normal":
        next_interval = max(1, round((next_interval//(24*60*60)) * next_ease))*24*60*60
    elif quality == "easy":
        next_ease = round(next_ease + 0.15, 2)
        next_interval = max(1, round((next_interval//(24*60*60)) * next_ease * 1.3))*24*60*60

    if next_ease < 1.3:
        next_ease = 1.3
    next_repetitions += 1
    return next_ease, next_interval, 0, next_repetitions, next_lapses, calculate_next_review(next_interval)
