# Trending Score Algorithm

## Overview

The Trending Score Algorithm calculates a 0-100 score for each e-commerce store to indicate how "hot" or trending the store is. This score is used to rank stores and highlight emerging opportunities for entrepreneurs and market researchers.

## Scoring Formula

The trending score is calculated using **5 weighted factors**:

```
trending_score = (
    growth_score × 0.35 +
    recency_score × 0.25 +
    engagement_score × 0.20 +
    category_score × 0.10 +
    traffic_score × 0.10
)
```

### 1. Growth Velocity (35% weight)

**Purpose:** Identifies stores with rapid product expansion

**Calculation:**
- Compares current product count to historical data (7 and 30 days ago)
- Growth rate = ((current - previous) / previous) × 100

**Scoring Brackets:**
- **>50% growth:** 100 points
- **20-50% growth:** 70-100 points (linear interpolation)
- **5-20% growth:** 40-70 points (linear interpolation)
- **0-5% growth:** 20-40 points (linear interpolation)
- **Negative growth:** 0-20 points (penalty based on decline)

**Data Storage:**
- Historical product counts stored in Redis with 90-day TTL
- Updated on each scrape to track growth trends

### 2. Recency Bonus (25% weight)

**Purpose:** Highlights newer stores that may be riding trends

**Formula:**
```python
base_score = 100 - (days_since_created / 365 × 50)
```

**Scoring:**
- **< 30 days:** 90-100 points (extra boost for very new stores)
- **< 90 days:** 70-90 points
- **< 180 days:** 50-70 points
- **> 1 year:** Gradual decay to 0 over time

**Rationale:** Newer stores often capitalize on emerging trends and deserve higher visibility during their launch phase.

### 3. Product Engagement Score (20% weight)

**Purpose:** Measures product quality and market fit

**Components:**

#### a) Availability Ratio (40% of engagement)
```python
availability_ratio = available_products / total_products
availability_score = availability_ratio × 40
```

#### b) Price Range Optimization (30% of engagement)

**Sweet Spot:** $30-$150 (based on e-commerce conversion data)

**Scoring:**
- **$30-$150:** 30 points (optimal range)
- **$15-$30:** 20-30 points (below optimal)
- **$150-$300:** 20-30 points (above optimal)
- **Other ranges:** 10 points

#### c) Product Diversity (30% of engagement)
```python
diversity_ratio = unique_titles / total_products
diversity_score = diversity_ratio × 30
```

**Total Engagement:**
```python
engagement_score = availability_score + price_score + diversity_score
```

### 4. Category Momentum (10% weight)

**Purpose:** Compare store performance to category peers

**Calculation:**
1. Calculate preliminary score for store (without category component)
2. Get category average from cached data (6-hour TTL)
3. Calculate ratio: `store_score / category_avg`
4. Convert to 0-100 scale

**Scoring:**
- **Outperforming category (ratio > 1.0):** Higher scores (up to 100)
- **Underperforming category (ratio < 1.0):** Lower scores (down to 0)

**Caching:** Category averages cached for 6 hours to improve performance

### 5. Traffic Estimation (10% weight)

**Purpose:** Factor in actual visitor traffic when available

**Data Sources:** Similarweb, Ahrefs (future integrations)

**Scoring Brackets:**
- **>1M monthly visitors:** 100 points
- **500K-1M visitors:** 80-100 points
- **100K-500K visitors:** 60-80 points
- **10K-100K visitors:** 40-60 points
- **<10K visitors:** 0-40 points

**Fallback:** If no traffic data available, estimate from product count:
- >1000 products: 60 points
- >500 products: 50 points
- >100 products: 40 points
- <100 products: 30 points

## Additional Features

### Revenue Estimation

**Formula:**
```python
base_revenue = product_count × avg_price × 30 × 0.05
estimated_revenue = base_revenue × category_multiplier
```

**Assumptions:**
- 5% conversion rate (industry standard)
- 30 orders per month per product (conservative)

**Category Multipliers:**
- Fashion: 1.2×
- Beauty: 1.5×
- Electronics: 0.8×
- Home: 1.0×
- Health: 1.3×
- Sports: 0.9×
- Other: 1.0×

### Batch Processing

The `batch_calculate_trending_scores()` method processes all stores:

**Features:**
- Processes stores in order of last update (prioritizes stale data)
- Tracks significant score changes (>5 points)
- Commits all changes in a single transaction
- Returns detailed statistics

**Performance:**
- Can process 1000+ stores in a few minutes
- Uses async database operations for efficiency
- Caches category averages to reduce queries

## Running the Script

### Basic Usage

```bash
# Calculate for all active stores
python scripts/calculate_trending.py

# Process limited number for testing
python scripts/calculate_trending.py --limit 100

# Process all stores including inactive
python scripts/calculate_trending.py --all

# Enable verbose logging
python scripts/calculate_trending.py --verbose

# Show only major changes
python scripts/calculate_trending.py --min-score 10

# Show top trending stores after calculation
python scripts/calculate_trending.py --top 20
```

### Cron Job Setup

**Daily at 3 AM:**
```bash
0 3 * * * cd /path/to/backend && python scripts/calculate_trending.py >> /var/log/trending.log 2>&1
```

**Every 6 hours:**
```bash
0 */6 * * * cd /path/to/backend && python scripts/calculate_trending.py >> /var/log/trending.log 2>&1
```

## Edge Cases Handled

### New Stores (No Historical Data)
- **Growth Score:** 50 points (neutral)
- **Category Score:** 50 points (neutral)
- First scrape establishes baseline for future growth tracking

### Stores with No Products
- **Engagement Score:** 0 points
- **Growth Score:** 0 points (no growth possible)
- Other factors still apply

### Stores with Missing Data
- **Missing traffic data:** Uses product count fallback
- **Missing price data:** Defaults to $50 average
- **Missing availability data:** Assumes 100% available

### Category with Few Stores
- **Category Average:** Defaults to 50 if no stores in category
- Prevents division by zero errors

## Performance Optimizations

### Redis Caching
1. **Historical Data:** 90-day TTL for growth tracking
2. **Category Averages:** 6-hour TTL to reduce database queries
3. **View Counts:** Real-time tracking without database load

### Batch Processing
- Single database transaction for all updates
- Processes stores in order of staleness
- Can be limited for testing or incremental updates

### Async Operations
- All database operations use async/await
- Concurrent processing of multiple stores possible
- Non-blocking I/O for Redis operations

## Monitoring and Logging

### Script Output
```
======================================================================
  E-Commerce Intelligence SaaS - Trending Score Calculator
======================================================================
  Started at: 2024-01-15 03:00:00
======================================================================

🚀 Starting trending score calculation...
   Mode: Active stores only

📊 Calculating scores...

======================================================================
  CALCULATION COMPLETE
======================================================================
  Total stores processed: 1,523
  Successfully updated:   1,520
  Errors encountered:     3
======================================================================

📈 Significant Score Changes (>= 5.0 points):
----------------------------------------------------------------------
 1. 📈 example-store.myshopify.com              45.2 →  78.9 (+33.7)
 2. 📈 trending-shop.com                        52.1 →  81.4 (+29.3)
 3. 📉 declining-store.com                      67.8 →  41.2 (-26.6)
...

✨ Success rate: 99.8%
⏰ Completed at: 2024-01-15 03:05:23
======================================================================
```

### Log Files
- **Console Output:** Real-time progress and results
- **trending_calculation.log:** Detailed logs with timestamps
- **Error Tracking:** Stack traces for debugging

## Future Enhancements

### Planned Features
1. **Social Media Integration:** Track Instagram/TikTok mentions
2. **Review Score Factor:** Integrate Trustpilot/Google reviews
3. **Keyword Trending:** Detect trending product keywords
4. **Seasonal Adjustment:** Account for seasonal businesses
5. **Machine Learning:** Predict future trending scores
6. **A/B Testing:** Optimize scoring weights based on user engagement

### API Integration Points
- Similarweb API for traffic data
- Ahrefs API for backlink analysis
- Google Trends API for keyword momentum
- Social media APIs for brand mentions

## Technical Details

### Database Schema Impact
The algorithm updates the following Store fields:
- `trending_score` (Float): The calculated 0-100 score
- `growth_rate` (Float): Percentage growth rate
- `estimated_monthly_revenue` (Integer): Calculated revenue estimate
- `updated_at` (DateTime): Last calculation timestamp

### Redis Keys Used
```python
f"store_history:{store.id}"           # Historical product counts
f"category_avg:{category.value}"      # Cached category averages
```

### Dependencies
- SQLAlchemy (async database operations)
- Redis (caching and historical data)
- Python 3.10+ (async/await support)

## Testing

### Manual Testing
```bash
# Test with single store
python -c "
from app.services.trending_service import TrendingService
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.store import Store

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Store).limit(1))
        store = result.scalar_one()
        score = await TrendingService.calculate_trending_score(store, db)
        print(f'Score: {score}')

asyncio.run(test())
"
```

### Unit Tests
Create tests in `tests/services/test_trending_service.py`:
- Test each scoring factor independently
- Test edge cases (no data, negative growth, etc.)
- Test batch processing performance
- Test caching behavior

## Support

For questions or issues:
1. Check logs in `trending_calculation.log`
2. Review store data in database
3. Verify Redis connection and cached data
4. Contact development team with error details
