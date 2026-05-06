"""
Team Analytics - Track validation metrics across teams.

Store and analyze validation results for teams.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationRecord:
    """A stored validation record."""
    id: Optional[int]
    timestamp: str
    file_path: str
    trust_score: int
    passed: bool
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    security_score: int
    hallucination_score: int
    logic_score: int
    best_practices_score: int
    user: str
    project: str
    branch: str
    commit: Optional[str]


@dataclass
class TeamStats:
    """Team statistics summary."""
    total_validations: int
    average_score: float
    pass_rate: float
    total_issues: int
    critical_issues: int
    score_trend: List[Dict[str, Any]]
    top_issues: List[Dict[str, int]]
    category_averages: Dict[str, float]
    project_breakdown: List[Dict[str, Any]]
    user_rankings: List[Dict[str, Any]]


class AnalyticsDB:
    """
    SQLite-based analytics storage.
    
    Stores validation results for team analysis.
    """

    DEFAULT_DB = ".aitrust_analytics.db"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or self.DEFAULT_DB)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                file_path TEXT,
                trust_score INTEGER,
                passed INTEGER,
                critical_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                security_score INTEGER,
                hallucination_score INTEGER,
                logic_score INTEGER,
                best_practices_score INTEGER,
                user TEXT,
                project TEXT,
                branch TEXT,
                commit TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON validations(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project ON validations(project)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user ON validations(user)
        """)

        conn.commit()
        conn.close()

    def record_validation(
        self,
        file_path: str,
        result: Any,
        user: str = "anonymous",
        project: str = "default",
        branch: str = "main",
        commit: Optional[str] = None
    ) -> int:
        """Store a validation result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        categories = result.categories or {}

        cursor.execute("""
            INSERT INTO validations (
                timestamp, file_path, trust_score, passed,
                critical_count, high_count, medium_count, low_count,
                security_score, hallucination_score, logic_score, best_practices_score,
                user, project, branch, commit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            file_path,
            result.trust_score,
            1 if result.passed else 0,
            len(result.critical_issues),
            len(result.high_issues),
            len([i for i in result.all_issues if i.severity == "medium"]),
            len([i for i in result.all_issues if i.severity == "low"]),
            categories.get("security", {}).get("score", 0) if isinstance(categories.get("security"), dict) else categories.get("security", 0),
            categories.get("hallucinations", {}).get("score", 0) if isinstance(categories.get("hallucinations"), dict) else categories.get("hallucinations", 0),
            categories.get("logic", {}).get("score", 0) if isinstance(categories.get("logic"), dict) else categories.get("logic", 0),
            categories.get("best_practices", {}).get("score", 0) if isinstance(categories.get("best_practices"), dict) else categories.get("best_practices", 0),
            user,
            project,
            branch,
            commit
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_stats(
        self,
        project: Optional[str] = None,
        user: Optional[str] = None,
        days: int = 30
    ) -> TeamStats:
        """Get team statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        where_clauses = [f"timestamp >= datetime('now', '-{days} days')"]
        params = []

        if project:
            where_clauses.append("project = ?")
            params.append(project)

        if user:
            where_clauses.append("user = ?")
            params.append(user)

        where_sql = " AND ".join(where_clauses)

        # Total validations
        cursor.execute(f"SELECT COUNT(*) FROM validations WHERE {where_sql}", params)
        total = cursor.fetchone()[0]

        if total == 0:
            conn.close()
            return TeamStats(
                total_validations=0,
                average_score=0,
                pass_rate=0,
                total_issues=0,
                critical_issues=0,
                score_trend=[],
                top_issues=[],
                category_averages={},
                project_breakdown=[],
                user_rankings=[]
            )

        # Average score
        cursor.execute(f"SELECT AVG(trust_score) FROM validations WHERE {where_sql}", params)
        avg_score = cursor.fetchone()[0] or 0

        # Pass rate
        cursor.execute(f"SELECT AVG(passed) FROM validations WHERE {where_sql}", params)
        pass_rate = (cursor.fetchone()[0] or 0) * 100

        # Total issues
        cursor.execute(f"""
            SELECT SUM(critical_count + high_count + medium_count + low_count)
            FROM validations WHERE {where_sql}
        """, params)
        total_issues = cursor.fetchone()[0] or 0

        # Critical issues
        cursor.execute(f"SELECT SUM(critical_count) FROM validations WHERE {where_sql}", params)
        critical_issues = cursor.fetchone()[0] or 0

        # Score trend (by day)
        cursor.execute(f"""
            SELECT date(timestamp) as day, AVG(trust_score), COUNT(*)
            FROM validations WHERE {where_sql}
            GROUP BY day ORDER BY day
        """, params)
        score_trend = [
            {"date": row[0], "avg_score": round(row[1], 1), "count": row[2]}
            for row in cursor.fetchall()
        ]

        # Category averages
        cursor.execute(f"""
            SELECT 
                AVG(security_score),
                AVG(hallucination_score),
                AVG(logic_score),
                AVG(best_practices_score)
            FROM validations WHERE {where_sql}
        """, params)
        row = cursor.fetchone()
        category_averages = {
            "security": round(row[0], 1) if row[0] else 0,
            "hallucinations": round(row[1], 1) if row[1] else 0,
            "logic": round(row[2], 1) if row[2] else 0,
            "best_practices": round(row[3], 1) if row[3] else 0,
        }

        # Project breakdown
        cursor.execute(f"""
            SELECT project, COUNT(*), AVG(trust_score), SUM(critical_count)
            FROM validations WHERE {where_sql}
            GROUP BY project ORDER BY COUNT(*) DESC LIMIT 10
        """, params)
        project_breakdown = [
            {
                "project": row[0],
                "validations": row[1],
                "avg_score": round(row[2], 1) if row[2] else 0,
                "critical_issues": row[3] or 0
            }
            for row in cursor.fetchall()
        ]

        # User rankings
        cursor.execute(f"""
            SELECT user, COUNT(*), AVG(trust_score)
            FROM validations WHERE {where_sql}
            GROUP BY user ORDER BY AVG(trust_score) DESC LIMIT 10
        """, params)
        user_rankings = [
            {
                "user": row[0],
                "validations": row[1],
                "avg_score": round(row[2], 1) if row[2] else 0
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        return TeamStats(
            total_validations=total,
            average_score=round(avg_score, 1),
            pass_rate=round(pass_rate, 1),
            total_issues=total_issues,
            critical_issues=critical_issues,
            score_trend=score_trend,
            top_issues=[],  # Would need issue storage
            category_averages=category_averages,
            project_breakdown=project_breakdown,
            user_rankings=user_rankings
        )

    def get_leaderboard(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """Get leaderboard of users by trust score."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT 
                user,
                COUNT(*) as validations,
                AVG(trust_score) as avg_score,
                SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passes
            FROM validations
            WHERE timestamp >= datetime('now', '-{days} days')
            GROUP BY user
            ORDER BY avg_score DESC
            LIMIT ?
        """, (limit,))

        leaderboard = [
            {
                "rank": i + 1,
                "user": row[0],
                "validations": row[1],
                "avg_score": round(row[2], 1),
                "pass_rate": round((row[3] / row[1]) * 100, 1) if row[1] > 0 else 0
            }
            for i, row in enumerate(cursor.fetchall())
        ]

        conn.close()
        return leaderboard

    def export_data(self, output_path: str, days: int = 30) -> None:
        """Export analytics data to JSON."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT * FROM validations
            WHERE timestamp >= datetime('now', '-{days} days')
            ORDER BY timestamp DESC
        """)

        columns = [desc[0] for desc in cursor.description]
        records = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()

        with open(output_path, 'w') as f:
            json.dump({
                "exported_at": datetime.utcnow().isoformat(),
                "records": records
            }, f, indent=2)


def generate_analytics_report(stats: TeamStats) -> str:
    """Generate a text analytics report."""
    lines = [
        "=" * 60,
        "📊 AI Trust Validator - Team Analytics Report",
        "=" * 60,
        "",
        "📈 Summary",
        "-" * 40,
        f"  Total Validations: {stats.total_validations}",
        f"  Average Score: {stats.average_score}/100",
        f"  Pass Rate: {stats.pass_rate}%",
        f"  Total Issues: {stats.total_issues}",
        f"  Critical Issues: {stats.critical_issues}",
        "",
        "📊 Category Averages",
        "-" * 40,
    ]

    for cat, score in stats.category_averages.items():
        lines.append(f"  {cat.title()}: {score}/100")

    if stats.project_breakdown:
        lines.extend([
            "",
            "📁 Project Breakdown",
            "-" * 40,
        ])
        for p in stats.project_breakdown[:5]:
            lines.append(f"  {p['project']}: {p['validations']} validations, {p['avg_score']} avg score")

    if stats.user_rankings:
        lines.extend([
            "",
            "🏆 Top Users",
            "-" * 40,
        ])
        for u in stats.user_rankings[:5]:
            lines.append(f"  {u['user']}: {u['avg_score']} avg score ({u['validations']} validations)")

    return "\n".join(lines)
