# Harput Finans — Final Performance Evaluation

## AI Assistant

| Metric | Result |
|---|---:|
| Intent Classification Accuracy | **94.00% (47/50)** |
| Raw Slot Extraction Accuracy | **74.42% (128/172)** |
| Strict Exact Filter Match | **33.33% (10/30)** |
| Numeric Financial Grounding | **100.00% (92/92)** |
| Retrieval Micro Precision | **100.00%** |
| Retrieval Micro Recall | **100.00%** |
| Retrieval Micro F1 | **100.00%** |
| Retrieval Exact Set Match | **100.00% (24/24)** |
| Retrieved-record Source Integrity | **100.00% (130/130)** |
| Multi-turn Context Checks — Post-fix | **100.00% (77/77)** |
| Multi-turn Scenario Exact — Post-fix | **100.00% (10/10)** |
| No-data Safety Checks — Post-fix | **100.00% (108/108)** |
| No-data Case Exact — Post-fix | **100.00% (12/12)** |

These results represent separate evaluation layers and are not aggregated into a single overall assistant accuracy.

---

## Multi-turn Regression

| Metric | Pre-fix | Post-fix | Improvement |
|---|---:|---:|---:|
| Context Check Accuracy | 85.71% | **100.00%** | +14.29 pp |
| Scenario Exact Success | 80.00% | **100.00%** | +20.00 pp |

The same frozen 10-scenario test set was used before and after the fix.

---

## No-data Regression

| Metric | Pre-fix | Post-fix | Improvement |
|---|---:|---:|---:|
| Safety Check Accuracy | 99.07% | **100.00%** | +0.93 pp |
| Case Exact Success | 91.67% | **100.00%** | +8.33 pp |

The same frozen 12-case test set was used before and after the fix.

The final post-fix evaluation produced:

- 108/108 successful safety checks
- 12/12 exact cases
- 0 requested-target record leaks
- 0 invalid source URLs
- 0 unsupported numeric claims
- 0 answer URL leaks

---

## Retrieval

The deterministic retrieval backend achieved:

- TP = 130
- FP = 0
- FN = 0
- Micro Precision = 100%
- Micro Recall = 100%
- Micro F1 = 100%
- Exact Set Match = 24/24
- Retrieved-record Source Integrity = 130/130

Retrieval V1 was invalidated because of evaluator implementation errors.

V3 is an offline rescore of the saved V2 predictions after correcting the documented generic-TASIT / TICARI_TASIT ground-truth semantics.

---

## Numeric Financial Grounding

Among the 14 responses containing evaluable numeric financial expressions, 92 numeric values were detected.

All 92 values were supported by the corresponding deterministic tool evidence.

Numeric Financial Grounding = **100% (92/92)**.

This metric should not be interpreted as whole-agent accuracy.

---

## Extraction

| Metric | Harput | Qwen3.5 9B Direct JSON | Llama3.1 8B Direct JSON |
|---|---:|---:|---:|
| Technical Success | 78.00% | 100.00% | 98.00% |
| Strict — All Fields | 47.85% | 73.19% | 60.30% |
| Weighted — All Fields | 54.00% | 81.78% | 68.93% |
| Strict — Successful Only | 61.35% | 73.19% | 61.53% |
| Weighted — Successful Only | 69.23% | 81.78% | 70.33% |

The extraction comparison is against two direct-JSON baselines.

Because both the model and extraction methodology differ between systems, observed performance differences cannot be attributed solely to architectural design.

---

## Harput Extraction Consistency

- Technical success: **78.00% (117/150)**
- Field-value mean pairwise Jaccard: **65.33%**
- Presence consistency: **79.11%**
- All-nine-fields-identical across three runs: **4.00%**

Consistency metrics should not be labeled as extraction accuracy.

---

## Evaluation Limitations

The intent, slot/filter and grounding evaluation sets are assistant-authored frozen test sets rather than independent human-annotated benchmarks.

The retrieval test uses independently derived master-data ground truth, but the V3 score includes an explicitly documented post-hoc evaluator semantics correction.

Multi-turn and no-data post-fix results are regression measurements using the same frozen sets as their corresponding pre-fix evaluations.

For this reason, the project reports individual layer metrics rather than presenting a single overall accuracy value.