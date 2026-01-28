# L1 Interpreter Specification

**L1 = deterministic rules over Atomic Frames. No ML, no parsing, just interpretation.**

---

## 1. Symbol Registry

```python
SYMBOL_REGISTRY = {
    # Semantic symbols (from vocabulary)
    'eat':              {'kind': 'EVENT',    'retractable': False, 'projectable': True},
    'king':             {'kind': 'STATE',    'retractable': False, 'projectable': True},
    'husband_of':       {'kind': 'RELATION', 'retractable': False, 'projectable': True},
    
    # Identity (the only non-monotonic symbol)
    '≡':                {'kind': 'IDENTITY', 'retractable': True,  'projectable': False},
    
    # Provenance
    'derive':           {'kind': 'TRACE',    'retractable': True,  'projectable': False},
    
    # Temporal (non-inferential)
    'before':           {'kind': 'TEMPORAL', 'retractable': False, 'projectable': False},
    
    # System symbols
    'RETRACT_IDENTITY': {'kind': 'SYSTEM',   'retractable': False, 'projectable': False},
    'trace':            {'kind': 'AUDIT',    'retractable': False, 'projectable': False},
}

def get_kind(symbol: str) -> str:
    """Default to EVENT if symbol not in registry (open vocabulary)"""
    return SYMBOL_REGISTRY.get(symbol, {'kind': 'EVENT'})['kind']

def is_retractable(symbol: str) -> bool:
    return SYMBOL_REGISTRY.get(symbol, {'retractable': False})['retractable']
```

**Invariant**: Only `IDENTITY` and `TRACE` kinds are retractable.

---

## 2. Entity vs Frame Resolution

```python
def resolve_argument(arg: str, frame_store) -> dict:
    """
    Arguments are either entity-refs or frame-refs.
    
    Rule: If it exists as a frame ID → frame-ref
          Else → entity-ref
    """
    if frame_store.exists(arg):
        return {'type': 'frame', 'id': arg}
    else:
        return {'type': 'entity', 'label': arg}
```

**Key insight**: Entities are symbols that only appear as arguments, never as frame IDs. No separate entity table needed.

---

## 3. Context (POV) Definition

```python
@dataclass
class Context:
    """A context is a filter, not a mutation."""
    
    active_sources: list[str] = None      # None = all sources
    min_confidence: float = 0.0
    excluded_identities: set[str] = None  # Identity frame IDs to ignore
    time_window: tuple[str, str] = None   # (start, end) or None = all time
    
    def accepts(self, frame) -> bool:
        """Does this frame pass the context filter?"""
        if not frame.active:
            return False
        if frame.confidence < self.min_confidence:
            return False
        if self.active_sources and frame.source not in self.active_sources:
            return False
        if self.excluded_identities and frame.id in self.excluded_identities:
            return False
        # Time window check if applicable
        return True
```

**Rule**: Context is declared, never implicit. There is no "default POV."

---

## 4. Status Evaluation

```python
def is_active(frame_id: str, context: Context, frame_store) -> bool:
    """
    A frame is ACTIVE in context C iff:
    1. frame.active = TRUE
    2. context.accepts(frame)
    3. All identity frames it depends on are active in C
    """
    frame = frame_store.get(frame_id)
    if not frame or not frame.active:
        return False
    if not context.accepts(frame):
        return False
    
    # Check identity dependencies (for derived frames)
    if get_kind(frame.symbol) == 'TRACE':
        for arg in frame.arguments:
            ref = resolve_argument(arg, frame_store)
            if ref['type'] == 'frame':
                dep_frame = frame_store.get(ref['id'])
                if dep_frame and get_kind(dep_frame.symbol) == 'IDENTITY':
                    if not is_active(ref['id'], context, frame_store):
                        return False
    
    return True
```

---

## 5. Provenance Queries

```python
def get_provenance(frame_id: str, context: Context, frame_store) -> dict:
    """
    Provenance = follow derive frames backwards.
    
    Returns a tree of evidence.
    """
    frame = frame_store.get(frame_id)
    if not frame:
        return None
    
    # Atomic observation: provenance is just source
    if get_kind(frame.symbol) not in ['TRACE']:
        return {
            'frame_id': frame_id,
            'symbol': frame.symbol,
            'source': frame.source,
            'confidence': frame.confidence,
            'type': 'observation'
        }
    
    # Derived: find the derive frame and recurse
    derive_frames = frame_store.query(
        symbol='derive',
        conclusion=frame_id,
        active=True
    )
    
    if not derive_frames:
        return {'frame_id': frame_id, 'type': 'orphan'}
    
    derive = derive_frames[0]
    evidence = []
    for arg in derive.arguments[1:]:  # Skip conclusion
        ref = resolve_argument(arg, frame_store)
        if ref['type'] == 'frame':
            evidence.append(get_provenance(ref['id'], context, frame_store))
        else:
            evidence.append({'entity': ref['label']})
    
    return {
        'frame_id': frame_id,
        'type': 'derived',
        'derive_frame': derive.id,
        'evidence': evidence
    }
```

---

## 6. Invalidation

```python
def invalidate_identity(identity_id: str, reason: str, source: str, frame_store):
    """
    The ONLY write operation that causes semantic change.
    
    Steps:
    1. Mark identity inactive
    2. Assert explicit retraction act
    3. Cascade to dependent derivations
    4. Audit log
    """
    # Step 1: Deactivate
    frame_store.update(identity_id, active=False)
    
    # Step 2: Explicit retraction (first-class, queryable)
    retract_id = generate_id()
    frame_store.insert(
        id=retract_id,
        symbol='RETRACT_IDENTITY',
        arguments=[identity_id],
        source=source,
        confidence=1.0
    )
    
    # Step 3: Cascade - find all derive frames depending on this identity
    dependent_derives = frame_store.query_containing(
        symbol='derive',
        contains_arg=identity_id,
        active=True
    )
    for d in dependent_derives:
        frame_store.update(d.id, active=False)
    
    # Step 4: Audit log
    frame_store.insert(
        id=generate_id(),
        symbol='trace',
        arguments=['RETRACT_IDENTITY', identity_id, reason],
        source='system',
        confidence=1.0
    )
    
    return retract_id
```

---

## 7. Frame Numbering Discipline

**Rules:**

| Rule | Rationale |
|------|-----------|
| IDs are UUIDs | No semantics leakage |
| IDs never reused | Immutability |
| IDs never ordered | No implicit sequence |
| IDs never interpreted | Labels are for humans |

```python
def generate_id() -> str:
    return str(uuid.uuid4())

# Entity labels are NOT IDs
# "ram_p5" is a label, "f_91e2..." is an ID
```

---

## 8. What is Context-Independent vs Context-Dependent

| Thing | Context-dependent? | Why |
|-------|-------------------|-----|
| Atomic frames (observations) | ❌ No | They exist objectively |
| Identity frames | ✅ Yes | Different POVs accept different identities |
| Derived frames | ✅ Yes | Depend on which identities are active |
| Status | ✅ Yes | Filtered by context |
| Explanations | ✅ Yes | Traversal respects active identities |

**Observations are context-independent. Interpretation is context-dependent.**

---

## Summary

L1 is exactly 6 responsibilities:

1. **Symbol typing** → `SYMBOL_REGISTRY`
2. **Entity vs frame resolution** → `resolve_argument()`
3. **Context filtering** → `Context.accepts()`
4. **Provenance traversal** → `get_provenance()`
5. **Status evaluation** → `is_active()`
6. **Invalidation** → `invalidate_identity()`

No ML. No inference. Just rules.

---

## Next: L2 (Not Yet)

L2 will handle:
- Natural language → frame extraction
- Query language syntax
- Question answering

**Do not define L2 until L1 is implemented and tested.**
