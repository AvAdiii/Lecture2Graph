# Benchmark: symbolic vs. neural vs. hybrid

## Fair head-to-head

Macro-averaged over the 5 videos where all three methods ran (N2P7w22tN9c, Tp37HXfekNo, XRcC7bAtL3c, azXr6nTaD9M, eXWl-Uor75o).

| method | videos | edge_P | edge_R | edge_F1 | node_F1 | order_acc | GED |
|---|---|---|---|---|---|---|---|
| symbolic | 5 | 0.549 | 0.619 | 0.540 | 0.833 | 0.921 | 11.6 |
| neural | 5 | 0.289 | 0.135 | 0.174 | 0.479 | 0.527 | 17.8 |
| hybrid | 5 | 0.485 | 0.664 | 0.551 | 0.804 | 0.932 | 14.4 |

## All available videos

Symbolic also covers videos the neural pipeline had not yet processed, so this view is not a like-for-like comparison.

| method | videos | edge_P | edge_R | edge_F1 | node_F1 | order_acc | GED |
|---|---|---|---|---|---|---|---|
| symbolic | 5 | 0.549 | 0.619 | 0.540 | 0.833 | 0.921 | 11.6 |
| neural | 5 | 0.289 | 0.135 | 0.174 | 0.479 | 0.527 | 17.8 |
| hybrid | 5 | 0.485 | 0.664 | 0.551 | 0.804 | 0.932 | 14.4 |

- **edge_P/R/F1**, directed prerequisite-edge precision / recall / F1
- **node_F1**, concept-recovery F1
- **order_acc**, fraction of gold 'A before B' pairs ordered correctly
- **GED**, graph edit distance (node + edge symmetric difference; lower is better)
