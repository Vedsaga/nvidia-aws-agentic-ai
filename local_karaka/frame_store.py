"""
Frame Store for Kāraka Frame Graph POC.
In-memory storage with JSON persistence.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict
from frame_extractor import Frame


class FrameStore:
    """
    Simple in-memory frame store with optional JSON persistence.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize the frame store.
        
        Args:
            persist_path: Optional path to JSON file for persistence
        """
        self.frames: dict[str, Frame] = {}
        self.entities: dict[str, set[str]] = {}  # entity -> frame_ids
        self.kriyas: dict[str, set[str]] = {}    # kriya -> frame_ids
        self.persist_path = Path(persist_path) if persist_path else None
        
        # Load existing data if persist file exists
        if self.persist_path and self.persist_path.exists():
            self._load()
    
    def add_frame(self, frame: Frame) -> None:
        """Add a frame to the store."""
        self.frames[frame.frame_id] = frame
        
        # Index by kriya (lowercase for consistent matching)
        kriya_key = frame.kriya.lower().strip()
        if kriya_key not in self.kriyas:
            self.kriyas[kriya_key] = set()
        self.kriyas[kriya_key].add(frame.frame_id)
        
        # Index by entities (all kāraka role fillers)
        for entity in self._get_entities(frame):
            normalized = entity.lower().strip()
            if normalized not in self.entities:
                self.entities[normalized] = set()
            self.entities[normalized].add(frame.frame_id)
        
        # Auto-persist
        if self.persist_path:
            self._save()
    
    def add_frames(self, frames: list[Frame]) -> None:
        """Add multiple frames."""
        for frame in frames:
            self.add_frame(frame)
    
    def get_frame(self, frame_id: str) -> Optional[Frame]:
        """Get a frame by ID."""
        return self.frames.get(frame_id)
    
    def get_all_frames(self) -> list[Frame]:
        """Get all frames."""
        return list(self.frames.values())
    
    def find_by_entity(self, entity: str) -> list[Frame]:
        """Find all frames mentioning an entity."""
        normalized = entity.lower().strip()
        frame_ids = self.entities.get(normalized, set())
        return [self.frames[fid] for fid in frame_ids if fid in self.frames]
    
    def find_by_kriya(self, kriya: str) -> list[Frame]:
        """Find all frames with a specific kriya."""
        normalized = kriya.lower().strip()
        frame_ids = self.kriyas.get(normalized, set())
        return [self.frames[fid] for fid in frame_ids if fid in self.frames]
    
    def find_by_role(self, role: str, value: str) -> list[Frame]:
        """Find frames where a specific role has a specific value."""
        results = []
        role_lower = role.lower()
        value_lower = value.lower()
        
        role_attr_map = {
            "karta": "karta", "kartā": "karta", "agent": "karta",
            "karma": "karma", "object": "karma",
            "karana": "karana", "karaṇa": "karana", "instrument": "karana",
            "sampradana": "sampradana", "sampradāna": "sampradana", "recipient": "sampradana",
            "apadana": "apadana", "apādāna": "apadana", "source": "apadana",
            "time": "locus_time", "locus_time": "locus_time",
            "space": "locus_space", "locus_space": "locus_space", "place": "locus_space",
            "topic": "locus_topic", "locus_topic": "locus_topic",
        }
        
        attr = role_attr_map.get(role_lower)
        if not attr:
            return results
        
        for frame in self.frames.values():
            frame_value = getattr(frame, attr, None)
            if frame_value and value_lower in frame_value.lower():
                results.append(frame)
        
        return results
    
    def clear(self) -> None:
        """Clear all frames."""
        self.frames.clear()
        self.entities.clear()
        self.kriyas.clear()
        
        if self.persist_path:
            self._save()
    
    def get_stats(self) -> dict:
        """Get statistics about the store."""
        return {
            "total_frames": len(self.frames),
            "unique_entities": len(self.entities),
            "unique_kriyas": len(self.kriyas),
            "kriyas": list(self.kriyas.keys()),
        }
    
    def to_json(self) -> str:
        """Export all frames as JSON."""
        return json.dumps(
            [f.to_dict() for f in self.frames.values()],
            indent=2
        )
    
    def to_graph_data(self) -> dict:
        """
        Export as graph visualization data.
        Returns nodes and edges for visualization.
        """
        nodes = []
        edges = []
        entity_ids = {}
        
        # Create entity nodes
        for entity in self.entities.keys():
            entity_id = f"E_{len(entity_ids)}"
            entity_ids[entity] = entity_id
            nodes.append({
                "id": entity_id,
                "label": entity.title(),
                "type": "entity"
            })
        
        # Create event nodes and edges
        for frame in self.frames.values():
            event_id = frame.frame_id
            nodes.append({
                "id": event_id,
                "label": frame.kriya.upper(),
                "type": "event"
            })
            
            # Create edges from entities to events
            role_map = {
                "Kartā": frame.karta,
                "Karma": frame.karma,
                "Karaṇa": frame.karana,
                "Sampradāna": frame.sampradana,
                "Apādāna": frame.apadana,
                "Time": frame.locus_time,
                "Space": frame.locus_space,
                "Topic": frame.locus_topic,
            }
            
            for role, value in role_map.items():
                if value:
                    entity_key = value.lower().strip()
                    if entity_key in entity_ids:
                        edges.append({
                            "source": entity_ids[entity_key],
                            "target": event_id,
                            "label": role
                        })
        
        return {"nodes": nodes, "edges": edges}
    
    def _get_entities(self, frame: Frame) -> list[str]:
        """Extract all entity mentions from a frame."""
        entities = []
        for value in [frame.karta, frame.karma, frame.karana, 
                     frame.sampradana, frame.apadana,
                     frame.locus_time, frame.locus_space, frame.locus_topic]:
            if value:
                entities.append(value)
        return entities
    
    def _save(self) -> None:
        """Persist frames to JSON file."""
        if self.persist_path:
            self.persist_path.write_text(self.to_json())
    
    def _load(self) -> None:
        """Load frames from JSON file."""
        if self.persist_path and self.persist_path.exists():
            try:
                data = json.loads(self.persist_path.read_text())
                for item in data:
                    frame = Frame(**item)
                    self.add_frame(frame)
            except Exception as e:
                print(f"⚠️ Failed to load frames: {e}")


# Global store instance
_store: Optional[FrameStore] = None

def get_store(persist_path: str = "frames.json") -> FrameStore:
    """Get or create the global frame store."""
    global _store
    if _store is None:
        _store = FrameStore(persist_path)
    return _store
