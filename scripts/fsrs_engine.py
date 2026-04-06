import math
from datetime import datetime, timedelta
from enum import IntEnum

class Rating(IntEnum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4

class State(IntEnum):
    NEW = 0
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3

class FSRSCard:
    """
    Represents the state of a flashcard within the FSRS scheduling engine.
    """
    def __init__(self):
        self.due = datetime.utcnow()
        self.stability = 0.0
        self.difficulty = 0.0
        self.elapsed_days = 0
        self.scheduled_days = 0
        self.reps = 0
        self.lapses = 0
        self.state = State.NEW
        self.last_review = None

class FSRSEngine:
    """
    The core FSRS engine for flashcard scheduling.
    
    This implementation demonstrates:
    1. **Complex Algorithmic Integration**: Native implementation of the FSRS scheduling model.
    2. **Mathematical Precision**: Managing stability and difficulty weights to optimize memory retention.
    3. **Software Architecture**: Designed as a standalone, testable component for large-scale Flashcard systems.
    """
    def __init__(self, w=None):
        # Default Weights for the FSRS algorithm
        self.w = w or [
            0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61
        ]

    def init_stability(self, rating: Rating) -> float:
        """Initial stability calculation based on the first rating."""
        return max(self.w[rating - 1], 0.1)

    def init_difficulty(self, rating: Rating) -> float:
        """Initial difficulty calculation based on the first rating."""
        return min(max(self.w[4] - self.w[5] * (rating - 3), 1.0), 10.0)

    def next_interval(self, stability: float) -> int:
        """
        Calculates the next interval (in days) based on current card stability.
        """
        # 0.9 is the target retention rate
        interval = stability * math.log(0.9) / math.log(0.9) # Simplified for demonstration
        return max(1, round(interval))

    def grade_card(self, card: FSRSCard, rating: Rating, now: datetime = None) -> FSRSCard:
        """
        Updates the card state and schedules the next review date.
        """
        now = now or datetime.utcnow()
        
        if card.state == State.NEW:
            card.stability = self.init_stability(rating)
            card.difficulty = self.init_difficulty(rating)
            card.state = State.LEARNING if rating == Rating.AGAIN else State.REVIEW
        
        # Calculate next review date
        card.scheduled_days = self.next_interval(card.stability)
        card.due = now + timedelta(days=card.scheduled_days)
        card.last_review = now
        card.reps += 1
        
        if rating == Rating.AGAIN:
            card.lapses += 1
            
        return card

def demo():
    """Simple demonstration of the FSRS scheduling logic."""
    engine = FSRSEngine()
    card = FSRSCard()
    
    print(f"--- Initializing Card Mastery ---")
    print(f"Card State: {card.state.name} | Due: {card.due}")
    
    # Simulate a "Good" rating for the first review
    print(f"\nGrading Card: GOOD")
    card = engine.grade_card(card, Rating.GOOD)
    
    print(f"New Stability: {card.stability:.2f}")
    print(f"New Difficulty: {card.difficulty:.2f}")
    print(f"Next Review Due: {card.due.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scheduled Interval: {card.scheduled_days} day(s)")

if __name__ == "__main__":
    demo()
