# Subset Sum Program Variants

Checked-in `.man` files are immutable candidates. New algorithms or geometry
optimizations get a new `subset_sum_NN.man` file and a corresponding
`variants.json` entry; older candidates are never overwritten.

`subset_sum_00.man` is the first accepted meet-in-the-middle implementation.
It enumerates the two ten-value halves independently, sorts both 1,024-entry
streams in opposite sum order, merges them against the target, and retains the
lexicographically first matching mask. The artifact is tracked with Git LFS
because its generated ASCII source is close to the contest's 10 MB limit.
