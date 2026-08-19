from quarries.gematria import mispar_gadol, breakdown

def test_mispar_gadol_regular_letters():
    assert mispar_gadol("שלום") == 936  # ש300 + ל30 + ו6 + final mem600

def test_mispar_gadol_final_letters_extended():
    assert mispar_gadol("ךםןףץ") == 3500

def test_niqqud_ignored():
    assert mispar_gadol("שָׁלוֹם") == mispar_gadol("שלום")
