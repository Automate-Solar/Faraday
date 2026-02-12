

import os
import re
import pandas as pd
from pypdf import PdfReader

# ================= CONFIGURATION =================
# Put your folder path here (use forward slashes / even on Windows)
PDF_FOLDER_PATH = "C:/Users/jonsc690/Desktop/CZTS papers" 
#PDF_FOLDER_PATH = "C:/Users/jonsc690/Desktop/CZTS papers/scragg"
OUTPUT_CSV_NAME = "czts_parameter_report.csv"
# =================================================

def extract_text_from_pdf(file_path):
    """
    Attempts to extract text from a PDF. 
    Returns the full text string or None if failed.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        # Limit to first 5 pages to target Intro/Experimental 
        # and avoid parsing 20 pages of references
        for page in reader.pages[:10]: 
            extracted = page.extract_text()
            if extracted:
                text += extracted
        return text
    except Exception as e:
        print(f"Error reading {os.path.basename(file_path)}: {e}")
        return None

def analyze_paper(text):
    """
    Scans text for experimental keywords and regex patterns.
    Returns a dictionary of boolean (True/False) or String results.
    """
    # Normalize text to lowercase for easier matching
    text_lower = text.lower()
    
    results = {
        "Has_Temperature": False,
        "Has_Time": False,
        "Has_Cooling_Info": False,
        "Has_Cooling_Data": False,
        "Has_S(e)_Pressure_Explicit": False,
        "Has_SnS(e)_Pressure_Explicit": False,
        "Has_Pressure_Calculable": False,
        "Synthesis_Method_Hint": "Unknown"
    }

    # --- 1. TEMPERATURE (High Confidence) ---
    # Look for 3 digits followed by C (e.g., 500 C, 550°C)
    # We ignore 2 digits to avoid room temp (25°C)
    if re.search(r'\d{3}\s?°?c', text_lower):
        results["Has_Temperature"] = True

    # --- 2. TIME (High Confidence) ---
    # Look for digits followed by min, hour, h (e.g., 30 min, 1 h)
    if re.search(r'\d+\s?(min|hour|h\b)', text_lower):
        results["Has_Time"] = True

    # --- 3. COOLING RATE / METHOD (Medium Confidence) ---
    # Explicit rate: digits followed by C/min or K/s
    rate_keywords = ["cooling rate", "cool rate", "quench rate", "cooled at a rate", "rate of cooling", "cooled at"]
    has_rate = any(kw in text_lower for kw in rate_keywords)

    # Updated to handle:
    # 1. Standard: min-1, s -1
    # 2. Caret: min^-1
    # 3. Full Unicode Superscript: min⁻¹ (Common in high-quality typesetting)
    # 4. Mixed: min⁻1
    explicit_rate = re.search(
    r'\d+\s*(?:°|deg)?\s*[ck](?:\s*/\s*(?:min|s)|[\s\.]*(?:min|s)\s*(?:\^)?\s*[-⁻−–]\s*[1¹])\b', 
    text_lower
    )
    # Method keywords
    method_keywords = ["quench", "quenched", "natural cooling", "natural cool", "furnace cool", "cooled naturally", "slow cool", "cooled slowly", "slowly cooled"]
    has_method = any(kw in text_lower for kw in method_keywords)
    
    
    if has_rate and explicit_rate:
       results["Has_Cooling_Data"] = True 
    if has_method:
        results["Has_Cooling_Info"] = True

    # --- 4. SULFUR PRESSURE (The tricky part) ---
    
    # Check A: Explicit Pressure Units (Torr, atm, Pa, bar)
    # Must be near "sulfur", "selenium", or "vapor" to count.
    # We take a simplistic approach: check if both exist in the text.
    pressure_units = ["mbar", "torr", "atm", "bar", "\bpa\b"] # \b is word boundary
    chalcogen_terms = [
        "pressure of sulphur",
        "sulphur pressure", 
        "sulphur partial pressure", 
        "partial pressure of sulphur", 
        "sulphur vapour pressure",
        "sulphur vapor pressure",
        "pressure of sulfur",
        "pressure of s",
        "pressure of s2",
        "sulfur pressure", 
        "s pressure", 
        "s2 pressure", 
        "sulfur partial pressure", 
        "partial pressure of sulfur", 
        "s partial pressure", 
        "s2 partial pressure", 
        "partial pressure of s",
        "s vapour pressure", 
        "s2 vapour pressure", 
        "sulfur vapour pressure",
        "s vapor pressure", 
        "s2 vapor pressure", 
        "sulfur vapor pressure",
        "selenium pressure", 
        "pressure of selenium",
        "pressure of se",
        "pressure of se2",
        "se pressure", 
        "se2 pressure", 
        "selenium partial pressure", 
        "partial pressure of selenium", 
        "se partial pressure", 
        "se2 partial pressure", 
        "partial pressure of se",
        "partial pressure of se2",
        "se vapour pressure", 
        "se2 vapour pressure", 
        "selenium vapour pressure",
        "se vapor pressure", 
        "se2 vapor pressure", 
        "selenium vapor pressure",
    ]
    sns_terms = [
        "tin sulphide pressure", 
        "tin sulphide partial pressure", 
        "partial pressure of tin sulphide", 
        "tin sulphide vapour pressure",
        "tin sulphide vapor pressure",
        "tin sulfide pressure", 
        "sns pressure", 
        "tin sulfide partial pressure", 
        "partial pressure of tin sulfide", 
        "sns partial pressure", 
        "partial pressure of sns",
        "sns vapour pressure", 
        "tin sulfide vapour pressure",
        "sns vapor pressure", 
        "tin sulfide vapor pressure",
        "tin selenide pressure", 
        "snse pressure", 
        "tin selenide partial pressure", 
        "partial pressure of tin selenide", 
        "snse partial pressure", 
        "partial pressure of snse",
        "snse vapour pressure", 
        "tin selenide vapour pressure",
        "snse vapor pressure", 
        "tin selenide vapor pressure",
        "pressure of tin sulfide",
        "pressure of sns",
        "pressure of tin selenide",
        "pressure of snse",
    ]
    
    has_p_unit = any(u in text_lower for u in pressure_units)
    has_chal_term = any(t in text_lower for t in chalcogen_terms)
    has_sns_term = any(t in text_lower for t in sns_terms)
    
    if has_p_unit and has_chal_term:
        results["Has_S(e)_Pressure_Explicit"] = True

    #if has_p_unit and has_chal_term:
    if has_p_unit and has_sns_term:
        results["Has_SnS(e)_Pressure_Explicit"] = True

    # Check B: Calculable (Mass + Volume)
    # Look for mass units (mg, g) AND volume terms (ampoule, tube, graphite box)
    mass_terms = ["mg", " g ", "weight", "amount"]
    vol_terms = ["ampoule", "tube", "graphite box", "chamber volume", "crucible", "cm3", "ml"]
    
    has_mass = any(m in text_lower for m in mass_terms)
    has_vol = any(v in text_lower for v in vol_terms)
    
    if has_mass and has_vol:
        results["Has_Pressure_Calculable"] = True
        
    # --- 5. METHOD HINT (Bonus) ---
    if "sputter" in text_lower:
        results["Synthesis_Method_Hint"] = "Sputtering"
    elif "spin" in text_lower or "sol-gel" in text_lower:
        results["Synthesis_Method_Hint"] = "Solution"
    elif "evaporat" in text_lower:
        results["Synthesis_Method_Hint"] = "Evaporation"

    return results

def main():
    if not os.path.exists(PDF_FOLDER_PATH):
        print("Folder not found! Please check the path.")
        return

    data = []
    files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.lower().endswith('.pdf')]
    print(f"Found {len(files)} PDFs. Starting scan...")

    for filename in files:
        filepath = os.path.join(PDF_FOLDER_PATH, filename)
        
        # 1. Read Text
        full_text = extract_text_from_pdf(filepath)
        
        if full_text:
            # 2. Analyze
            analysis = analyze_paper(full_text)
            
            # 3. Add Metadata
            row = {"Filename": filename}
            row.update(analysis)
            data.append(row)
        else:
            print(f"Skipping {filename} (unreadable)")

    # 4. Save to CSV
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_CSV_NAME, index=False)
    
    # 5. Print Summary Statistics
    print("\n" + "="*30)
    print("SCAN COMPLETE. SUMMARY:")
    print("="*30)
    print(f"Total Papers Scanned: {len(df)}")
    print(f"Temp Reported:      {df['Has_Temperature'].sum()} ({df['Has_Temperature'].mean():.1%})")
    print(f"Time Reported:      {df['Has_Time'].sum()} ({df['Has_Time'].mean():.1%})")
    print(f"Cooling Info:       {df['Has_Cooling_Info'].sum()} ({df['Has_Cooling_Info'].mean():.1%})")
    print(f"Cooling Data:       {df['Has_Cooling_Data'].sum()} ({df['Has_Cooling_Data'].mean():.1%})")
    print(f"S(e) Pressure (Explicit):{df['Has_S(e)_Pressure_Explicit'].sum()} ({df['Has_S(e)_Pressure_Explicit'].mean():.1%})")
    print(f"SnS(e) Pressure (Explicit):{df['Has_SnS(e)_Pressure_Explicit'].sum()} ({df['Has_SnS(e)_Pressure_Explicit'].mean():.1%})")
    print(f"Pressure (Calc.):   {df['Has_Pressure_Calculable'].sum()} ({df['Has_Pressure_Calculable'].mean():.1%})")
    print("="*30)
    print(f"Detailed results saved to: {OUTPUT_CSV_NAME}")

if __name__ == "__main__":
    main()
# How this script works (The "Logic"):

# PDF Reader: It uses pypdf to open the file. I set it to only read the first 5 pages.

# Why? Most synthesis papers are 4–8 pages long. The "Experimental" section is almost always on page 2 or 3. This prevents the script from searching the "References" section (which is full of titles from other papers that might contain keywords like "pressure" or "temperature").

# Temperature Filter: It looks for \d{3} (3 digits) followed by "C". This targets annealing temps (e.g., "550 C") while ignoring room temperature ("25 C").

# Cooling Filter: It accepts two types of "Yes":

# Quantitative: If it finds units like "°C/min" or "K/s".

# Qualitative: If it finds keywords like "quench," "natural cool," or "furnace cool."

# Pressure Logic (The tiered approach):

# Explicit: It checks for pressure units (Torr, atm, Pa) and chalcogen keywords (sulfur, vapor). This avoids flagging "standard atmospheric pressure" as a reported experimental variable.

# Calculable: It checks for the ingredients of the Ideal Gas Law. If the paper mentions "ampoule/tube" (Volume) AND "mg/g" (Mass), it marks it as Calculable.

# How to use it:

# Create a folder named my_czts_papers in the same directory as the script.

# Dump your 100+ PDFs into that folder.

# Run the script.

# Open the generated czts_parameter_report.csv in Excel.

# You will immediately get the summary statistics printed in the terminal (e.g., "Pressure (Explicit): 5%"), giving you the answer to your research question in seconds.