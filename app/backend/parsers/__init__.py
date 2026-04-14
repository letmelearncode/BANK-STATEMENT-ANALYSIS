# parsers package
from parsers.bank_identifier import identify_bank
from parsers.absa import AbsaParser
from parsers.fnb import FnbParser
from parsers.nedbank import NedbankParser
from parsers.standard_bank import StandardBankParser
from parsers.capitec import CapitecParser
from parsers.csv_import import CsvImportParser

PARSERS = {
    "ABSA": AbsaParser,
    "FNB": FnbParser,
    "Nedbank": NedbankParser,
    "Standard Bank": StandardBankParser,
    "Capitec": CapitecParser,
}

__all__ = [
    "identify_bank",
    "PARSERS",
    "AbsaParser",
    "FnbParser",
    "NedbankParser",
    "StandardBankParser",
    "CapitecParser",
    "CsvImportParser",
]
