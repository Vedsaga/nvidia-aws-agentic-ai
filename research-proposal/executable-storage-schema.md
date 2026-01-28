# Executable Storage Schema: The Atomic Frame

**One table. One type. Everything else is interpretation.**

---

## The Insight

Your theory already defined the storage schema in **Definition 4 (Atomic Frame)**:

```
F = ⟨symbol, arguments[], time_ref, confidence, source⟩
```

That's L0. Everything else — Kriyā, STATE, Kāraka, identity, projection — is **L1 interpretation** over this substrate.

---

## The Schema (Complete)

```sql
CREATE TABLE frame (
    id          TEXT PRIMARY KEY,
    symbol      TEXT NOT NULL,           -- open vocabulary (constrained at L1)
    arguments   TEXT NOT NULL,           -- JSON array of entity/frame refs
    time_ref    TEXT,                    -- temporal anchor or NULL
    confidence  REAL DEFAULT 1.0,
    source      TEXT NOT NULL,
    active      BOOLEAN DEFAULT TRUE,    -- FALSE = retracted
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_frame_symbol ON frame(symbol);
CREATE INDEX idx_frame_active ON frame(active) WHERE active = TRUE;
```

**That's it. One table.**

---

## Symbol Classification (L1 Interpretation)

The **symbol** field determines the semantic type:

| Symbol | Type | Arguments Pattern |
|--------|------|-------------------|
| Any verb/action | Kriyā frame | `[agent?, patient?, instrument?, ...]` |
| Any property | State frame | `[subject, property_value?]` |
| `≡` | Identity hypothesis | `[entity_a, entity_b]` |
| `derive` | Meta-trace (Φ₅) | `[conclusion, evidence_1, evidence_2, ...]` |
| `before` | Temporal relation | `[earlier_frame, later_frame]` |

### Reserved System Symbols (L1 Constraint)

| Symbol | Purpose | Arguments |
|--------|---------|----------|
| `RETRACT_IDENTITY` | First-class retraction act | `[identity_frame_id]` |
| `trace` | Audit log (non-semantic) | `[operation, target_id, ...]` |

**L1 code** (not storage) enforces:
- Finite vocabulary constraints
- Kāraka position semantics
- What can be retracted
- `before` cannot participate in derivation (traversal only)
- `trace` frames are non-semantic audit logs

---

## The Three Operations

### 1. Assert a Frame

```sql
INSERT INTO frame (id, symbol, arguments, time_ref, confidence, source)
VALUES ('f_001', 'eat', '["ram_42", "food_1"]', 't1', 0.95, 'doc_a');
```

### 2. Assert Identity (Still Just a Frame)

```sql
INSERT INTO frame (id, symbol, arguments, confidence, source)
VALUES ('id_001', '≡', '["ram_42", "ram_73"]', 0.75, 'inference_engine');
```

### 3. Retract Identity (The Only Invalidation)

```sql
-- 1. Mark identity inactive
UPDATE frame SET active = FALSE WHERE id = 'id_001';

-- 2. Assert explicit retraction act (first-class, queryable)
INSERT INTO frame (id, symbol, arguments, source)
VALUES ('rid_001', 'RETRACT_IDENTITY', '["id_001"]', 'user_correction');

-- 3. Invalidate dependent derivations
UPDATE frame SET active = FALSE
WHERE symbol = 'derive'
  AND EXISTS (SELECT 1 FROM json_each(arguments) WHERE value = 'id_001');

-- 4. Audit log (optional, non-semantic)
INSERT INTO frame (id, symbol, arguments, source)
VALUES ('tr_001', 'trace', '["RETRACT_IDENTITY", "id_001"]', 'system');
```

---

## Projection (Computed, Not Stored)

Equivalence classes from active identity frames:

```sql
CREATE VIEW equivalence AS
WITH RECURSIVE equiv(entity, class_root) AS (
    -- Every entity mentioned in any frame starts as its own root
    SELECT DISTINCT value, value
    FROM frame, json_each(frame.arguments)
    WHERE frame.active = TRUE
    
    UNION
    
    -- Propagate through active identity frames
    SELECT 
        CASE WHEN e.entity = json_extract(f.arguments, '$[0]')
             THEN json_extract(f.arguments, '$[1]')
             ELSE json_extract(f.arguments, '$[0]')
        END,
        e.class_root
    FROM equiv e
    JOIN frame f ON f.symbol = '≡' AND f.active = TRUE
                 AND (e.entity = json_extract(f.arguments, '$[0]')
                   OR e.entity = json_extract(f.arguments, '$[1]'))
)
SELECT entity, MIN(class_root) AS canonical FROM equiv GROUP BY entity;
```

---

## Cascade Invalidation

```sql
-- Find all derive frames that depend on a retracted identity
SELECT f.*
FROM frame f
WHERE f.symbol = 'derive'
  AND f.active = TRUE
  AND EXISTS (
    SELECT 1 FROM json_each(f.arguments) 
    WHERE value = 'id_001'  -- the retracted identity
  );

-- Mark them inactive too
UPDATE frame SET active = FALSE
WHERE symbol = 'derive'
  AND id IN (...);  -- from above query
```

---

## Why This Works

| Question | Answer |
|----------|--------|
| What is allowed to exist? | Constrain `symbol` vocabulary at L1 |
| What is allowed to change? | Only `active` flag on identity frames |
| What is a valid explanation? | Chase `derive` frames back to sources |
| Is this arbitrary? | No — it's Definition 4 made executable |

---

## 10-Frame Toy Example

```sql
-- Observations (immutable)
INSERT INTO frame VALUES ('f1', 'eat', '["ram_p5"]', 't1', 0.95, 'page_5', TRUE, NOW());
INSERT INTO frame VALUES ('f2', 'king', '["ram_p50"]', 't2', 0.90, 'page_50', TRUE, NOW());

-- Identity hypothesis (retractable)
INSERT INTO frame VALUES ('id1', '≡', '["ram_p5", "ram_p50"]', NULL, 0.75, 'inference', TRUE, NOW());

-- Projection trace
INSERT INTO frame VALUES ('d1', 'derive', '["proj_king_eats", "f1", "f2", "id1"]', NULL, 0.68, 'system', TRUE, NOW());

-- USER CORRECTION: "They're different people"
-- Step 1: Deactivate
UPDATE frame SET active = FALSE WHERE id = 'id1';

-- Step 2: Explicit retraction act
INSERT INTO frame VALUES ('rid1', 'RETRACT_IDENTITY', '["id1"]', NULL, 1.0, 'user', TRUE, NOW());

-- Step 3: Cascade invalidation
UPDATE frame SET active = FALSE WHERE id = 'd1';

-- Step 4: Audit log
INSERT INTO frame VALUES ('tr1', 'trace', '["RETRACT_IDENTITY", "id1"]', NULL, 1.0, 'system', TRUE, NOW());

-- Query: active frames
SELECT * FROM frame WHERE active = TRUE;
-- Returns: f1, f2, rid1, tr1
-- Does NOT return: id1, d1
```

---

## Summary

```
L0: ONE table (frame)
L1: symbol vocabulary + interpretation rules
L2: projection = function over L0
L3: research narrative

Storage is stupid. Interpretation is smart.
```

All elegance lives above the concrete.
