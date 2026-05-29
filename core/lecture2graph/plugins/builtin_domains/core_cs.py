"""General CS concepts shared across multiple lectures."""

from lecture2graph.plugins.base import DomainPlugin, PrerequisiteRule


PLUGIN = DomainPlugin(
    name="core_cs",
    concept_patterns={
        "recursion": [r"\brecurs(?:ion|ive)\b"],
        "array": [r"\barray\b", r"\barrays\b"],
        "linked list": [r"linked\s+list"],
        "pointer": [r"\bpointer\b", r"\bpointers\b"],
        "hash table": [r"hash\s+(?:table|map|function)", r"\bhashing\b"],
        "algorithm": [r"\balgorithm\b", r"\balgorithms\b"],
        "data structure": [r"data\s+structure"],
    },
    prerequisite_rules=[
        PrerequisiteRule("data structure", "array", relation="refines", confidence=0.8, reason="Arrays are a specific data structure."),
        PrerequisiteRule("data structure", "linked list", relation="refines", confidence=0.8, reason="Linked lists are a specific data structure."),
        PrerequisiteRule("data structure", "stack", relation="refines", confidence=0.8, reason="Stacks are a specific data structure."),
        PrerequisiteRule("data structure", "queue", relation="refines", confidence=0.8, reason="Queues are a specific data structure."),
        PrerequisiteRule("data structure", "hash table", relation="refines", confidence=0.8, reason="Hash tables are a specific data structure."),
        PrerequisiteRule("data structure", "tree", relation="refines", confidence=0.8, reason="Trees are a specific data structure."),
        PrerequisiteRule("data structure", "graph", relation="refines", confidence=0.8, reason="Graphs are a specific data structure."),
        PrerequisiteRule("pointer", "linked list", confidence=0.7, reason="Linked lists are usually explained with pointers or references."),
        PrerequisiteRule("array", "hash table", confidence=0.6, reason="Hash table implementations often begin from array-based storage."),
    ],
    fragment_aliases={
        "recursion": "recursion",
        "array": "array",
        "linked list": "linked list",
        "pointer": "pointer",
        "hash table": "hash table",
        "hashing": "hash table",
        "algorithm": "algorithm",
        "data structure": "data structure",
    },
    descriptions={
        "recursion": "A problem-solving approach where a function calls itself on smaller subproblems.",
        "array": "A contiguous collection of elements accessed by index.",
        "linked list": "A sequence of nodes linked together through references.",
        "pointer": "A reference to another location or object in memory.",
        "hash table": "A key-value data structure built around hashing.",
        "algorithm": "A step-by-step procedure for solving a computational problem.",
        "data structure": "A way of organizing data so operations are efficient and understandable.",
    },
)

