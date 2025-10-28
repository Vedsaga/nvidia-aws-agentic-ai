"""
Kāraka Mapper - Maps SRL roles to Pāṇinian Kāraka semantic roles
"""

from typing import Dict

# Mapping from spaCy SRL dependency labels to Kāraka types
SRL_TO_KARAKA = {
    'nsubj': 'KARTA',           # Subject → Agent (who performs)
    'obj': 'KARMA',             # Direct object → Patient (what is acted upon)
    'iobj': 'SAMPRADANA',       # Indirect object → Recipient (for whom/to whom)
    'obl:with': 'KARANA',       # Instrumental → Instrument (by what means)
    'obl:loc': 'ADHIKARANA',    # Locative → Location (where)
    'obl:from': 'APADANA'       # Source → Source (from where/from whom)
}


class KarakaMapper:
    """Maps semantic role labels to Kāraka types"""
    
    def __init__(self):
        self.mapping = SRL_TO_KARAKA
    
    def map_to_karakas(self, srl_roles: Dict[str, str]) -> Dict[str, str]:
        """
        Convert SRL roles to Kāraka roles
        
        Args:
            srl_roles: Dictionary mapping SRL role labels to entity mentions
                      Example: {"nsubj": "Rama", "obj": "bow", "iobj": "Lakshmana"}
        
        Returns:
            Dictionary mapping Kāraka types to entity mentions
            Example: {"KARTA": "Rama", "KARMA": "bow", "SAMPRADANA": "Lakshmana"}
        """
        karaka_roles = {}
        
        for srl_role, entity in srl_roles.items():
            # Map SRL role to Kāraka type
            karaka_type = self.mapping.get(srl_role)
            
            if karaka_type:
                karaka_roles[karaka_type] = entity
        
        return karaka_roles
