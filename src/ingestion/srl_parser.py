"""
SRL Parser using spaCy for semantic role extraction.

This module extracts semantic roles from sentences using dependency parsing.
It handles multiple verbs per line and extracts full noun phrases with modifiers.
"""

from typing import List, Tuple, Dict
import spacy
from spacy.tokens import Token


class SRLParser:
    """
    Semantic Role Labeling parser using spaCy dependency parsing.
    
    Extracts semantic roles (nsubj, obj, iobj, obl) for all verbs in a line.
    """
    
    def __init__(self):
        """Initialize spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm"
            )
    
    def parse_line(self, line: str) -> List[Tuple[str, Dict[str, str]]]:
        """
        Parse a line and extract semantic roles for all verbs.
        
        Args:
            line: Input text line
            
        Returns:
            List of (verb, {role: entity}) tuples for each verb in the line
            Example: [("called", {"nsubj": "she", "obj": "team"}), 
                     ("scheduled", {"nsubj": "she", "obj": "meeting"})]
        """
        if not line or not line.strip():
            return []
        
        doc = self.nlp(line)
        verbs = self._extract_all_verbs(doc)
        
        results = []
        for verb in verbs:
            roles = self._extract_semantic_roles(doc, verb)
            if roles:  # Only include verbs that have at least one role
                results.append((verb.text, roles))
        
        return results
    
    def _extract_all_verbs(self, doc) -> List[Token]:
        """
        Extract all verbs from the dependency tree.
        
        Args:
            doc: spaCy Doc object
            
        Returns:
            List of verb tokens
        """
        verbs = []
        for token in doc:
            # Include main verbs and auxiliary verbs that act as main predicates
            if token.pos_ == "VERB" and token.dep_ not in ["aux", "auxpass"]:
                verbs.append(token)
        
        return verbs
    
    def _extract_semantic_roles(self, doc, verb: Token) -> Dict[str, str]:
        """
        Extract semantic roles for a specific verb.
        
        Extracts:
        - nsubj: nominal subject (agent)
        - obj: direct object (patient)
        - iobj: indirect object (recipient)
        - obl: oblique nominal (with preposition variants like obl:with, obl:loc, obl:from)
        
        Args:
            doc: spaCy Doc object
            verb: Verb token to extract roles for
            
        Returns:
            Dictionary mapping role labels to entity strings
        """
        roles = {}
        
        # Iterate through all tokens to find dependents of this verb
        for token in doc:
            if token.head == verb:
                role = token.dep_
                
                # Handle core semantic roles
                if role in ["nsubj", "nsubjpass"]:
                    # Nominal subject (agent)
                    entity = self._get_noun_phrase(token)
                    roles["nsubj"] = entity
                
                elif role == "obj" or role == "dobj":
                    # Direct object (patient)
                    entity = self._get_noun_phrase(token)
                    roles["obj"] = entity
                
                elif role == "iobj":
                    # Indirect object (recipient)
                    entity = self._get_noun_phrase(token)
                    roles["iobj"] = entity
                
                elif role.startswith("obl"):
                    # Oblique nominals with preposition information
                    entity = self._get_noun_phrase(token)
                    
                    # Try to get preposition for more specific role
                    prep = self._get_preposition(token)
                    if prep:
                        role_key = f"obl:{prep}"
                        roles[role_key] = entity
                    else:
                        roles["obl"] = entity
                
                elif role == "pobj":
                    # Prepositional object - get the preposition
                    if token.head.pos_ == "ADP":
                        prep = token.head.text.lower()
                        entity = self._get_noun_phrase(token)
                        role_key = f"obl:{prep}"
                        roles[role_key] = entity
        
        return roles
    
    def _get_noun_phrase(self, token: Token) -> str:
        """
        Extract full noun phrase including modifiers.
        
        Includes:
        - Determiners (the, a, an)
        - Adjectives (mighty, brave)
        - Compounds (bow and arrow)
        - Possessives (his, Rama's)
        
        Args:
            token: Head noun token
            
        Returns:
            Full noun phrase as string
        """
        # Start with the head noun
        phrase_tokens = [token]
        
        # Collect left modifiers (determiners, adjectives, compounds, etc.)
        for child in token.lefts:
            if child.dep_ in ["det", "amod", "compound", "poss", "nummod", "nmod"]:
                phrase_tokens.insert(0, child)
                # Recursively get modifiers of modifiers
                phrase_tokens = self._collect_subtree(child, phrase_tokens)
        
        # Collect right modifiers (prepositional phrases, relative clauses)
        for child in token.rights:
            if child.dep_ in ["prep", "relcl", "acl"]:
                phrase_tokens.append(child)
                phrase_tokens = self._collect_subtree(child, phrase_tokens)
        
        # Sort by position in sentence and join
        phrase_tokens.sort(key=lambda t: t.i)
        phrase = " ".join([t.text for t in phrase_tokens])
        
        return phrase
    
    def _collect_subtree(self, token: Token, collected: List[Token]) -> List[Token]:
        """
        Recursively collect subtree tokens for compound phrases.
        
        Args:
            token: Current token
            collected: List of already collected tokens
            
        Returns:
            Updated list of tokens
        """
        for child in token.children:
            if child not in collected:
                collected.append(child)
                collected = self._collect_subtree(child, collected)
        
        return collected
    
    def _get_preposition(self, token: Token) -> str:
        """
        Get the preposition associated with an oblique nominal.
        
        Args:
            token: Oblique nominal token
            
        Returns:
            Preposition string (lowercase) or empty string
        """
        # Check if there's a preposition child
        for child in token.children:
            if child.pos_ == "ADP":
                return child.text.lower()
        
        # Check if the head is a preposition
        if token.head.pos_ == "ADP":
            return token.head.text.lower()
        
        return ""
