# Test suites

Tests are organized by the behavior they protect. They do not download a model,
contact a provider or submit an order.

| Suite | Responsibility |
| --- | --- |
| `contracts/` | Identity, scalar types, units, windows, source mapping and policy requirements |
| `strategy/` | Entry, holding and exits; optional coverage; explicit reasons and exact thresholds |
| `runtime/` | Typed output validation, caching, durable assessments, recovery and stream boundaries |
| `reporting/` | Price arithmetic, capture integrity, native-input binding and the published market window |
| `cases/` | Catalog boundary corpus shared by contract checks |
| `helpers.py` | Small controlled backends and input builders for software regressions |

```bash
python -m pip install -e . ruff==0.16.8
python -m unittest discover -s tests -v
python -m unittest discover -s tests/reporting -v
```

The published-window regression reads recorded native responses; it does not
replace them with controlled answers or perform new inference. It recalculates
all 621 report series and checks all 180 input/output bindings.

Model quality is reported separately in the window's task table. Passing a
software regression means the contract behaved as asserted; it is not an
accuracy score for a model or a return forecast.
