from fedatlas.country_codes import country_alpha3, country_display_name


def test_country_code_lookup_for_map_locations():
    assert country_alpha3("US") == "USA"
    assert country_alpha3("CN") == "CHN"
    assert country_display_name("GB") == "United Kingdom"
