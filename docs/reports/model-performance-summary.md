# Model Performance Summary

Generated for the World Cup Oracle portfolio checkpoint.

## Purpose

This report summarizes how the model is evaluated and what the current operational run shows. It is intentionally short: the full machine-readable artifacts live in `data/processed/`, while this document explains the model-performance story for reviewers.

## Evaluation Setup

The current validation report evaluates completed group-stage match predictions. Knockout games are tracked separately in the performance-audit layer because advancement can involve extra time and penalties, while the score model keeps penalty shootouts out of goals.

Current checkpoint:

```text
Generated on: 2026-07-12
Operational completed matches: 100
Group-stage validation matches: 72
Knockout matches audited: 28
Current live teams: 4
```

## Metrics

```text
Brier Score: 0.5097
Log Loss: 0.8749
Expected Calibration Error: 0.1423
Score log-likelihood: -2.8853
Score negative log-likelihood: 2.8853
```

Metric meaning:

- Brier Score checks probability accuracy across win/draw/loss outcomes.
- Log Loss penalizes confident wrong predictions.
- Expected Calibration Error checks whether predicted probabilities line up with observed frequencies.
- Score likelihood evaluates whether the Poisson score model assigns reasonable probability to observed scorelines.

## Current Tournament Model State

After the quarter-finals, the live bracket is:

```text
France vs Spain
Argentina vs England
```

Current title probabilities:

```text
Spain:     30.1%
France:    28.1%
Argentina: 24.2%
England:   17.6%
```

Current top TSI values among remaining teams:

```text
Spain:     16.249
France:    16.188
Argentina: 15.822
England:   15.560
```

## Performance-Audit Behavior

Completed matches create a zero-sum TSI delta: one team's gain is the opponent's loss. The raw match signal combines result surprise and process surprise, then applies a soft cap and a conservative TSI weight.

Example quarter-final deltas:

```text
France 2-0 Morocco:      +3.174 final match delta for France
Spain 2-1 Belgium:       +2.489 final match delta for Spain
England 2-1 Norway:      +2.697 final match delta for England
Argentina 3-1 Switzerland:+2.909 final match delta for Argentina
```

These are not applied one-for-one to TSI. The TSI update uses a conservative post-match weight so that one game informs the model without dominating the full prior.

## Tradeoffs

- The score model uses Poisson for interpretability and speed.
- Match deltas are soft-capped to prevent one extreme result from overwhelming the model.
- Odds are a capped prior, not a direct input to same-game prediction.
- Penalty shootouts determine advancement but are excluded from modeled goals.
- The validation sample is still small; calibration should be monitored as more matches are added.

## Artifacts

```text
data/processed/validation_summary.parquet
data/processed/validation_calibration_bins.parquet
data/processed/knockout_match_performance.parquet
data/processed/knockout_match_performance_audit.parquet
docs/reports/validation-2026-07-12.md
```
