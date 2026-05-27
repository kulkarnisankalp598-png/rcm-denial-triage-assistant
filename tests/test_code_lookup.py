import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.code_lookup import get_carc_meaning, get_rarc_meaning, get_code_meanings

def test_carc_16():
    assert get_carc_meaning("16") == "Claim/service lacks information or has submission/billing error(s)."

def test_carc_50():
    assert get_carc_meaning("50") == "These are non-covered services because this is not deemed a 'medical necessity' by the payer."

def test_carc_97():
    assert get_carc_meaning("97") == "The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated."

def test_carc_1():
    assert get_carc_meaning("1") == "Deductible Amount."

def test_carc_96():
    assert get_carc_meaning("96") == "Non-covered charge(s)."

def test_carc_4():
    assert get_carc_meaning("4") == "The procedure code is inconsistent with the modifier used."

def test_rarc_ma130():
    assert get_rarc_meaning("MA130") == "Your claim contains incomplete and/or invalid information, and no appeal rights are afforded because the claim is unprocessable. Please submit a new claim with the complete/correct information."

def test_rarc_n20():
    assert get_rarc_meaning("N20") == "Service not payable with other service rendered on the same date."

def test_rarc_m15():
    assert get_rarc_meaning("M15") == "Separately billed services/tests have been bundled as they are considered components of the same procedure. Separate payment is not allowed."

def test_rarc_n4():
    assert get_rarc_meaning("N4") == "Missing/Incomplete/Invalid prior Insurance Carrier(s) EOB."

def test_rarc_n180():
    assert get_rarc_meaning("N180") == "This item or service does not meet the criteria for the category under which it was billed."

def test_rarc_n130():
    assert get_rarc_meaning("N130") == "Consult plan benefit documents/guidelines for information about restrictions for this service."

def test_unknown_carc():
    assert get_carc_meaning("9999") == "CARC code not found in lookup table."

def test_unknown_rarc():
    assert get_rarc_meaning("ZZZ999") == "RARC code not found in lookup table."

def test_unknown_rarc_flag():
    assert get_rarc_meaning("UNKNOWN") == "No remark code provided."

def test_rarc_none():
    assert get_rarc_meaning("") == "No remark code provided."

def test_get_code_meanings_returns_dict():
    result = get_code_meanings("16", "MA130")
    assert isinstance(result, dict)
    assert "carc_meaning" in result
    assert "rarc_meaning" in result

def test_get_code_meanings_values():
    result = get_code_meanings("16", "MA130")
    assert result["carc_meaning"] == "Claim/service lacks information or has submission/billing error(s)."
    assert "incomplete" in result["rarc_meaning"].lower()

def test_carc_case_insensitive():
    assert get_carc_meaning("a1") == get_carc_meaning("A1")

def test_rarc_case_insensitive():
    assert get_rarc_meaning("ma130") == get_rarc_meaning("MA130")