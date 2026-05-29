"""Sorting and searching concepts."""

from lecture2graph.plugins.base import DomainPlugin, PrerequisiteRule


PLUGIN = DomainPlugin(
    name="sorting",
    concept_patterns={
        "sorting": [r"\bsort(?:ing)?\b"],
        "searching": [r"\bsearch(?:ing)?\b"],
        "binary search": [r"binary\s+search"],
        "linear search": [r"linear\s+search"],
        "bubble sort": [r"bubble\s+sort"],
        "merge sort": [r"merge\s+sort"],
        "quick sort": [r"quick\s+sort", r"quicksort"],
        "insertion sort": [r"insertion\s+sort"],
        "selection sort": [r"selection\s+sort"],
        "time complexity": [r"time\s+complex", r"\bbig[\s\-]?o\b", r"O\s*\("],
        "space complexity": [r"space\s+complex"],
    },
    prerequisite_rules=[
        PrerequisiteRule("algorithm", "sorting", confidence=0.7, reason="Sorting is taught as a class of algorithms."),
        PrerequisiteRule("algorithm", "searching", confidence=0.7, reason="Searching is taught as a class of algorithms."),
        PrerequisiteRule("sorting", "bubble sort", relation="refines", reason="Bubble sort is one sorting algorithm."),
        PrerequisiteRule("sorting", "merge sort", relation="refines", reason="Merge sort is one sorting algorithm."),
        PrerequisiteRule("sorting", "quick sort", relation="refines", reason="Quick sort is one sorting algorithm."),
        PrerequisiteRule("sorting", "insertion sort", relation="refines", reason="Insertion sort is one sorting algorithm."),
        PrerequisiteRule("sorting", "selection sort", relation="refines", reason="Selection sort is one sorting algorithm."),
        PrerequisiteRule("searching", "binary search", relation="refines", reason="Binary search is one searching technique."),
        PrerequisiteRule("searching", "linear search", relation="refines", reason="Linear search is one searching technique."),
        PrerequisiteRule("array", "sorting", confidence=0.7, reason="Sorting examples are commonly introduced over arrays."),
        PrerequisiteRule("array", "searching", confidence=0.7, reason="Searching examples are commonly introduced over arrays."),
        PrerequisiteRule("recursion", "merge sort", confidence=0.7, reason="Merge sort is often explained recursively."),
        PrerequisiteRule("recursion", "quick sort", confidence=0.7, reason="Quick sort is often explained recursively."),
        PrerequisiteRule("algorithm", "time complexity", confidence=0.7, reason="Complexity analysis builds on algorithmic thinking."),
        PrerequisiteRule("algorithm", "space complexity", confidence=0.7, reason="Complexity analysis builds on algorithmic thinking."),
    ],
    descriptions={
        "sorting": "The process of arranging data items into a defined order.",
        "searching": "The process of finding a target item in a collection.",
        "binary search": "A search algorithm that halves the search space on sorted data.",
        "linear search": "A search algorithm that checks each item in order.",
        "bubble sort": "A sorting algorithm that repeatedly swaps adjacent out-of-order items.",
        "merge sort": "A divide-and-conquer sorting algorithm that merges sorted halves.",
        "quick sort": "A divide-and-conquer sorting algorithm built around partitioning.",
        "insertion sort": "A sorting algorithm that grows a sorted prefix one item at a time.",
        "selection sort": "A sorting algorithm that repeatedly selects the next minimum item.",
        "time complexity": "How running time grows as input size increases.",
        "space complexity": "How memory usage grows as input size increases.",
    },
)

