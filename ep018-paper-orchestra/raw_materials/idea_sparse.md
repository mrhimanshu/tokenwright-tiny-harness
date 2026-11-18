## Problem Statement
Recent "reasoning" benchmarks such as Sudoku-Extreme are used to argue that looped / recurrent neural models learn to reason. Hoover, Blayney and Whittington (arXiv 2611.17309, Nov 2026, "Classical Energies Learn to Reason 1,000x Faster than Looped Models") propose CRAM, a learned version of Hopfield and Tank's 1980s energy model, and report 99.996% on Sudoku-Extreme after 42 ms of training on one H200 GPU. Separately, practitioners now ask frontier LLMs to solve such puzzles directly with long chain-of-thought. It is unclear how these approaches compare on cost, speed and reliability when measured on the same puzzles and the same hardware budget.

## Core Hypothesis
On Sudoku-Extreme, (1) a frontier LLM reasoning "in its head" is slow, expensive and unreliable; (2) the same LLM asked to write a conventional backtracking solver is cheap, fast and essentially perfect; (3) an independent CPU re-implementation of CRAM reproduces near-perfect accuracy with seconds of training, but a hand-set energy with a single weight value does equally well, supporting the original authors' caution that Sudoku is too easy to demonstrate reasoning.

## Proposed Methodology (High-Level)
- This is a replication and comparison study; CRAM is the method of Hoover et al., not ours. We rebuild it from the paper (NumPy pseudolikelihood fit + a C focused Gibbs search) without using the authors' code.
- Three solver families on one fixed sample of 500 Sudoku-Extreme test puzzles: (a) Claude models (Opus 5.5, Sonnet 5.5, Haiku 5.5) answering directly with adaptive thinking; (b) the same models writing a standard-library Python solver in one prompt, which we then run on all 500 puzzles; (c) the CRAM re-implementation with a learned energy (3 seeds) and with a hand-set energy.
- Metrics: puzzles solved, wrong answers, dollars per puzzle, wall-clock time, training time, and whether the learned couplings recover the true Sudoku constraint graph.

## Expected Contribution
An honest, small-budget, single-machine comparison showing that the cheapest reliable option is having an LLM write ordinary code, and an independent replication of CRAM on a CPU.
