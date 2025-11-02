## Table Schema: `claims`

### Primary Key
- **claim_number** - Unique identifier for each claim

### Complete Field Reference

#### 1. **claim_number** (VARCHAR(50))
- **Description:** Unique claim identifier serving as the primary key
- **Nullability:** NOT NULL
- **Cardinality:** High (unique per claim)
- **Usage:** 
  - Primary identifier for tracking individual claims
  - Used for joins and references
  - Key for deduplication checks

---

#### 2. **product_category** (VARCHAR(100))
- **Description:** High-level product classification
- **Nullability:** YES (nullable)
- **Cardinality:** Low (limited distinct values)
- **Distribution:** Categorical field with few unique categories
- **Usage:**
  - Segment claims by product type
  - Group policies for portfolio analysis
  - Filter claims by insurance product line
- **Analysis Tip:** Check distinct values to understand product portfolio mix

---

#### 3. **product_name** (VARCHAR(200))
- **Description:** Specific product name within a category
- **Nullability:** YES (nullable)
- **Cardinality:** Medium (multiple products per category)
- **Distribution:** More granular than product_category
- **Usage:**
  - Detailed product performance analysis
  - Identify best/worst performing products
  - Calculate product-specific loss ratios
  - Compare claims frequency across products

---

#### 4. **claim_status** (VARCHAR(100))
- **Description:** Current status of the claim
- **Nullability:** YES (nullable)
- **Cardinality:** Very low (typically 2-5 distinct values)
- **Expected Values:** Likely includes "Open", "Closed", and possibly intermediate states
- **Usage:**
  - Filter active vs. closed claims
  - Calculate closure rates
  - Monitor claims workflow
  - Identify claims requiring attention
  - Calculate pending reserves (open claims)
- **Analysis Tip:** Check distribution between open/closed for workload assessment

---

#### 5. **accident_date** (DATE)
- **Description:** Date when the incident occurred
- **Nullability:** Implied NOT NULL (critical field)
- **Range:** Depends on data collection period
- **Usage:**
  - Timeline analysis of incidents
  - Seasonality patterns (peak travel months)
  - Calculate reporting lag (accident_date to report_date)
  - Trend analysis over time
  - Identify accident clusters
- **Analysis Considerations:**
  - Should always precede report_date
  - Check for data quality issues if after report_date

---

#### 6. **report_date** (DATE)
- **Description:** Date when the claim was reported to the insurer
- **Nullability:** Implied NOT NULL (required for claim initiation)
- **Range:** Should be >= accident_date
- **Usage:**
  - Calculate reporting lag (days from accident to report)
  - Monthly claims volume analysis
  - Workflow efficiency metrics
  - Identify late reporting patterns
- **Key Metric:** `reporting_lag = report_date - accident_date`

---

#### 7. **closed_date** (DATE)
- **Description:** Date when the claim was closed
- **Nullability:** YES (NULL for open claims)
- **Range:** Should be >= report_date
- **Distribution:** NULL for all open claims, populated for closed claims
- **Usage:**
  - Calculate claim settlement duration
  - Measure claims processing efficiency
  - Identify aging claims (long settlement times)
  - Calculate closure rates by period
- **Key Metrics:**
  - `settlement_duration = closed_date - report_date`
  - `total_lifecycle = closed_date - accident_date`
- **Analysis Tip:** NULL values indicate open/active claims

---

#### 8. **destination** (VARCHAR(100))
- **Description:** Travel destination country/region
- **Nullability:** YES (nullable)
- **Cardinality:** Medium-High (many possible destinations)
- **Distribution:** Likely skewed toward popular travel destinations
- **Usage:**
  - Geographic risk analysis
  - Destination-specific loss patterns
  - Pricing by destination risk
  - Identify high-risk destinations
  - Travel trend analysis
- **Analysis Considerations:**
  - May have data quality issues (spelling variations, abbreviations)
  - Can be grouped into regions for analysis

---

#### 9. **claim_type** (VARCHAR(100))
- **Description:** Type or classification of the claim
- **Nullability:** Implied by schema
- **Cardinality:** Low-Medium (limited claim types)
- **Usage:**
  - Categorize claims by type
  - Analyze type-specific patterns
  - Calculate type-specific loss ratios

---

#### 10. **cause_of_loss** (VARCHAR(100))
- **Description:** Root cause or reason for the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (various causes)
- **Usage:**
  - Root cause analysis
  - Identify preventable losses
  - Risk mitigation strategies
  - Claims prevention initiatives

---

#### 11. **loss_type** (VARCHAR(100))
- **Description:** Detailed category of the loss
- **Nullability:** Implied by schema
- **Cardinality:** Medium (multiple loss categories)
- **Expected Categories:** Medical, Baggage, Trip Cancellation, Trip Delay, etc.
- **Usage:**
  - Detailed loss analysis by category
  - Calculate loss-type-specific frequencies
  - Identify most expensive loss types
  - Portfolio composition analysis
  - Underwriting insights
- **Key Analysis:** Cross-tabulate with destination for risk assessment

---

### Financial Fields (All DECIMAL(10,2) in SGD)

#### 12-14. **Gross Fields** (gross_incurred, gross_paid, gross_reserve)
- **Description:** Financial amounts before reinsurance recovery
- **Nullability:** May contain NULL or 0
- **Range:** 0 to potentially millions (SGD)
- **Relationship:** `gross_incurred = gross_paid + gross_reserve`
- **Usage:**
  - Calculate total exposure
  - Measure claim costs before reinsurance
  - Assess reinsurance impact
- **Key Metrics:**
  - Total gross incurred losses
  - Average claim size (gross)

---

#### 15-17. **Net Fields** (net_incurred, net_paid, net_reserve)
- **Description:** Financial amounts after reinsurance recovery (company's actual exposure)
- **Nullability:** May contain NULL or 0
- **Range:** 0 to gross amounts (should be <= gross)
- **Relationship:** `net_incurred = net_paid + net_reserve`
- **Distribution:** 
  - net_paid: Right-skewed (few large claims, many small)
  - net_reserve: Only for open claims; 0 for closed claims
- **Usage:**
  - Calculate actual company loss exposure
  - Determine profitability
  - Reserve adequacy analysis
  - Cash flow projections
  - Loss ratio calculations