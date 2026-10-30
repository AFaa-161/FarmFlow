def recommend_action(
    quality_score: int,
    shelf_life_days: int,
    market_price: float,
    storage_cost: float,
    transport_cost: float,
    transport_hours: float,
) -> dict:
    """
    Simple rule-based demo decision engine.
    Costs and prices are illustrative user inputs, not live market data.
    """

    sell_profit = market_price

    store_profit = (
        market_price * 1.08
        - storage_cost
        if shelf_life_days >= 3
        else float("-inf")
    )

    transport_profit = (
        market_price * 1.12 - transport_cost
        if shelf_life_days * 24 > transport_hours
        else float("-inf")
    )

    options = {
        "SELL": sell_profit,
        "STORE": store_profit,
        "TRANSPORT": transport_profit,
    }

    # Low quality or very short shelf life: prefer selling quickly.
    if quality_score < 60 or shelf_life_days <= 1:
        action = "SELL"
    else:
        action = max(options, key=options.get)

    explanations = {
        "SELL": "Sell quickly to reduce the risk of spoilage.",
        "STORE": "Storage may improve the expected return if the crop lasts long enough.",
        "TRANSPORT": "Transport may offer a better return if the crop can safely make the journey.",
    }

    return {
        "recommended_action": action,
        "reason": explanations[action],
        "estimated_returns": {
            key: round(value, 2) if value != float("-inf") else None
            for key, value in options.items()
        },
        "currency": "INR",
        "note": "Illustrative estimates only; not live market prices or guaranteed profits.",
    }