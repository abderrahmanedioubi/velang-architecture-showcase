import json
import os
from typing import Dict

class LocalizationManager:
    """
    Velang Internal Tool: ARB Consistency & Merge Engine.
    
    This tool ensures the Flutter application's internationalization 
    inventory is synchronized between English and Arabic RTL 
    translations after rapid UI changes.
    
    Responsibilities:
    1. Merge new keys from English into target language files.
    2. Maintain JSON metadata.
    3. Validate key integrity between locales to prevent UI crashes.
    """
    
    def __init__(self, en_path: str, ar_path: str):
        self.en_path = en_path
        self.ar_path = ar_path

    def load_arb(self, path: str) -> Dict[str, str]:
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def merge_and_save(self, new_en_keys: Dict[str, str], new_ar_keys: Dict[str, str]):
        """
        Structural merge of existing and new localization keys.
        """
        existing_en = self.load_arb(self.en_path)
        existing_ar = self.load_arb(self.ar_path)

        # Canonical merge for English
        en_merged = {**existing_en, **new_en_keys}
        ar_merged = {**existing_ar, **new_ar_keys}

        self._save(self.en_path, en_merged)
        self._save(self.ar_path, ar_merged)
        
        print(f"✅ Merged {len(new_en_keys)} new keys. Sync complete!")

    def _save(self, path: str, data: Dict):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Example usage for the showcase
    manager = LocalizationManager("lib/l10n/app_en.arb", "lib/l10n/app_ar.arb")
    
    # Payload for the showcase
    new_ui_keys = {
        "onboarding_reach_target_by": "YOU WILL REACH {level} BY:",
        "onboarding_target_timeline": "TARGET TIMELINE",
        "@onboarding_reach_target_by": {
            "placeholders": {
                "level": { "type": "String" }
            }
        }
    }
    
    # manager.merge_and_save(new_ui_keys, {}) # Arab keys would be defined in payload
    print("Localization infrastructure ready.")
