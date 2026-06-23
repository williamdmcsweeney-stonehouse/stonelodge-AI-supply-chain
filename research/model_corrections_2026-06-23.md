# Model corrections, 2026-06-23 — FLOPs-native demand + retirement dial

Two opt-in levers added to `build_macro_gap` in `model.py`. **Both default OFF and
reproduce the committed base case byte-for-byte** (verified: the committed-base
fingerprint hash `fdd0de9ef53c8247` and the 332.4256 GW @ 2029 peak are unchanged).
They follow the model's house pattern: every new knob is an opt-in toggle whose
default leaves the locked headline untouched. The dashboards keep the base case
because they call `build_macro_gap` with keyword args and never set these.

Why these two: they are the highest-leverage fixes from the 2026-06-18 discussion
on how tokens convert to gigawatts. ITEM 8 fixes the "a token is not a fixed amount
of compute" problem. ITEM 9 fixes the "is the 2030s a plateau or a cliff" problem,
which previously was a hidden binary switch.

---

## ITEM 8 — FLOPs-native demand basis + model-mix routing lever

### The problem it fixes
The committed base measures demand in **raw token count** and divides by a single
blended **tokens/kWh** efficiency index. That one number secretly fuses three
different things:

> tokens/kWh  ≈  (hardware FLOPS/W) × (MFU) ÷ (2 × N_active)

so when it "doubles every ~1.85 years" you cannot tell whether that came from
better chips, better software, or smaller/cheaper models. And because every token
is treated as identical, the model is blind to routing/orchestration (which shifts
work from frontier models to small ones), even though that is a real efficiency
lever. A frontier token costs ~50x the FLOPs of a small-model token.

### The fix
When `use_flops_demand=True`, demand is rebuilt from first principles:

```
FLOPs/day      = tokens/day × (2 × N_active)          # Kaplan / Chinchilla 2N rule
power proxy (W) = FLOPs/day ÷ 86400 ÷ (fleet_TFLOP/W × MFU)
```

- `N_active` is the **mix-weighted** active-parameter count. The routing mix shifts
  from frontier-heavy (2025) toward small-model-heavy (2040), so model-size shrink
  becomes an explicit, tunable efficiency channel — separate from hardware.
- `fleet_TFLOP/W` reuses the existing `tflop_per_w_for_year()` ramp (9 -> 60), so
  hardware efficiency is the *other*, now-separated channel.
- `MFU` and the 86400 constant cancel in the 2025 re-anchor, so they do not move the
  curve; they are kept only so the formula reads as real physics. 2025 still anchors
  to 70 GW, so token mode and FLOPs mode are directly comparable from the same start.

### Parameters (all defaulted; defaults are illustrative, see Calibration below)
| Param | Default | Meaning |
|---|---|---|
| `use_flops_demand` | `False` | OFF = committed token-count basis |
| `flops_n_active_b` | `(500, 70, 8)` | active params (billions): frontier / mid / small |
| `flops_mix_2025` | `(0.55, 0.30, 0.15)` | 2025 token shares per tier (frontier-heavy) |
| `flops_mix_2040` | `(0.15, 0.35, 0.50)` | 2040 token shares (routed toward small models) |
| `flops_mfu` | `0.35` | model-FLOPs-utilization (cancels in anchor) |

Two new diagnostic output columns: `avg_n_active_b`, `flops_per_day` (both 0 in
token mode).

### What it shows (defaults)
| | peak gap | peak yr | overshoot | 2042 demand |
|---|---|---|---|---|
| token basis (base) | 332 GW | 2029 | 2034 | 549 GW |
| FLOPs basis | 278 GW | 2031 | 2036 | 708 GW |

Mix-weighted N falls 297B (2025) -> 104B (2040): a ~2.9x model-size shrink. Combined
with ~6.7x hardware TFLOP/W gain that is ~19x total efficiency by 2040 — far below
the token path's implied ~122x. Year by year (demand GW):

```
year  token  flops
2025     70     70
2028    427    307     <- FLOPs LOWER early (TFLOP/W improves faster than the lagged index)
2029    509    390
2030    549    476
2032    549    619     <- crossover: FLOPs now HIGHER
2035    549    701
2042    549    708
```

**Read:** the FLOPs view is more efficient *early* (hardware improves faster than the
slow fleet-lagged index) but much less efficient *late* (physical efficiency cannot
match the token path's exponential). Net result: a later, lower peak, but no
out-year collapse and a later gap-close (2036 vs 2034). The bear "efficiency rolls
the gap over in the mid-2030s" case depends materially on the optimistic tokens/kWh
curve; under raw FLOPs physics the power thesis is more durable.

This also surfaces a real inconsistency worth reconciling: the macro 1.85-yr doubling
index and the layer `tflop_per_w` 9->60 ramp imply *different* efficiency
trajectories. The FLOPs path makes that visible (it is why the two curves diverge).

---

## ITEM 9 — tunable capacity retirement dial

### The problem it fixes
The committed base uses a **strict monotonic floor**: once net demand is set it can
never fall (deployed fleet is never torn down). The only alternative previously was
to remove the floor entirely. So the 2030s outcome was a hidden **binary**:
plateau (floor on) vs cliff (floor off). Reality is in between.

### The fix
`capacity_retirement_rate` decays the frozen floor each year:

```
decayed_floor = net_demand_prev × (1 - capacity_retirement_rate)
net_compute_demand_T = max(net_compute_demand_raw_T, decayed_floor)
```

- `0.0` -> strict monotonic floor = committed base (plateau).
- `1.0` -> floor fully released = pure raw physics (the cliff).
- `0 < r < 1` -> old/inefficient capacity retires at `r`/yr; demand slides toward
  the raw physics line at a controlled pace.

### What it shows
| retirement rate | peak gap | 2042 demand | overshoot |
|---|---|---|---|
| 0.0 (base) | 332 GW @ 2029 | 549 GW | 2034 |
| 0.10 | 332 GW @ 2029 | 171 GW | 2033 |
| 0.20 | 332 GW @ 2029 | 62 GW | 2033 |
| 1.00 (cliff) | 332 GW @ 2029 | 48 GW | 2033 |

The peak is unchanged in every case — retirement only acts after the peak, which is
the correct behavior. This is the single biggest swing factor in the out-years, now
a continuous dial instead of an invisible switch.

---

## How to run it

```python
import model
tok = model.build_token_demand(scenario="Base")

base   = model.build_macro_gap(tok)                                 # committed base
flops  = model.build_macro_gap(tok, use_flops_demand=True)          # ITEM 8
retire = model.build_macro_gap(tok, capacity_retirement_rate=0.20)  # ITEM 9
both   = model.build_macro_gap(tok, use_flops_demand=True,
                               capacity_retirement_rate=0.20)        # combined "realistic"

print(model.gap_summary(flops))
```

Tune the routing assumption directly, e.g. aggressive shift to small models:

```python
model.build_macro_gap(tok, use_flops_demand=True,
                      flops_mix_2040=(0.05, 0.25, 0.70))
```

---

## Where the levers live (control surfaces)
Added 2026-06-23 so these are not abstract Python-only knobs:

1. **Excel — `Token_and_Data_Build_Out_v4_2.xlsx`, tab "Macro Levers".** Edit
   column B. This is the home of the ITEM 8 / ITEM 9 defaults. The tab was inserted
   by surgical zip-level edit that left every existing sheet's formula cache
   byte-for-byte intact (verified: the model still reads identical demand, golden
   hash `fdd0de9ef53c8247`). The model NEVER rewrites this workbook, so the 2,400+
   live formulas are safe.
2. **`model.load_macro_levers()`** reads that tab and returns `build_macro_gap`
   kwargs. Fully robust: missing sheet / key / blank cell each falls back to the
   committed-base default, so the workbook can never break a run. With the shipped
   defaults, `build_macro_gap(tok, **load_macro_levers())` reproduces the base case.
3. **Dashboard (`dashboard_v2/app.py`)** — sidebar expander "Advanced — FLOPs demand
   & retirement (ITEM 8 / ITEM 9)". The sliders are SEEDED from the Excel tab (so the
   Excel sets the starting point) and then let you flex live without touching Excel.

Flow: edit Excel tab -> defaults change in dashboard + `load_macro_levers()` callers.
Move a slider -> live override for that session. Code defaults in `model.py` are the
final fallback. All three agree on the committed base out of the box.

## Calibration caveats (read before quoting any FLOPs number)
- The default `flops_n_active_b` and mix tuples are **illustrative**, not calibrated.
  Pin them to disclosed model sizes and observed routing before citing the FLOPs
  peak as a headline.
- The FLOPs path and the token path use different efficiency curves
  (`tflop_per_w` ramp vs the 1.85-yr doubling index). They do not currently agree;
  reconciling them is calibration work (deferred item #5 below).
- Decode tokens are memory-bandwidth-bound, not FLOP-bound, so 2N slightly
  understates decode power. First-order fine; a v2 would add an HBM-bandwidth term.

## Deferred (proposed earlier, intentionally NOT built here)
These are larger or need external data; left for a follow-up so this change stays
self-contained and low-risk.
- **#3 Decompose the ÷utilization divisor** into training / inference / idle-redundancy.
- **#4 Backlog / book-to-bill layer** so the model emits the *equity* clock (order
  growth rolling, 2-4 yrs before the physics peak), not just the physics clock.
- **#5 Calibrate** the FLOPs `N`/mix and reconcile the two efficiency curves against
  disclosed hyperscaler capex, tokens/day, and GW-online actuals.
