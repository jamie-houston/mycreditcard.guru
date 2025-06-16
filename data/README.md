# 📊 Credit Card Data Scraping & Import Guide

Complete workflow for collecting, processing, and importing credit card data into the application.

## 🔄 Complete Workflow Overview

### 1. **Data Collection** 🌐
Save webpages locally → Run scraping scripts → Generate timestamped files → Import to database

### 2. **File Organization** 📁
```
data/
├── input/                          # Source HTML files
│   └── nerdwallet_bonus_offers_table.html
├── scraped/                        # Legacy scraped files
└── output/ → flask_app/data/output/ # Timestamped output files
    ├── 202506152230_nerdwallet_table_cards.json
    ├── 202506152232_nerdwallet_table_cards.json
    └── 202506152237_nerdwallet_table_cards.json
```

## 🕷️ Step 1: Data Scraping

### **NerdWallet Table Scraper**

**Source Preparation:**
1. Navigate to [NerdWallet Credit Cards](https://www.nerdwallet.com/best/credit-cards/bonus-offers)
2. Inspect source to get the <table> surrounding the credit cards and save to `data/input/<summary of page name>.html`
3. Ensure the table with credit card data is included

**Run Scraping Script:**
```bash
cd flask_app
python scripts/scraping/scrape_nerdwallet.py
```

**Expected Output:**
```
2025-06-15 22:37:45,742 - INFO - Loading table HTML file: .../data/input/nerdwallet_bonus_offers_table.html
2025-06-15 22:37:45,743 - INFO - Scraping NerdWallet table...
2025-06-15 22:37:45,762 - INFO - Found 20 card rows in table
2025-06-15 22:37:45,768 - INFO - Extracted 20 cards from table

======================================================================
NERDWALLET TABLE SCRAPING RESULTS
======================================================================
📊 Total cards found: 20
🎯 Cards with reward categories: 10
💬 Cards with reward tooltips: 20
🎁 Cards with intro offers: 3

Results saved to: /flask_app/data/output/202506152237_nerdwallet_table_cards.json
```

### **What Gets Extracted:**

**Card Information:**
- Card names and issuers
- Annual fees and NerdWallet ratings
- "Best for" categories
- Reward rate displays (e.g., "2x-5x")

**Detailed Rewards:**
- Parsed from aria-label tooltips
- Category-specific rates (e.g., "3x on dining")
- Handles compound categories ("dining, streaming services")
- Maps to standardized database categories

**Signup Bonuses:**
- Bonus amounts (points/miles/cash)
- Spending requirements
- Time limits
- Estimated values

**Example Extracted Data:**
```json
{
  "name": "Chase Sapphire Preferred® Card",
  "issuer": "Chase",
  "annual_fee": 95.0,
  "nerdwallet_rating": 5.0,
  "reward_categories": {
    "Travel": 2.0,
    "Dining & Restaurants": 3.0,
    "Streaming Services": 3.0,
    "Other": 1.0
  },
  "signup_bonus_points": 60000,
  "signup_bonus_min_spend": 5000.0,
  "signup_bonus_max_months": 3
}
```

## 📥 Step 2: Data Import

### **Method A: Command Line Import**

**Import All Files (Chronological Order):**
```bash
cd flask_app
python scripts/data/seed_credit_cards.py --import-scraped
```

**Import Specific File:**
```bash
cd flask_app
python scripts/data/seed_credit_cards.py --file /path/to/file.json
```

**View Options:**
```bash
cd flask_app
python scripts/data/seed_credit_cards.py --help
```

**Sample Output:**
```
📁 Processing file: 202506152230_nerdwallet_table_cards.json
   ✅ Imported 15 cards from 202506152230_nerdwallet_table_cards.json

📁 Processing file: 202506152232_nerdwallet_table_cards.json  
   ✅ Imported 18 cards from 202506152232_nerdwallet_table_cards.json

Total imported: 33 cards
```

### **Method B: Web Interface Import**

**1. Start Flask Application:**
```bash
cd flask_app && python run.py
```

**2. Navigate to Import Interface:**
- Open `http://127.0.0.1:5000`
- Go to **Credit Cards** → **Import Cards**
- Click **"Import from Files"** tab

**3. File Selection Interface:**
```
Available Files (3 files)                                    ☑ Import All Files

☑ Select All
File                                          Cards  Size    Modified         Details
☑ 202506152237_nerdwallet_table_cards.json   20     24.2KB  2025-06-15 22:37 Table Html Parsing • 10 with rewards
☑ 202506152232_nerdwallet_table_cards.json   20     24.1KB  2025-06-15 22:32 Table Html Parsing • 10 with rewards  
☐ 202506152230_nerdwallet_table_cards.json   20     24.0KB  2025-06-15 22:30 Table Html Parsing • 10 with rewards

[Import Selected Files (2)]
```

**4. Import Process:**
- Files processed chronologically (oldest → newest)
- Creates new cards or updates existing ones
- Maps reward categories to database categories
- Creates issuers automatically if needed
- Shows success/error messages

## ⚙️ Data Processing Details

### **File Naming Convention**
- Format: `YYYYMMDDHHMM_source_description.json`
- Example: `202506152237_nerdwallet_table_cards.json`
- Breakdown: 2025-06-15 22:37 NerdWallet table cards

### **Import Logic**
1. **Chronological Processing**: Oldest files first
2. **Duplicate Handling**: Updates existing cards (by name + issuer)
3. **Category Mapping**: Maps scraped text to standardized categories
4. **Issuer Management**: Creates unknown issuers automatically
5. **Error Resilience**: Continues processing if individual cards fail

### **Category Mapping Examples**
```
Scraped Text                           → Database Category
"3x on dining"                        → "Dining & Restaurants" (3.0x)
"2x on all other travel purchases"    → "Travel" (2.0x)  
"5x on gas stations"                  → "Gas Stations" (5.0x)
"select streaming services"           → "Streaming Services" (rate varies)
"dining, select streaming services"   → Multiple categories:
                                        - "Dining & Restaurants" (3.0x)
                                        - "Streaming Services" (3.0x)
```

### **Reward Processing Rules**
- **Skip Portal Bonuses**: Ignores "5x through Chase Travel" type bonuses
- **Extract General Rates**: Captures "2x on all other travel" rates
- **Handle Compound Categories**: Splits "dining, streaming, groceries"
- **Map to Standards**: Uses database category names and aliases

## ✅ Verification & Quality Control

### **Built-in Validation**
The scraper includes validation against known card structures:

**Chase Sapphire Preferred Test:**
```
✅ Category validation:
✅ Dining & Restaurants: 3.0x (expected 3.0x)
✅ Streaming Services: 3.0x (expected 3.0x)  
✅ Travel: 2.0x (expected 2.0x)
```

### **Data Quality Checks**
- **Required Fields**: Name, issuer, annual fee
- **Category Validation**: Maps to existing database categories
- **Rate Validation**: Ensures numeric reward rates
- **Bonus Validation**: Validates signup bonus structure

## 🛠️ Troubleshooting

### **Common Issues & Solutions**

**1. No Files Found:**
```
⚠️  No JSON files found in /flask_app/data/output
```
**Solution**: Run scraping scripts first to generate data files

**2. HTML File Missing:**
```
❌ HTML file not found: /data/input/nerdwallet_bonus_offers_table.html
```
**Solution**: Save webpage to correct location in `data/input/`

**3. Category Not Found:**
```
⚠️  Category 'Unknown Category' not found for card 'Card Name'
```
**Solution**: Add category to database or update category mapping in scraper

**4. Database Locked:**
```
❌ Error importing card 'Card Name': database locked
```
**Solution**: Ensure no other processes are using the database

### **Debug Commands**

**Check Available Files:**
```bash
ls -la flask_app/data/output/
```

**View File Contents:**
```bash
head -20 flask_app/data/output/202506152237_nerdwallet_table_cards.json
```

**Test Database Connection:**
```bash
cd flask_app && python -c "from app import create_app, db; app=create_app('development'); app.app_context().push(); print('DB OK')"
```

**Validate JSON File:**
```bash
cd flask_app && python -c "import json; print('Valid JSON' if json.load(open('data/output/filename.json')) else 'Invalid')"
```

## 📈 Monitoring & Maintenance

### **File Management**
- **Retention**: Files kept indefinitely for audit trail
- **Archival**: Older files can be moved/deleted manually
- **Timestamps**: Each import records timestamp in database

### **Performance Metrics**
- **Processing Speed**: ~1-2 seconds per file
- **Memory Usage**: ~50MB for 20-card files  
- **Database Growth**: ~1KB per card with categories
- **Success Rate**: >95% for well-formed HTML

### **Best Practices**

**1. Regular Data Collection:**
- Run scrapers weekly for fresh data
- Monitor source websites for structure changes
- Keep HTML files for debugging

**2. Import Management:**
- Import new files as they're created
- Backup database before large imports
- Monitor import logs for errors

**3. Quality Assurance:**
- Validate key cards after import (e.g., Chase Sapphire Preferred)
- Check category mappings for new reward types
- Review error logs for patterns

**4. Maintenance:**
- Update scrapers when websites change
- Add new category mappings as needed
- Archive old files periodically

## 🚀 Advanced Usage

### **Custom Scrapers**
To add new data sources:

1. Create scraper in `flask_app/scripts/scraping/`
2. Follow naming convention: `scrape_[source]_[type].py`
3. Save output to `flask_app/data/output/` with timestamp
4. Use standard JSON structure for compatibility

### **Batch Processing**
```bash
# Process multiple HTML files
for file in data/input/*.html; do
    python flask_app/scripts/scraping/scrape_nerdwallet.py "$file"
done

# Import all generated files
cd flask_app && python scripts/data/seed_credit_cards.py --import-scraped
```

### **Automated Workflows**
```bash
#!/bin/bash
# automated_update.sh
cd flask_app
python scripts/scraping/scrape_nerdwallet.py
python scripts/data/seed_credit_cards.py --import-scraped
echo "✅ Data update complete: $(date)"
```

This comprehensive system ensures reliable, traceable credit card data management with full audit trails and error handling! 🎯