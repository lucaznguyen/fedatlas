from __future__ import annotations

from typing import Any


COUNTRY_BY_ALPHA2: dict[str, tuple[str, str]] = {
    "AE": ("ARE", "United Arab Emirates"),
    "AL": ("ALB", "Albania"),
    "AT": ("AUT", "Austria"),
    "AU": ("AUS", "Australia"),
    "AZ": ("AZE", "Azerbaijan"),
    "BD": ("BGD", "Bangladesh"),
    "BE": ("BEL", "Belgium"),
    "BG": ("BGR", "Bulgaria"),
    "BH": ("BHR", "Bahrain"),
    "BN": ("BRN", "Brunei Darussalam"),
    "BR": ("BRA", "Brazil"),
    "BS": ("BHS", "Bahamas"),
    "CA": ("CAN", "Canada"),
    "CH": ("CHE", "Switzerland"),
    "CL": ("CHL", "Chile"),
    "CN": ("CHN", "China"),
    "CO": ("COL", "Colombia"),
    "CR": ("CRI", "Costa Rica"),
    "CY": ("CYP", "Cyprus"),
    "CZ": ("CZE", "Czechia"),
    "DE": ("DEU", "Germany"),
    "DK": ("DNK", "Denmark"),
    "DZ": ("DZA", "Algeria"),
    "EC": ("ECU", "Ecuador"),
    "EE": ("EST", "Estonia"),
    "EG": ("EGY", "Egypt"),
    "ES": ("ESP", "Spain"),
    "ET": ("ETH", "Ethiopia"),
    "FI": ("FIN", "Finland"),
    "FJ": ("FJI", "Fiji"),
    "FM": ("FSM", "Micronesia"),
    "FR": ("FRA", "France"),
    "GB": ("GBR", "United Kingdom"),
    "GH": ("GHA", "Ghana"),
    "GR": ("GRC", "Greece"),
    "GW": ("GNB", "Guinea-Bissau"),
    "HK": ("HKG", "Hong Kong"),
    "HR": ("HRV", "Croatia"),
    "HU": ("HUN", "Hungary"),
    "ID": ("IDN", "Indonesia"),
    "IE": ("IRL", "Ireland"),
    "IL": ("ISR", "Israel"),
    "IN": ("IND", "India"),
    "IQ": ("IRQ", "Iraq"),
    "IR": ("IRN", "Iran"),
    "IT": ("ITA", "Italy"),
    "JM": ("JAM", "Jamaica"),
    "JO": ("JOR", "Jordan"),
    "JP": ("JPN", "Japan"),
    "KR": ("KOR", "South Korea"),
    "KW": ("KWT", "Kuwait"),
    "KZ": ("KAZ", "Kazakhstan"),
    "LB": ("LBN", "Lebanon"),
    "LK": ("LKA", "Sri Lanka"),
    "LT": ("LTU", "Lithuania"),
    "LU": ("LUX", "Luxembourg"),
    "LV": ("LVA", "Latvia"),
    "MA": ("MAR", "Morocco"),
    "ME": ("MNE", "Montenegro"),
    "MK": ("MKD", "North Macedonia"),
    "MO": ("MAC", "Macao"),
    "MV": ("MDV", "Maldives"),
    "MX": ("MEX", "Mexico"),
    "MY": ("MYS", "Malaysia"),
    "NC": ("NCL", "New Caledonia"),
    "NG": ("NGA", "Nigeria"),
    "NL": ("NLD", "Netherlands"),
    "NO": ("NOR", "Norway"),
    "NP": ("NPL", "Nepal"),
    "NZ": ("NZL", "New Zealand"),
    "OM": ("OMN", "Oman"),
    "PE": ("PER", "Peru"),
    "PH": ("PHL", "Philippines"),
    "PK": ("PAK", "Pakistan"),
    "PL": ("POL", "Poland"),
    "PR": ("PRI", "Puerto Rico"),
    "PS": ("PSE", "Palestine"),
    "PT": ("PRT", "Portugal"),
    "QA": ("QAT", "Qatar"),
    "RO": ("ROU", "Romania"),
    "RS": ("SRB", "Serbia"),
    "RU": ("RUS", "Russia"),
    "RW": ("RWA", "Rwanda"),
    "SA": ("SAU", "Saudi Arabia"),
    "SD": ("SDN", "Sudan"),
    "SE": ("SWE", "Sweden"),
    "SG": ("SGP", "Singapore"),
    "SI": ("SVN", "Slovenia"),
    "SK": ("SVK", "Slovakia"),
    "SS": ("SSD", "South Sudan"),
    "TH": ("THA", "Thailand"),
    "TN": ("TUN", "Tunisia"),
    "TR": ("TUR", "Turkey"),
    "TT": ("TTO", "Trinidad and Tobago"),
    "TW": ("TWN", "Taiwan"),
    "TZ": ("TZA", "Tanzania"),
    "UA": ("UKR", "Ukraine"),
    "UG": ("UGA", "Uganda"),
    "US": ("USA", "United States"),
    "VN": ("VNM", "Vietnam"),
    "YE": ("YEM", "Yemen"),
    "ZA": ("ZAF", "South Africa"),
}


def normalize_alpha2(value: Any) -> str | None:
    if value is None:
        return None
    code = str(value).strip().upper()
    return code if len(code) == 2 else None


def country_alpha3(value: Any) -> str | None:
    code = normalize_alpha2(value)
    if not code:
        return None
    return COUNTRY_BY_ALPHA2.get(code, (None, code))[0]


def country_display_name(value: Any) -> str | None:
    code = normalize_alpha2(value)
    if not code:
        return None
    return COUNTRY_BY_ALPHA2.get(code, (code, code))[1]
