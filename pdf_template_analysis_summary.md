# PDF Template Analysis Summary

## Analysis Overview
This document provides a detailed analysis of the PDF templates in the GreenWatt-documents folder, identifying their structure, signature areas, fillable fields, and programmatic requirements.

## 1. GreenWattUSA_Limited_Power_of_Attorney.pdf

### Document Structure:
- **Pages**: 2
- **Type**: Limited Power of Attorney for Community Solar Enrollment
- **Purpose**: Authorizes GreenWatt USA Inc. to enroll customers in Community Solar programs

### Fillable Fields (Customer Information Section):
- Customer Name: `__________________________`
- Service Address: `__________________________` 
- Utility Provider: `__________________________`
- Utility Account Number: `____________________`

### Signature Areas (Page 2):
- Customer Signature: `__________________________`
- Printed Name: `__________________________`
- Date: `__________________________`
- Email Address: `__________________________`
- Phone Number (optional): `__________________________`

### POA ID Placement:
- **Recommendation**: Add POA ID field at the top of the document after the title
- **Alternative**: Include in the customer information section as "POA Reference ID"

### Programming Notes:
- Simple 2-page document, easy to fill programmatically
- Clear field separators with underscores
- Consistent formatting throughout

---

## 2. Meadow-National-Grid-Commercial-UCB-Agreement.pdf

### Document Structure:
- **Pages**: 11
- **Type**: Master Electricity Discount Agreement (Commercial UCB)
- **Utility**: National Grid
- **Purpose**: Community Distributed Generation Bill Credits purchase agreement

### Key Fillable Areas:

#### Page 2 (Agreement Header):
- Effective Date: `_______________(the "Effective Date")`
- Subscriber Company Name: `_____________________________________`
- Business Type: "a Domestic Business Corporation"

#### Page 9 (Signature Page):
```
SOLAR PRODUCER: DRS Operations Company, LLC
By: [Signature field]
Name: [Name field]  
Title: [Title field]

SUBSCRIBER: [Company Name]
By: [Signature field]
Name: [Name field]
Title: [Title field]
```

#### Page 10 (Exhibit 1 - Utility Accounts Table):
Table with columns:
- Utility Company
- Name on Utility Account
- Utility Account Number  
- Service Address

#### Page 11 (Exhibit 2 - Facility Schedule Change Form):
Complex table with multiple columns for account management

### Signature Requirements:
- **Solar Producer**: Pre-filled with "DRS Operations Company, LLC"
- **Subscriber**: Requires company name, authorized signatory details

### POA ID Placement:
- **Recommendation**: Add to Exhibit 1 as additional column "POA Reference ID"
- **Alternative**: Include in header section next to effective date

### Programming Complexity: **High**
- Multiple pages with complex legal text
- Structured exhibits requiring table filling
- Corporate signature requirements

---

## 3. Meadow-NYSEG-Commercial-UCB-Agreement.pdf

### Document Structure:
- **Pages**: 11  
- **Type**: Master Electricity Discount Agreement (Commercial UCB)
- **Utility**: NYSEG
- **Purpose**: Identical to National Grid version, utility-specific

### Key Differences from National Grid Version:
- Page 1: References "NYSEG" instead of "National Grid"
- All other structure and fields identical
- Same signature page layout (Page 9)
- Same exhibit structure (Pages 10-11)

### Fillable Fields: 
Same as National Grid version

### Programming Notes:
- Can use same template structure as National Grid
- Only utility name needs to be dynamically changed
- Identical signature and exhibit requirements

---

## 4. Meadow-RGE-Commercial-UCB-Agreement.pdf

### Document Structure:
- **Pages**: 11
- **Type**: Master Electricity Discount Agreement (Commercial UCB)  
- **Utility**: RGE (Rochester Gas & Electric)
- **Purpose**: Identical to other commercial UCB agreements

### Key Differences:
- Page 1: References "RGE" instead of other utilities
- All other structure identical to National Grid/NYSEG versions

### Programming Notes:
- Can use same template as other commercial UCB agreements
- Utility name is only variable parameter
- Identical signature and exhibit structure

---

## 5. Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf

### Document Structure:
- **Pages**: 12
- **Type**: Community Distributed Generation Disclosure Form + Subscription Agreement
- **Target**: Mass Market (Residential) customers
- **Purpose**: Residential community solar subscription with UCB

### Key Fillable Fields:

#### Page 1 (Customer Information):
- Customer Name/Address fields (implied from context)
- Distribution Utility field

#### Project Information (TBD Fields):
- Project Name: TBD
- Project Location: TBD  
- Project Size: TBD
- Project Allocation Percentage: TBD
- Estimated Project In-Service Date: TBD

#### Page 12 (Cancellation Notice):
- Date of Transaction: `[DATE SUBSCRIBER SIGNED AGREEMENT]`
- Customer Name: `_________________`
- Cancellation Date: `______________________[DATE]`
- Customer Signature: `__________________________________________`

### Signature Areas:
- Multiple signature requirements throughout
- Final cancellation notice with customer signature
- Less formal than commercial agreements

### POA ID Placement:
- **Recommendation**: Add to customer information section on page 1
- **Alternative**: Include as reference number in project information

### Programming Complexity: **Medium**
- Longer document with multiple sections
- Mix of formal agreement and disclosure language
- Residential-focused, simpler than commercial versions

---

## 6. GreenWATT-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf

### Document Structure:
- **Pages**: 4
- **Type**: Community Solar Agency Agreement
- **Purpose**: Authorizes GreenWATT USA Inc. to act as agent for community solar enrollment

### Key Features:
- **Plain Language Summary**: First section explains the agreement in simple terms
- **Agency Authorization**: Detailed explanation of agent powers
- **No Direct Signatures**: References electronic signature via LOA format

### Signature Method:
- Uses electronic signature format: `"[USER FIRST NAME LAST NAME] BY GreenWATT USA Inc. (LOA)"`
- No traditional signature lines

### Fillable Fields:
- Customer contact information (referenced but not explicitly shown as form fields)
- Email address for notifications
- Account information (handled programmatically)

### POA ID Integration:
- **Natural Fit**: This document already references LOA (Limited Power of Attorney)
- **Recommendation**: Add POA ID as reference number in agency relationship

### Programming Complexity: **Low**
- Shortest document (4 pages)
- Minimal form filling required
- Electronic signature process
- Template-friendly structure

---

## Programming Implementation Recommendations

### 1. Template Hierarchy:
```
Primary Templates:
├── Power of Attorney (POA) - Simple authorization
├── Agency Agreement - Electronic authorization  
├── Mass Market UCB - Residential subscription
└── Commercial UCB - Business subscription
    ├── National Grid variant
    ├── NYSEG variant  
    └── RGE variant
```

### 2. Common Fillable Field Types:
- **Customer Information**: Name, address, phone, email
- **Utility Information**: Provider name, account number, service address
- **Signature Blocks**: Name, title, date, signature
- **Reference Numbers**: POA ID, transaction dates
- **Project Information**: Allocation percentages, project details

### 3. POA ID Integration Strategy:
1. **Power of Attorney**: Add as header reference number
2. **Commercial UCB**: Include in Exhibit 1 utility accounts table
3. **Mass Market UCB**: Add to customer information section
4. **Agency Agreement**: Reference as part of LOA authorization

### 4. Signature Placement Standards:
- **Power of Attorney**: Customer signature only (page 2)
- **Commercial UCB**: Dual signature (Solar Producer + Subscriber, page 9)
- **Mass Market UCB**: Customer signature (multiple locations)
- **Agency Agreement**: Electronic signature (no physical signature lines)

### 5. Template Fill Complexity Ranking:
1. **Agency Agreement** (Lowest) - Minimal fields, electronic process
2. **Power of Attorney** (Low) - Simple 2-page form
3. **Mass Market UCB** (Medium) - Multiple sections, residential focus
4. **Commercial UCB** (Highest) - Complex exhibits, corporate signatures

## Implementation Notes

### PDF Manipulation Approach:
1. **Field Identification**: Use coordinate-based positioning for text placement
2. **Template Variants**: Create utility-specific versions of commercial UCB
3. **Dynamic Content**: Implement variable substitution for utility names
4. **Signature Handling**: Different approaches for different document types

### Quality Assurance:
- Test with various customer data lengths
- Verify signature block alignment
- Ensure POA ID placement doesn't disrupt layout
- Validate exhibit table formatting

### Integration Points:
- Customer data from intake system
- Utility bill parsing results
- POA ID generation and tracking
- Electronic signature workflow
- Document delivery system