import datetime
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace

import beangulp
from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import D

from tariochbctools.importers.general.deduplication import ReferenceDuplicatesComparator

NOT_PROVIDED = "NOTPROVIDED"

CAMT053_NAMESPACE = re.compile(
    r"^\{urn:iso:std:iso:20022:tech:xsd:camt\.053\.001\.\d+\}"
)


@dataclass(frozen=True)
class CamtTransaction:
    """One booked transaction of a camt.053 statement, independent of its version."""

    date: datetime.date
    amount: Amount
    ref: str
    counterparty: str = ""
    remittance: list[str] = field(default_factory=list)
    instruction_id: str = ""
    additional_info: str = ""
    entry_info: str = ""


def _strip_namespaces(root: ET.Element) -> None:
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None, path: str) -> str:
    if element is None:
        return ""
    found = element.find(path)
    if found is None or found.text is None:
        return ""
    return re.sub(r"\s+", " ", found.text).strip()


def _date(element: ET.Element | None) -> datetime.date | None:
    """Date of a `Dt` / `DtTm` choice, e.g. `BookgDt` or the `Dt` of a balance."""
    value = _text(element, "Dt") or _text(element, "DtTm")
    if not value:
        return None
    return datetime.date.fromisoformat(value[:10])


def _amount(element: ET.Element, indicator: str = "") -> Amount | None:
    amt = element.find("Amt")
    if amt is None or amt.text is None:
        return None
    number = D(amt.text.strip())
    if (_text(element, "CdtDbtInd") or indicator) == "DBIT":
        number = -number
    return Amount(number, amt.get("Ccy", ""))


def _status(entry: ET.Element) -> str:
    # up to version 08 the status is the text of Sts, from 09 on it is Sts/Cd
    return _text(entry, "Sts/Cd") or _text(entry, "Sts")


class Importer(beangulp.Importer):
    """An importer for ISO 20022 camt.053 bank statements (version 04 and later).

    Each booked entry becomes a transaction on `account`, batch bookings with
    individual amounts become one transaction per detail. The closing booked
    balance becomes a balance assertion. Subclasses can adapt metadata, payee
    and narration through `prepare_metadata`, `prepare_payee` and
    `prepare_narration`.
    """

    def __init__(self, filepattern: str, account: data.Account):
        self._filepattern = filepattern
        self._account = account

    def identify(self, filepath: str) -> bool:
        if re.search(self._filepattern, filepath) is None:
            return False
        try:
            for _, element in ET.iterparse(filepath, events=("start",)):
                return CAMT053_NAMESPACE.match(element.tag) is not None
        except ET.ParseError:
            return False
        return False

    def account(self, filepath: str) -> data.Account:
        return self._account

    cmp = ReferenceDuplicatesComparator()

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        root = ET.parse(filepath).getroot()
        _strip_namespaces(root)

        entries: data.Entries = []
        for statement in root.iterfind("BkToCstmrStmt/Stmt"):
            for entry in statement.iterfind("Ntry"):
                if _status(entry) == "BOOK":
                    for trx in self._parse_entry(entry):
                        entries.append(self._create_transaction(filepath, trx))
            entries.extend(self._create_balances(filepath, statement))

        return entries

    def _parse_entry(self, entry: ET.Element) -> list[CamtTransaction]:
        entry_amount = _amount(entry)
        booking_date = _date(entry.find("BookgDt"))
        if entry_amount is None or booking_date is None:
            return []
        indicator = _text(entry, "CdtDbtInd")
        base = CamtTransaction(
            booking_date,
            entry_amount,
            ref=_text(entry, "AcctSvcrRef"),
            entry_info=_text(entry, "AddtlNtryInf"),
        )

        details = entry.findall("NtryDtls/TxDtls")
        if len(details) == 1:
            return [self._with_details(base, details[0], indicator)]

        # a batch is split into its details only when their amounts add up
        parsed = [_amount(detail, indicator) for detail in details]
        detail_amounts = [a for a in parsed if a is not None]
        if (
            len(details) > 1
            and len(detail_amounts) == len(details)
            and all(a.currency == entry_amount.currency for a in detail_amounts)
            and sum(a.number or 0 for a in detail_amounts) == entry_amount.number
        ):
            return [
                self._with_details(
                    replace(
                        base,
                        amount=detail_amount,
                        ref=f"{base.ref}/{number}" if base.ref else "",
                    ),
                    detail,
                    indicator,
                )
                for number, (detail, detail_amount) in enumerate(
                    zip(details, detail_amounts, strict=True), start=1
                )
            ]
        return [base]

    def _with_details(
        self, base: CamtTransaction, detail: ET.Element, indicator: str
    ) -> CamtTransaction:
        # the counterparty is paid for a debit and pays for a credit
        role = "Cdtr" if indicator == "DBIT" else "Dbtr"
        # from version 08 on the party is wrapped in Pty
        counterparty = _text(detail, f"RltdPties/{role}/Nm") or _text(
            detail, f"RltdPties/{role}/Pty/Nm"
        )
        remittance = [_text(ustrd, ".") for ustrd in detail.iterfind("RmtInf/Ustrd")]
        remittance += [
            _text(strd, "AddtlRmtInf") for strd in detail.iterfind("RmtInf/Strd")
        ]
        instruction_id = _text(detail, "Refs/InstrId")
        additional_info = _text(detail, "AddtlTxInf")
        creditor_reference = _text(detail, "RmtInf/Strd/CdtrRefInf/Ref")
        if creditor_reference:
            # banks repeat the creditor reference (e.g. a QR reference) here
            additional_info = " ".join(
                additional_info.replace(creditor_reference, "").split()
            )
        return replace(
            base,
            ref=_text(detail, "Refs/AcctSvcrRef") or base.ref,
            counterparty=counterparty,
            remittance=[line for line in remittance if line],
            instruction_id="" if instruction_id == NOT_PROVIDED else instruction_id,
            additional_info=additional_info,
        )

    def _create_transaction(
        self, filepath: str, trx: CamtTransaction
    ) -> data.Transaction:
        meta = data.new_metadata(filepath, 0, self.prepare_metadata(trx))
        return data.Transaction(
            meta,
            trx.date,
            "*",
            self.prepare_payee(trx) or None,
            self.prepare_narration(trx),
            data.EMPTY_SET,
            data.EMPTY_SET,
            [
                data.Posting(
                    self._account,
                    trx.amount,
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )

    def _create_balances(
        self, filepath: str, statement: ET.Element
    ) -> list[data.Balance]:
        balances = []
        for balance in statement.iterfind("Bal"):
            if _text(balance, "Tp/CdOrPrtry/Cd") != "CLBD":
                continue
            balance_amount = _amount(balance)
            balance_date = _date(balance.find("Dt"))
            if balance_amount is None or balance_date is None:
                continue
            balances.append(
                data.Balance(
                    data.new_metadata(filepath, 0),
                    balance_date + datetime.timedelta(days=1),
                    self._account,
                    balance_amount,
                    None,
                    None,
                )
            )
        return balances

    def prepare_metadata(self, trx: CamtTransaction) -> dict[str, str]:
        return {"ref": trx.ref} if trx.ref else {}

    def prepare_payee(self, trx: CamtTransaction) -> str:
        return trx.counterparty

    def prepare_narration(self, trx: CamtTransaction) -> str:
        # what the payment is for, the bank's booking texts only as a fallback
        parts = dict.fromkeys(
            part for part in [trx.instruction_id, *trx.remittance] if part
        )
        return " - ".join(parts) or trx.additional_info or trx.entry_info
