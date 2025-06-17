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
    }
}

# Universal Commercial UCB Agreement Anchors (Dynamic page search)
# These work for National Grid, NYSEG, RG&E commercial agreements
UCB_COMMERCIAL_ANCHORS = {
    "customer_signature": {
        "anchor": "By:",
        "context": "SUBSCRIBER:",  # Look for "By:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 15  # Move down 15 pixels for better positioning
    },
    "printed_name": {
        "anchor": "Name:",
        "context": "SUBSCRIBER:",  # Look for "Name:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 15  # Move down 15 pixels for better positioning
    },
    "title": {
        "anchor": "Title:",
        "context": "SUBSCRIBER:",  # Look for "Title:" after "SUBSCRIBER:" section
        "context_preference": "second",  # Use second match (subscriber vs solar producer)
        "dx": 60, 
        "dy": 15  # Move down 15 pixels for better positioning
    },
    # "email": {
    #     "anchor": "Email:",
    #     "dx": 120, 
    #     "dy": -2
    # }
}

# Mass Market Agreement Anchors
MASS_MARKET_ANCHORS = {
    "customer_signature": {
        "anchor": "Subscriber Signature:",
        "dx": 150, 
        "dy": -2
    },
    "printed_name": {
        "anchor": "Print Name:",
        "dx": 100, 
        "dy": -2
    },
    "date": {
        "anchor": "Date:",
        "dx": 60, 
        "dy": -2
    },
    "email": {
        "anchor": "Email Address:",
        "dx": 120, 
        "dy": -2
    }
}

# Template mapping to anchor configurations
TEMPLATE_ANCHOR_MAP = {
    "GreenWattUSA_Limited_Power_of_Attorney.pdf": POA_ANCHORS,
    "Meadow-National-Grid-Commercial-UCB-Agreement.pdf": UCB_COMMERCIAL_ANCHORS,
    "Meadow-NYSEG-Commercial-UCB-Agreement.pdf": UCB_COMMERCIAL_ANCHORS,
    "Meadow-RGE-Commercial-UCB-Agreement.pdf": UCB_COMMERCIAL_ANCHORS,
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