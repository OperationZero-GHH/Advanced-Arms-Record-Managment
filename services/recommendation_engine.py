from __future__ import annotations

import pandas as pd

from database.db_manager import DatabaseManager


class RecommendationEngine:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def recommend_items_for_user(self, user_id: int, limit: int = 5) -> list[str]:
        rows = self.db.analytics_dataframe()
        if not rows:
            return []
        df = pd.DataFrame([dict(row) for row in rows])
        user_history = df[df["user_id"] == user_id]
        if user_history.empty:
            global_popular = df.groupby("title").size().sort_values(ascending=False)
            return list(global_popular.head(limit).index)

        favorite_category = (
            user_history.groupby("category").size().sort_values(ascending=False).index[0]
        )
        candidates = df[df["category"] == favorite_category]
        ranked = candidates.groupby("title").size().sort_values(ascending=False)
        return list(ranked.head(limit).index)
