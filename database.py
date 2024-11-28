import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class InsightDatabase:
    def __init__(self, db_path='insights.db'):
        """Initialize the database connection"""
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create insights table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        insight_text TEXT NOT NULL,
                        insight_type TEXT NOT NULL,
                        confidence REAL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        validated INTEGER DEFAULT 0,
                        validation_feedback TEXT,
                        UNIQUE(insight_text, insight_type) ON CONFLICT REPLACE
                    )
                ''')
                
                # Create patterns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT NOT NULL,
                        pattern_data TEXT NOT NULL,
                        confidence REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(pattern_type) ON CONFLICT REPLACE
                    )
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")

    def add_insight(self, insight_text, insight_type, confidence=None, metadata=None):
        """Add a new insight to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO insights (insight_text, insight_type, confidence, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (insight_text, insight_type, confidence, json.dumps(metadata) if metadata else None))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding insight: {str(e)}")
            return None

    def get_insights(self, limit=10, insight_type=None):
        """Get the most recent insights"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if insight_type:
                    cursor.execute("""
                        SELECT id, insight_text, insight_type, confidence, metadata, created_at, validated, validation_feedback
                        FROM insights
                        WHERE insight_type = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (insight_type, limit))
                else:
                    cursor.execute("""
                        SELECT id, insight_text, insight_type, confidence, metadata, created_at, validated, validation_feedback
                        FROM insights
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))
                
                insights = []
                for row in cursor.fetchall():
                    insight = {
                        'id': row[0],
                        'insight_text': row[1],
                        'insight_type': row[2],
                        'confidence': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {},
                        'timestamp': row[5],
                        'validated': bool(row[6]),
                        'validation_feedback': row[7]
                    }
                    insights.append(insight)
                return insights
                
        except Exception as e:
            logger.error(f"Error getting insights: {str(e)}")
            return []

    def add_pattern(self, pattern_type, pattern_data, confidence=None):
        """Add or update a pattern"""
        try:
            # Ensure pattern_data is JSON serializable
            if isinstance(pattern_data, dict):
                pattern_data = json.dumps(pattern_data)
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO patterns 
                    (pattern_type, pattern_data, confidence)
                    VALUES (?, ?, ?)
                """, (pattern_type, pattern_data, confidence))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding pattern: {str(e)}")
            return None

    def get_pattern(self, pattern_type):
        """Get a pattern by type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pattern_type, pattern_data, confidence, created_at
                    FROM patterns
                    WHERE pattern_type = ?
                """, (pattern_type,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'pattern_type': row[0],
                        'pattern_data': json.loads(row[1]) if row[1] else {},
                        'confidence': row[2],
                        'created_at': row[3]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting pattern {pattern_type}: {str(e)}")
            return None

    def get_patterns(self, pattern_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get patterns from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if pattern_type:
                    cursor.execute('''
                        SELECT pattern_type, pattern_data, confidence, created_at 
                        FROM patterns 
                        WHERE pattern_type = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (pattern_type, limit))
                else:
                    cursor.execute('''
                        SELECT pattern_type, pattern_data, confidence, created_at 
                        FROM patterns 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                patterns = []
                for row in cursor.fetchall():
                    pattern = {
                        'pattern_type': row[0],
                        'pattern_data': json.loads(row[1]),
                        'confidence': row[2],
                        'created_at': row[3]
                    }
                    patterns.append(pattern)
                return patterns
        except Exception as e:
            logger.error(f"Error getting patterns: {str(e)}")
            return []

    def validate_insight(self, insight_id, validated=False, feedback=None):
        """Update the validation status of an insight"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE insights 
                    SET validated = ?, validation_feedback = ?
                    WHERE id = ?
                ''', (1 if validated else 0, feedback, insight_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error validating insight: {str(e)}")
            return False
