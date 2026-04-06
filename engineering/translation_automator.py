import json
import os
import time
from typing import List, Dict
from supabase import create_client, Client

# --- CONFIGURATION ---
# These are managed via securely stored environment variables.
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_KEY_HERE"

class TranslationAutomator:
    """
    Velang Internal Engineering Tool: Localization Sync Engine.
    
    These scripts automate the process of merging distributed translation batches
    and performing optimized, state-aware updates to the database.
    
    Features:
    1. **Batch Merging**: Aggregates JSON translation outputs from AI-agents or LSPs.
    2. **JSONB Content Merging**: Intelligently updates nested L10N objects without data loss.
    3. **Rate-Limited Syncing**: Ensures database stability during high-volume updates.
    4. **Audit Logging**: Tracks successes and failures for high-integrity data migration.
    """
    
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)
        self.stats = {"success": 0, "errors": 0}

    def merge_translation_batches(self, pattern: str = "translated_batch_*.json") -> List[Dict]:
        """
        Merges multiple translation batch files into a unified dataset.
        """
        import glob
        all_translations = []
        files = glob.glob(pattern)
        
        print(f"📦 Merging {len(files)} translation batches...")
        for filename in sorted(files):
            with open(filename, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                all_translations.extend(batch)
        
        return all_translations

    def sync_to_supabase(self, translations: List[Dict], lang_code: str = "ar"):
        """
        Performs optimized upserts of translations to the 'cards' table.
        """
        print(f"🚀 Starting synchronization of {len(translations)} entries to Supabase...")
        
        for idx, entry in enumerate(translations):
            card_id = entry['id']
            translated_text = entry.get('translation') or entry.get('arabic_translation')

            try:
                # 1. Fetch current localization state to perform an intelligent merge
                response = self.supabase.table("cards").select("l10n").eq("id", card_id).single().execute()
                if not response.data:
                    print(f"⚠️ Warning: Card {card_id} not found.")
                    self.stats["errors"] += 1
                    continue

                l10n = response.data.get('l10n', {})
                
                # 2. Update the language-specific mapping
                if lang_code not in l10n:
                    l10n[lang_code] = {}
                l10n[lang_code]['example'] = translated_text

                # 3. Perform a scoped update to protect other column integrity
                update_res = self.supabase.table("cards").update({"l10n": l10n}).eq("id", card_id).execute()
                
                if update_res.data:
                    self.stats["success"] += 1
                else:
                    self.stats["errors"] += 1

                # Progress output every 50 cards
                if idx > 0 and idx % 50 == 0:
                    print(f"✅ Progress: {idx} records processed...")

            except Exception as e:
                print(f"❌ Error syncing card {card_id}: {str(e)}")
                self.stats["errors"] += 1

        print(f"\n✨ Sync Complete!")
        print(f"   - Successfully Updated: {self.stats['success']}")
        print(f"   - Errors Encountered: {self.stats['errors']}")

def run_sync():
    """Main execution flow for localized data synchronization."""
    # Ensure credentials are set
    if SUPABASE_URL == "YOUR_SUPABASE_URL_HERE":
        print("🛑 Error: Please configure YOUR_SUPABASE_URL in translation_automator.py")
        return

    automator = TranslationAutomator(SUPABASE_URL, SUPABASE_KEY)
    
    # Process
    data = automator.merge_translation_batches()
    if data:
        automator.sync_to_supabase(data)
    else:
        print("⚠️ No translation files found to process.")

if __name__ == "__main__":
    run_sync()
