import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fsrs/fsrs.dart';
import '../models/flashcard.dart';

/// Represents the state of an active study session.
class StudySessionState {
  final List<Flashcard> deck;
  final int initialCardCount;
  final Set<String> completedIds;
  final int gradedCount;

  StudySessionState({
    required this.deck,
    required this.initialCardCount,
    this.completedIds = const {},
    this.gradedCount = 0,
  });

  StudySessionState copyWith({
    List<Flashcard>? deck,
    int? initialCardCount,
    Set<String>? completedIds,
    int? gradedCount,
  }) {
    return StudySessionState(
      deck: deck ?? this.deck,
      initialCardCount: initialCardCount ?? this.initialCardCount,
      completedIds: completedIds ?? this.completedIds,
      gradedCount: gradedCount ?? this.gradedCount,
    );
  }
}

/// The core controller for the Velang study experience.
/// 
/// This class demonstrates:
/// 1. **Robust State Management**: Utilizing Riverpod for predictable, reactive UI updates.
/// 2. **Algorithmic Integration**: Native implementation of the FSRS (Free Spaced Repetition Scheduler).
/// 3. **Smart Re-insertion**: Dynamic queue management for immediate reinforcement (spaced repetition).
/// 4. **Optimistic Persistence**: Handling complex backend sync without blocking the user flow.
class StudySessionNotifier extends Notifier<StudySessionState?> {
  
  @override
  StudySessionState? build() => null;

  /// Initializes the session with a fresh deck of cards.
  void initialize(List<Flashcard> cards) {
    state = StudySessionState(
      deck: List<Flashcard>.from(cards),
      initialCardCount: cards.length,
    );
  }

  /// Handles the grading of a card, updating its FSRS state and the session queue.
  void gradeCurrentCard(Rating rating, int elapsedMs) {
    if (state == null || state!.deck.isEmpty) return;

    final deck = List<Flashcard>.from(state!.deck);
    final currentCard = deck.removeAt(0); // Optimistically advance UI
    final now = DateTime.now().toUtc();

    // 1. Calculate new FSRS state
    // We utilize the open-source FSRS algorithm to calculate precision intervals.
    final scheduler = Scheduler();
    final result = scheduler.reviewCard(
      currentCard.fsrsCard, 
      rating, 
      reviewDateTime: now,
    );

    // 2. Update card metadata
    currentCard.fsrsCard = result.card;
    currentCard.reps++;
    
    // 3. Smart Queue Management
    final updatedCompletedIds = Set<String>.from(state!.completedIds);

    if (rating == Rating.again) {
      // "Again" rating: Reinforce immediately by re-inserting into the current queue.
      // Card remains in the 'Learning' phase for this session.
      final int reinsertPos = deck.length > 5 ? 5 : deck.length;
      deck.insert(reinsertPos, currentCard);
      debugPrint('🔁 Reinforcement: Card ${currentCard.id} re-inserted at index $reinsertPos');
    } else {
      // Success: Card is graduated and scheduled for a future date.
      updatedCompletedIds.add(currentCard.id);
      debugPrint('✅ Mastery: Card ${currentCard.id} scheduled for ${result.card.due}');
    }

    // 4. Update the Session State
    state = state!.copyWith(
      deck: deck,
      completedIds: updatedCompletedIds,
      gradedCount: state!.gradedCount + 1,
    );

    // 5. Asynchronous Persistence
    // In production, this enqueues an offline-first sync to the Supabase backend.
    _persistProgress(currentCard, result.card, rating, elapsedMs);
  }

  Future<void> _persistProgress(Flashcard card, Card fsrsResult, Rating rating, int timeMs) async {
    // Implementation of the persistence layer would follow here,
    // handling payload generation and network reliability.
  }
}

final studySessionProvider = NotifierProvider.autoDispose<StudySessionNotifier, StudySessionState?>(
  StudySessionNotifier.new,
);
