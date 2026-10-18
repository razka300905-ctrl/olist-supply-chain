# Data pipeline: raw CSV → clean, analysis-ready tables

This is the shared foundation for all three portfolio projects (site selection, VRP, inventory). Every analysis reads the **clean layer**, never the raw CSVs directly.

```
archive/*.csv ──► 01_load_raw.py ──► raw_* tables (TEXT, untouched)
                                        │
                                        ▼
                                  02_clean.py ──► clean tables (typed, standardized, flagged)
                                        │            + clean_csv/*.csv
                                        ▼
                                  reports/cleaning_log.csv   (every rule, rows affected, action)
                                  reports/row_counts.csv     (raw vs clean row counts)
```

Both layers live in one SQLite file, `olist.db`, which can be rebuilt at any time. Raw tables are prefixed `raw_`. Clean tables have plain names: `orders`, `customers`, and so on.

## Cleaning principles

1. **Never delete silently.** A row is dropped only if it is an exact duplicate or physically impossible. Anything questionable is kept with a **flag column**, so each analysis decides for itself.
2. **Log every rule.** Each rule writes its row count and action to `reports/cleaning_log.csv`.
3. **Validate at the end.** Primary keys, foreign keys, zip format, state codes and geo coverage are checked. The script stops if any check fails.

## What was cleaned

| Table | Issue found | Rows | Action |
|---|---|---|---|
| geolocation | Coordinates outside Brazil | 42 | Dropped |
| geolocation | Exact duplicate rows (after standardizing city names) | ~280k of 1.0M | Dropped |
| geolocation | ~38 points per zip | – | Aggregated to one **median** centroid per zip (`geo_zip_centroid`) |
| customers / sellers | Zip codes missing from geolocation | 163 | 162 filled from the 3-digit zone centroid (`source = zip3_fallback`) |
| sellers | Free-typed cities: `sao paulo / sao paulo`, `lages - sc`, `sbc/sp`, a zip code, an e-mail, typos (`floranopolis`) | ~80 | Standardized; values that are not a known city name were replaced with the city of the zip code |
| all city columns | Accents, case, double spaces, `´` apostrophes | – | `são paulo` → `sao paulo`; official hyphens kept (`embu-guacu`) |
| orders | Status "delivered" but no delivery date | 8 | Flagged |
| orders | Handed to carrier before purchase | 166 | Flagged |
| orders | Delivered to customer before carrier pickup | 23 | Flagged |
| orders | Orders with no items | 775 | Flagged (`has_items = 0`) |
| orders | Timestamps stored as text, in mixed formats | all | Parsed and stored as ISO `YYYY-MM-DD HH:MM:SS`. Added `delivery_days`, `estimated_days`, `is_late` |
| orders | – | 96,447 | **`is_valid_delivered = 1`**: the standard filter for logistics analyses |
| products | Column-name typo `lenght` | 2 cols | Renamed to `_length` |
| products | Missing category | 610 | Set to `unknown` |
| products | Weight or dimensions missing or 0 | 6 | Imputed with the category median, flagged |
| products | – | – | Added `product_category_name_english` and `product_volume_cm3` |
| category_translation | 2 categories with no English name | 2 | Added manually |
| order_payments | 0 installments | 2 | Set to 1 |
| order_reviews | Free-text comment columns (88% / 59% empty) | 2 cols | Dropped (not needed for supply chain). Kept a `has_comment` flag |

**Note on empty columns:** no column in the dataset is 100% empty. Columns with partial nulls are kept when they carry information, and the gaps are flagged or imputed instead. The only columns dropped are the two Portuguese free-text review fields.

## Validation checks (all pass)

- Primary keys are unique for all 7 entity tables.
- Foreign keys are complete: items → orders, products, sellers; orders → customers; payments and reviews → orders.
- All zip codes are 5-digit text, and all states are valid Brazilian state codes (UFs).
- No city names are missing.
- 100% of customer zips have coordinates.

## Run

```bash
.venv/Scripts/python data_pipeline/01_load_raw.py
.venv/Scripts/python data_pipeline/02_clean.py
```
