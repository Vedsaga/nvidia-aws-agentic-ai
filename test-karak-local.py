#!/usr/bin/env python3
"""Test Karaka extraction locally"""
import json

# Simulate entity extraction
sentence = "Rama gives book to Sita in library."
entities = ["Rama", "book", "Sita", "library"]
verb = "give"

print(f"Sentence: {sentence}")
print(f"Entities: {entities}")
print(f"Verb: {verb}")
print()

# Expected Karaka output
expected_karakas = [
    {"role": "Agent", "entity": "Rama"},
    {"role": "Object", "entity": "book"},
    {"role": "Recipient", "entity": "Sita"},
    {"role": "Location", "entity": "library"}
]

print("Expected Karaka relationships:")
for k in expected_karakas:
    print(f"  {k['role']}: {k['entity']}")
print()

# Show prompt that would be sent
prompt_template = open('prompts/karak_prompt.txt').read()
prompt = prompt_template.replace('{SENTENCE_HERE}', sentence)
prompt = prompt.replace('{ENTITIES}', json.dumps(entities))
prompt = prompt.replace('{VERB}', verb)

print("=" * 60)
print("PROMPT TO LLM:")
print("=" * 60)
print(prompt)
