# PDF Template Analysis Summary - Signature Anchors

## Overview
This document summarizes the exact text anchors found in the GreenWatt agreement PDF templates for signature field placement. These anchors are crucial for accurate PDF form filling and signature positioning.

## Sample Documents Analyzed
1. **Micheal-Makin.pdf** - Individual subscriber agreement
2. **Ann-Curry.pdf** - Individual subscriber agreement 
3. **Gan Development-790 Southside Dr-413.pdf** - Business subscriber agreement
4. **Keith-Martin.pdf** - Individual subscriber agreement

## Key Signature Anchors Found

### 1. Individual Subscriber Agreements (Residential)
**Pattern for individual subscribers:**
```
Signature of Authorized CDG HostRepresentative: Date:
[Name appears on next line]
Signature of Subscriber: Date: [date]
```

**Exact text anchors:**
- `Signature of Authorized CDG HostRepresentative:` - For CDG Host signature
- `Date:` - For CDG Host date (immediately after representative signature line)
- `Signature of Subscriber:` - For subscriber signature
- `Date:` - For subscriber date (immediately after subscriber signature line)

### 2. Business Subscriber Agreements 
**Pattern for business subscribers:**
```
SOLAR PRODUCER: DRS Operations Company, LLC
By:
Name:
Title:
SUBSCRIBER: [Business Name]
By: [Person Name]
Name: [Person Name]  
Title: [Person Title]
```

**Exact text anchors:**
- `SOLAR PRODUCER: DRS Operations Company, LLC` - Header for solar producer section
- `By:` - Solar producer signature line (first occurrence)
- `Name:` - Solar producer name line (first occurrence)
- `Title:` - Solar producer title line (first occurrence)
- `SUBSCRIBER: [Business Name]` - Header for subscriber section
- `By:` - Subscriber signature line (second occurrence)
- `Name:` - Subscriber name line (second occurrence)
- `Title:` - Subscriber title line (second occurrence)

### 3. Other Important Text Anchors

**Project Information Section:**
- `Project Name:` - For project details
- `Business Name:` - For business information

**Common Elements:**
- `Subscriber` - Appears throughout document (147+ occurrences in sample)
- `Date:` - Multiple date fields throughout

## Implementation Notes for PDF Form Filling

### For Individual Agreements:
1. Look for `Signature of Authorized CDG HostRepresentative:` to place CDG host signature
2. Find the `Date:` immediately following for CDG host date
3. Look for `Signature of Subscriber:` to place subscriber signature  
4. Find the `Date:` immediately following for subscriber date

### For Business Agreements:
1. Look for `SOLAR PRODUCER: DRS Operations Company, LLC` section
2. Within that section, find the first `By:`, `Name:`, `Title:` sequence for solar producer
3. Look for `SUBSCRIBER: [Business Name]` section
4. Within that section, find the second `By:`, `Name:`, `Title:` sequence for subscriber

### Positioning Strategy:
- Use exact text matching to find anchor points
- Position signature fields relative to these anchors
- Account for line spacing and formatting variations
- Consider that names may appear on the line immediately following signature anchors

## Template Variations
- **Individual agreements**: Use simple signature lines with "Signature of..." format
- **Business agreements**: Use structured "By:", "Name:", "Title:" format with clear PRODUCER/SUBSCRIBER sections
- **Date formats**: Dates appear in various formats (10/31/2024, 1/15/2025, etc.)

## Recommended Anchor Hierarchy
1. **Primary anchors**: `Signature of Authorized CDG HostRepresentative:`, `Signature of Subscriber:`, `SOLAR PRODUCER:`, `SUBSCRIBER:`
2. **Secondary anchors**: `By:`, `Name:`, `Title:`, `Date:`
3. **Context anchors**: Use surrounding text to disambiguate when multiple instances exist

This analysis provides the exact text patterns needed for precise signature field placement in the PDF generation system.