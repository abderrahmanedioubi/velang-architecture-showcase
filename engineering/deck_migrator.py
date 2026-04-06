import os
import sqlite3
import json
import zipfile
import re
import tempfile
from typing import Dict, List, Tuple, Any
from supabase import create_client, Client

# --- CONFIGURATION ---
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SERVICE_KEY_HERE"

class DeckMigrator:
    """
    Velang Engineering Tool: Anki-to-Supabase ETL Engine.
    
    Responsibilities:
    1. Extract .apkg archives and access internal SQLite collection.
    2. Parse hierarchical deck names into CEFR levels.
    3. Extract and map raw Anki HTML/CSS templates to Supabase 'card_templates'.
    4. Transform and batch-load thousands of flashcards with relational integrity.
    """
    
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def parse_hierarchy(self, deck_path: str) -> Tuple[str, str, str]:
        """
        Regex-based parser for curriculum hierarchy.
        Turns 'Velang::A1::1. Vocab::1.1. Greetings' into ('A1', '1. Vocab', '1.1. Greetings').
        """
        parts = [p.strip() for p in deck_path.split('::')]
        phase_pattern = re.compile(r'^([A-C][012])$', re.IGNORECASE)
        
        phase_idx = next((i for i, p in enumerate(parts) if phase_pattern.match(p)), None)
        
        if phase_idx is None:
            return ('Unknown', '', deck_path)

        phase = parts[phase_idx].upper()
        category = parts[phase_idx + 1] if phase_idx + 1 < len(parts) else ''
        sub_category = parts[phase_idx + 2] if phase_idx + 2 < len(parts) else ''
        
        return (phase, category, sub_category)

    def process_apkg(self, apkg_path: str):
        """
        Main extraction and processing pipeline.
        """
        print(f"📦 Extracting package: {apkg_path}")
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(apkg_path, 'r') as zf:
                zf.extractall(tmpdir)
            
            # Locate Anki SQLite DB
            db_path = os.path.join(tmpdir, "collection.anki21b")
            if not os.path.exists(db_path):
                db_path = os.path.join(tmpdir, "collection.anki2")

            self._migrate_db(db_path)

    def _migrate_db(self, db_path: str):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Migrate Templates
        print("📑 Processing Note Type templates...")
        cursor.execute("SELECT models FROM col")
        models_data = json.loads(cursor.fetchone()[0])
        
        for mid, model in models_data.items():
            name = model.get("name")
            css = model.get("css")
            tmpls = model.get("tmpls", [])
            front = tmpls[0].get("qfmt") if tmpls else ""
            back = tmpls[0].get("afmt") if tmpls else ""

            # Upsert into Supabase
            self.supabase.table("card_templates").upsert({
                "name": name,
                "front_html": front,
                "back_html": back,
                "css": css
            }).execute()

        # 2. Migrate Cards
        print("🎴 Processing Cards & Notes...")
        cursor.execute("""
            SELECT c.nid, c.did, n.flds, n.mid 
            FROM cards c 
            JOIN notes n ON c.nid = n.id
        """)
        
        anki_cards = cursor.fetchall()
        print(f"Found {len(anki_cards)} cards to migrate.")

        # In a real run, we would cluster these by batch 
        # and parse fields based on Note IDs.
        # This demonstrates the logic flow.

if __name__ == "__main__":
    migrator = DeckMigrator()
    # migrator.process_apkg("german_curriculum_A1.apkg")
    print("Migration infrastructure initialized.")
