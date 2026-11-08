# pyssms

Continuous surrogate safety indicators for road-user encounters: TTC, Time Advantage, T2 and Time Gap for arbitrary approach angles, computed exactly on a time-time conflict polygon.

## Install

```
pip install pyssms
```

## Five-minute tour

```python
import numpy as np
from pyssms import indicators_rect

k = indicators_rect(-20, 0, 0, 10, 0, 4.5, 1.8,  0, -30, np.pi / 2, 0, 10, 4.5, 1.8)
k.state, k.tadv, k.t2   # crossing course (B), 0.37 s, 2.685 s
```

## Pages

* [Validation](validation.md): what reproduces and what does not.
* [Data notes](data_notes.md): the pitfalls found while building the package.
* [NGSIM](ngsim_notes.md): source, licence (modified CC BY 2.0, not public domain), reader decisions, checks, the shipped conflict bank, and what the hierarchy counts depend on.
