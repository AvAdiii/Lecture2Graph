# Ablation: does OCR (the board) help the symbolic pipeline?

Same 5 lectures, same gold graphs, same symbolic pipeline, the only difference is whether handwritten-board OCR is fed in alongside speech.

| input | videos | edge_P | edge_R | edge_F1 | node_F1 | order_acc | GED |
|---|---|---|---|---|---|---|---|
| speech only (no OCR) | 5 | 0.503 | 0.554 | 0.482 | 0.808 | 0.899 | 13.2 |
| speech + OCR (default) | 5 | 0.549 | 0.619 | 0.54 | 0.833 | 0.921 | 11.6 |

Per-video edge_F1:

| video | speech only | speech + OCR |
|---|---|---|
| N2P7w22tN9c | 0.538 | 0.609 |
| Tp37HXfekNo | 0.909 | 0.909 |
| XRcC7bAtL3c | 0.512 | 0.571 |
| azXr6nTaD9M | 0.167 | 0.167 |
| eXWl-Uor75o | 0.286 | 0.444 |
