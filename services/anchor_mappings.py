"""
Anchor-based signature and field placement configurations for PDF templates.
Each template has specific anchor text and offset coordinates for precise placement.
"""

# POA Template Anchor Mapping (Dynamic page search)
POA_ANCHORS = {
    # Page 1: Customer Information Fields
    "customer_name_page1": {
        "anchor": "Customer Name:",
        "dx": 120,  # Reduced offset - move text left
        "dy": -2
    },
    "service_address_page1": {
        "anchor": "Service Address:",
        "dx": 130,  # Reduced offset - move text left
        "dy": -2
    },
    "utility_provider_page1": {
        "anchor": "Utility Provider:",
        "dx": 140,  # Reduced offset - move text left
        "dy": -2
    },
    "utility_account_page1": {
        "anchor": "Utility Account Number:",
        "dx": 190,  # Reduced offset - move text left
        "dy": -2
    },
    
    # Page 2: Signature Fields
    "customer_signature": {
        "anchor": "Customer Signature:",
        "dx": 150,  # Reduced offset - signatures may be too far right
        "dy": -2
    },
    "printed_name": {
        "anchor": "Printed Name:",
        "dx": 100,  # Reduced offset 
        "dy": -2
    },
    "date_signed": {
        "anchor": "Date:",
        "dx": 50, 
        "dy": -2
    },
    "email": {
        "anchor": "Email Address:",
        "dx": 120,  # Reduced offset
        "dy": -2
    },
    
    # Document ID & Timestamp Fields (below phone number)
    "submission_id": {
        "anchor": "Phone Number",
        "dx": 0,    # Start at left edge of phone field
        "dy": 30    # Position lower below phone number for more white space
    },
    "poa_id_placement": {
        "anchor": "Phone Number",
        "dx": 0,    # Start at left edge of phone field 
        "dy": 45    # Position below submission ID
    },
    "generation_timestamp": {
        "anchor": "Phone Number",
        "dx": 0,    # Start at left edge of phone field
        "dy": 60    # Position below POA ID
    }
}

# Universal Commercial UCB Agreement Anchors (Dynamic page search)
# These work for National Grid, NYSEG, RG&E commercial agreements
UCB_COMMERCIAL_ANCHORS = {
    # Page 2: Agreement Header Fields (Anchor-based)
    "effective_date": {
        "anchor": "Effective Date",
        "dx": -80,  # Move further LEFT from the anchor 
        "dy": 8     # Move UP less to position in the blank line
    },
    "agreement_business_name": {
        "anchor": "between",
        "context": "Effective Date",  # Look for "between" near "Effective Date" 
        "dx": 50,   # Move less to the right to center in the long blank line
        "dy": 8     # Move UP less to position in the blank line
    },
    
    # Page 7: Subscriber Information Fields (Fixed coordinates) - Final positioning adjustment
    "subscriber_attention": {"x": 188.5, "y": 617.8},  # Subscriber Attention field - moved up 10px, right 15px
    "subscriber_business_name": {"x": 209.9, "y": 630.9},  # Subscriber Business Name field - moved up 10px, right 15px
    "subscriber_address": {"x": 180.9, "y": 644.1},  # Subscriber Address field - moved up 10px, right 15px
    "subscriber_email": {"x": 171.7, "y": 657.5},  # Subscriber Email field - moved up 10px, right 15px
    "subscriber_phone": {"x": 174.7, "y": 670.8},  # Subscriber Phone field - moved up 10px, right 15px
    
    # Signature Section Fields (Anchor-based) - Adjusted for proper alignment
    "customer_signature": {
        "anchor": "By:",
        "context": "SUBSCRIBER:",  # Look for "By:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 2  # Moved up 13 pixels (was 15, now 2) for better positioning on signature line
    },
    "printed_name": {
        "anchor": "Name:",
        "context": "SUBSCRIBER:",  # Look for "Name:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 2  # Moved up 13 pixels (was 15, now 2) for better positioning
    },
    "title": {
        "anchor": "Title:",
        "context": "SUBSCRIBER:",  # Look for "Title:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 2  # Moved up 13 pixels (was 15, now 2) for better positioning
    },
    
    # Document ID & Timestamp Fields (below Title field in Subscriber section)
    "submission_id_agreement": {
        "anchor": "Title:",
        "context": "SUBSCRIBER:",  # Look for "Title:" in subscriber section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 0,    # Start at left edge of title field
        "dy": 30    # Position lower below title field
    },
    "generation_timestamp_agreement": {
        "anchor": "Title:",
        "context": "SUBSCRIBER:",  # Look for "Title:" in subscriber section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 0,    # Start at left edge of title field
        "dy": 45    # Position lower below submission ID
    },
    # "email": {
    #     "anchor": "Email:",
    #     "dx": 120, 
    #     "dy": -2
    # }
}

# Mass Market Agreement Anchors
MASS_MARKET_ANCHORS = {
    # Page 1: Customer Information Box
    "customer_info_name": {
        "anchor": "Customer",
        "dx": 150,  # Position in the data area of the box
        "dy": 5,    # Slightly below the header
        "font_size": 10
    },
    "customer_info_address": {
        "anchor": "Customer", 
        "dx": 150,  # Same X as name
        "dy": 20,   # Second row 
        "font_size": 10
    },
    "customer_info_city": {
        "anchor": "Customer",
        "dx": 300,  # Middle of the row
        "dy": 20,   # Same row as address
        "font_size": 10
    },
    "customer_info_state": {
        "anchor": "Customer", 
        "dx": 450,  # Right side for state
        "dy": 20,
        "font_size": 10
    },
    "customer_info_zip": {
        "anchor": "Customer",
        "dx": 500,  # Far right for zip
        "dy": 20,
        "font_size": 10
    },
    "customer_info_phone": {
        "anchor": "Customer",
        "dx": 150,  # Left side of third row
        "dy": 35,   # Third row
        "font_size": 10
    },
    "customer_info_email": {
        "anchor": "Customer",
        "dx": 300,  # Right side of third row  
        "dy": 35,
        "font_size": 10
    },
    
    # Page 1: Distribution Utility Section (below Customer Information)
    "distribution_utility_name": {
        "anchor": "Distribution",
        "dx": 150,  # Move to the right into the data area  
        "dy": 5,    # Much higher - just below the header
        "font_size": 10
    },
    "distribution_utility_account": {
        "anchor": "Distribution", 
        "dx": 150,  # Move to the right into the data area
        "dy": 20,   # Second row below utility name
        "font_size": 10
    },
    "distribution_utility_poid": {
        "anchor": "Distribution",
        "dx": 350,  # Further right for POID placement
        "dy": 20,   # Same row as account number
        "font_size": 10
    },
    
    # Page 2: Signature Section
    "customer_signature": {
        "anchor": "Signature of Subscriber:",
        "dx": 280,  # Position signature to the right of the text
        "dy": -2
    },
    "date_signed": {
        "anchor": "Date:",
        "context": "Signature of Subscriber:",  # Look for Date near Subscriber signature, not CDG Host
        "context_preference": "second",  # Use second Date field (subscriber's date)
        "dx": 50,  # Reduced offset - place date in the field, not far to the right
        "dy": -2
    }
}

# Exhibit 1 anchors for Commercial Agreements
# This is for the "List of Utility Accounts" table on the second to last page
EXHIBIT_1_ANCHORS = {
    "exhibit_utility": {
        "anchor": "Utility Company",
        "page_hint": -2,  # Second to last page
        "dx": 0,
        "dy": 25  # Moved up from 30 to 25 for better alignment
    },
    "exhibit_account_name": {
        "anchor": "Name on Utility Account",
        "page_hint": -2,
        "dx": 0,
        "dy": 25  # Moved up from 30 to 25
    },
    "exhibit_account_number": {
        "anchor": "Utility Account Number",
        "page_hint": -2,
        "dx": 0,
        "dy": 25  # Moved up from 30 to 25
    },
    "exhibit_service_address": {
        "anchor": "Service Address",
        "page_hint": -2,
        "dx": -140,  # Position text around X=465, safely in the column
        "dy": 25,  # Moved up from 30 to 25
        "multi_line": True  # Flag for multi-line handling
    }
}

# Commercial agreements need both UCB anchors and Exhibit 1 anchors
COMMERCIAL_AGREEMENT_ANCHORS = {**UCB_COMMERCIAL_ANCHORS, **EXHIBIT_1_ANCHORS}

# Template mapping to anchor configurations
TEMPLATE_ANCHOR_MAP = {
    "GreenWattUSA_Limited_Power_of_Attorney.pdf": POA_ANCHORS,
    "Meadow-National-Grid-Commercial-UCB-Agreement.pdf": COMMERCIAL_AGREEMENT_ANCHORS,
    "Meadow-NYSEG-Commercial-UCB-Agreement.pdf": COMMERCIAL_AGREEMENT_ANCHORS,
    "Meadow-RGE-Commercial-UCB-Agreement.pdf": COMMERCIAL_AGREEMENT_ANCHORS,
    "Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf": MASS_MARKET_ANCHORS,
    "GreenWATT-USA-Inc-Communtiy-Solar-Agency-Agreement.pdf": UCB_COMMERCIAL_ANCHORS  # Agency agreement uses similar format
}

def get_anchor_config(template_filename):
    """
    Get the anchor configuration for a specific template.
    
    Args:
        template_filename (str): Name of the PDF template file
        
    Returns:
        dict: Anchor configuration dictionary or None if not found
    """
    return TEMPLATE_ANCHOR_MAP.get(template_filename)

def get_signature_font_config():
    """
    Get signature font configuration for Adobe PDF signature style.
    Uses authentic cursive fonts for professional signature appearance.
    
    Returns:
        dict: Font configuration for signatures
    """
    return {
        "font_name": "Arizonia",  # Arizonia cursive font - elegant script style
        "font_file": "Arizonia/Arizonia-Regular.ttf",  # TTF file path
        "font_size": 22,  # Larger size for signature prominence 
        "color": (0, 0, 0),  # Solid black like Adobe signatures
        "style": "signature",  # Marker for signature styling
        "fallback_font": "Helvetica-Oblique",  # Fallback if TTF fails to load
    }