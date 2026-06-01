from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from database.db_manager import DatabaseManager


class AnalyticsEngine:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.output_dir = Path("generated/charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_dataframe(self) -> pd.DataFrame:
        rows = self.db.analytics_dataframe()
        if not rows:
            return pd.DataFrame(
                columns=["id", "item_id", "user_id", "borrow_date", "due_date", "return_date", "fine_amount", "title", "category"]
            )
        df = pd.DataFrame([dict(row) for row in rows])
        for col in ("borrow_date", "due_date", "return_date"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def build_dashboard_charts(self) -> dict[str, Path]:
        df = self.load_dataframe()
        if df.empty:
            return {}

        result: dict[str, Path] = {}
        trend = df.groupby(df["borrow_date"].dt.to_period("M")).size()
        fig, ax = plt.subplots(figsize=(8, 4))
        trend.plot(ax=ax, marker="o", title="Borrow Trends")
        ax.set_xlabel("Month")
        ax.set_ylabel("Borrows")
        path = self.output_dir / "borrow_trends.png"
        fig.tight_layout()
        fig.savefig(path, dpi=140)
        plt.close(fig)
        result["borrow_trends"] = path

        popular = df.groupby("title").size().sort_values(ascending=False).head(10)
        fig, ax = plt.subplots(figsize=(8, 4))
        popular.plot(kind="bar", ax=ax, title="Most Popular Items")
        ax.set_xlabel("Item")
        ax.set_ylabel("Count")
        fig.tight_layout()
        path = self.output_dir / "popular_items.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        result["popular_items"] = path

        category = df.groupby("category").size()
        fig, ax = plt.subplots(figsize=(6, 6))
        category.plot(kind="pie", autopct="%1.1f%%", ax=ax, title="Category Distribution")
        ax.set_ylabel("")
        fig.tight_layout()
        path = self.output_dir / "category_distribution.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        result["category_distribution"] = path

        heat = df.copy()
        heat["weekday"] = heat["borrow_date"].dt.day_name()
        heat["hour"] = heat["borrow_date"].dt.hour.fillna(0)
        pivot = heat.pivot_table(index="weekday", columns="hour", values="id", aggfunc="count").fillna(0)
        pivot = pivot.reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        ).fillna(0)
        fig, ax = plt.subplots(figsize=(10, 4))
        cax = ax.imshow(pivot.values, cmap="viridis", aspect="auto")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45)
        ax.set_title("User Activity Heatmap")
        fig.colorbar(cax)
        fig.tight_layout()
        path = self.output_dir / "user_activity_heatmap.png"
        fig.savefig(path, dpi=140)
        plt.close(fig)
        result["user_activity_heatmap"] = path

        return result

    def inventory_health_metrics(self) -> dict[str, float]:
        rows = self.db.list_items()
        total = len(rows)
        available = sum(1 for row in rows if row["available"])
        utilization = (1 - (available / total)) * 100 if total else 0.0
        return {
            "total_items": float(total),
            "available_items": float(available),
            "utilization_percent": round(utilization, 2),
        }
