import datetime
from decimal import Decimal

import pytest
from beancount.core import data

from tariochbctools.importers.general import camt053importer


def document(version: str, entries: str, balances: str = "") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.{version}">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>MSG1</MsgId><CreDtTm>2024-03-01T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT1</Id>
      <Acct><Id><IBAN>CH9300762011623852957</IBAN></Id><Ccy>CHF</Ccy></Acct>
      {balances}
      {entries}
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""


BALANCES = """
<Bal>
  <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
  <Amt Ccy="CHF">1000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2024-02-01</Dt></Dt>
</Bal>
<Bal>
  <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
  <Amt Ccy="CHF">850.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><Dt><Dt>2024-02-29</Dt></Dt>
</Bal>
"""

SINGLE_CREDIT = """
<Ntry>
  <Amt Ccy="CHF">250.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><RvslInd>false</RvslInd><Sts>BOOK</Sts>
  <BookgDt><Dt>2024-02-05</Dt></BookgDt><ValDt><Dt>2024-02-06</Dt></ValDt>
  <AcctSvcrRef>REF-100</AcctSvcrRef>
  <BkTxCd><Domn><Cd>PMNT</Cd><Fmly><Cd>RCDT</Cd><SubFmlyCd>OTHR</SubFmlyCd></Fmly></Domn></BkTxCd>
  <NtryDtls><TxDtls>
    <Refs><AcctSvcrRef>REF-100/1</AcctSvcrRef></Refs>
    <Amt Ccy="CHF">250.00</Amt><CdtDbtInd>CRDT</CdtDbtInd>
    <RltdPties>
      <Dbtr><Nm>Example   Employer AG</Nm></Dbtr>
      <DbtrAcct><Id><IBAN>CH5604835012345678009</IBAN></Id></DbtrAcct>
      <Cdtr><Nm>Account Holder</Nm></Cdtr>
    </RltdPties>
    <RmtInf><Ustrd>Salary
      February</Ustrd></RmtInf>
    <AddtlTxInf>Credit transfer</AddtlTxInf>
  </TxDtls></NtryDtls>
  <AddtlNtryInf>Credit</AddtlNtryInf>
</Ntry>
"""

BATCH_DEBIT = """
<Ntry>
  <Amt Ccy="CHF">400.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>BOOK</Sts>
  <BookgDt><Dt>2024-02-10</Dt></BookgDt>
  <AcctSvcrRef>REF-200</AcctSvcrRef>
  <NtryDtls>
    <Btch><NbOfTxs>2</NbOfTxs></Btch>
    <TxDtls>
      <Refs><AcctSvcrRef>REF-200/1</AcctSvcrRef></Refs>
      <Amt Ccy="CHF">150.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
      <RltdPties><Cdtr><Nm>Example Utility</Nm></Cdtr></RltdPties>
      <RmtInf><Strd>
        <CdtrRefInf><Tp><CdOrPrtry><Prtry>QRR</Prtry></CdOrPrtry></Tp><Ref>210000000003139471430009017</Ref></CdtrRefInf>
        <AddtlRmtInf>Invoice 42</AddtlRmtInf>
      </Strd></RmtInf>
    </TxDtls>
    <TxDtls>
      <Amt Ccy="CHF">250.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
      <RltdPties><Cdtr><Nm>Example Landlord</Nm></Cdtr></RltdPties>
      <RmtInf><Strd>
        <CdtrRefInf><Tp><CdOrPrtry><Prtry>QRR</Prtry></CdOrPrtry></Tp><Ref>210000000003139471430009018</Ref></CdtrRefInf>
      </Strd></RmtInf>
      <AddtlTxInf>Mobile order</AddtlTxInf>
    </TxDtls>
  </NtryDtls>
</Ntry>
"""

PENDING = """
<Ntry>
  <Amt Ccy="CHF">99.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>PDNG</Sts>
  <BookgDt><Dt>2024-02-28</Dt></BookgDt>
  <AcctSvcrRef>REF-300</AcctSvcrRef>
</Ntry>
"""


@pytest.fixture(name="importer")
def importer_fixture():
    return camt053importer.Importer(r"\.xml$", "Assets:Bank:CHF")


def write(tmp_path, content: str, name: str = "statement.xml") -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def transactions(entries):
    return [entry for entry in entries if isinstance(entry, data.Transaction)]


def summary(entries):
    return [
        (
            entry.date,
            entry.payee,
            entry.narration,
            entry.meta.get("ref"),
            entry.postings[0].units.number,
            entry.postings[0].units.currency,
        )
        for entry in transactions(entries)
    ]


def test_extract(importer, tmp_path):
    path = write(
        tmp_path, document("04", SINGLE_CREDIT + BATCH_DEBIT + PENDING, BALANCES)
    )

    entries = importer.extract(path, [])

    assert summary(entries) == [
        (
            datetime.date(2024, 2, 5),
            "Example Employer AG",
            "Salary February",
            "REF-100/1",
            Decimal("250.00"),
            "CHF",
        ),
        (
            datetime.date(2024, 2, 10),
            "Example Utility",
            "Invoice 42",
            "REF-200/1",
            Decimal("-150.00"),
            "CHF",
        ),
        (
            datetime.date(2024, 2, 10),
            "Example Landlord",
            "Mobile order",
            "REF-200/2",
            Decimal("-250.00"),
            "CHF",
        ),
    ]
    assert all(
        entry.postings[0].account == "Assets:Bank:CHF"
        for entry in transactions(entries)
    )


def test_closing_balance_on_the_next_day(importer, tmp_path):
    path = write(tmp_path, document("08", SINGLE_CREDIT, BALANCES))

    balances = [
        entry for entry in importer.extract(path, []) if isinstance(entry, data.Balance)
    ]

    assert [
        (b.date, b.account, b.amount.number, b.amount.currency) for b in balances
    ] == [(datetime.date(2024, 3, 1), "Assets:Bank:CHF", Decimal("850.00"), "CHF")]


def test_negative_closing_balance(importer, tmp_path):
    balance = BALANCES.replace(
        '<Amt Ccy="CHF">850.00</Amt><CdtDbtInd>CRDT',
        '<Amt Ccy="CHF">850.00</Amt><CdtDbtInd>DBIT',
    )
    path = write(tmp_path, document("04", "", balance))

    balances = [
        entry for entry in importer.extract(path, []) if isinstance(entry, data.Balance)
    ]

    assert [b.amount.number for b in balances] == [Decimal("-850.00")]


def test_batch_that_does_not_add_up_stays_one_transaction(importer, tmp_path):
    entry = BATCH_DEBIT.replace(
        '<Amt Ccy="CHF">400.00</Amt>', '<Amt Ccy="CHF">410.00</Amt>'
    )
    path = write(tmp_path, document("04", entry))

    assert summary(importer.extract(path, [])) == [
        (datetime.date(2024, 2, 10), None, "", "REF-200", Decimal("-410.00"), "CHF"),
    ]


def test_entry_without_details(importer, tmp_path):
    entry = """
    <Ntry>
      <Amt Ccy="EUR">12.50</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>BOOK</Sts>
      <BookgDt><DtTm>2024-02-12T10:15:00</DtTm></BookgDt>
      <AddtlNtryInf>Card payment Example Shop</AddtlNtryInf>
    </Ntry>
    """
    path = write(tmp_path, document("04", entry))

    entries = importer.extract(path, [])

    assert summary(entries) == [
        (
            datetime.date(2024, 2, 12),
            None,
            "Card payment Example Shop",
            None,
            Decimal("-12.50"),
            "EUR",
        ),
    ]


def test_version_09_status_code_and_party(importer, tmp_path):
    entry = """
    <Ntry>
      <Amt Ccy="CHF">75.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts><Cd>BOOK</Cd></Sts>
      <BookgDt><Dt>2024-02-20</Dt></BookgDt>
      <AcctSvcrRef>REF-500</AcctSvcrRef>
      <NtryDtls><TxDtls>
        <Amt Ccy="CHF">75.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
        <RltdPties><Cdtr><Pty><Nm>Example Insurance</Nm></Pty></Cdtr></RltdPties>
        <RmtInf><Ustrd>Premium</Ustrd></RmtInf>
      </TxDtls></NtryDtls>
    </Ntry>
    """
    path = write(tmp_path, document("09", entry))

    assert summary(importer.extract(path, [])) == [
        (
            datetime.date(2024, 2, 20),
            "Example Insurance",
            "Premium",
            "REF-500",
            Decimal("-75.00"),
            "CHF",
        ),
    ]


def test_reversal_follows_the_credit_debit_indicator(importer, tmp_path):
    entry = """
    <Ntry>
      <Amt Ccy="CHF">40.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><RvslInd>true</RvslInd><Sts>BOOK</Sts>
      <BookgDt><Dt>2024-02-21</Dt></BookgDt>
      <AddtlNtryInf>Return of a payment</AddtlNtryInf>
    </Ntry>
    """
    path = write(tmp_path, document("04", entry))

    assert [e[4] for e in summary(importer.extract(path, []))] == [Decimal("40.00")]


def test_identify(importer, tmp_path):
    camt053 = write(tmp_path, document("08", ""))
    camt054 = write(
        tmp_path, document("08", "").replace("camt.053", "camt.054"), "notification.xml"
    )
    other_xml = write(tmp_path, "<root/>", "other.xml")
    broken = write(tmp_path, "not xml", "broken.xml")
    wrong_name = write(tmp_path, document("08", ""), "statement.txt")

    assert importer.identify(camt053)
    assert not importer.identify(camt054)
    assert not importer.identify(other_xml)
    assert not importer.identify(broken)
    assert not importer.identify(wrong_name)


def test_subclass_hooks(tmp_path):
    class CustomImporter(camt053importer.Importer):
        def prepare_metadata(self, trx):
            return {"ref": trx.ref, "info": trx.entry_info}

        def prepare_payee(self, trx):
            return trx.counterparty.upper()

        def prepare_narration(self, trx):
            return f"{trx.additional_info}: {' '.join(trx.remittance)}"

    path = write(tmp_path, document("04", SINGLE_CREDIT))
    entries = transactions(CustomImporter(r"\.xml$", "Assets:Bank").extract(path, []))

    assert [(e.payee, e.narration, e.meta["info"]) for e in entries] == [
        ("EXAMPLE EMPLOYER AG", "Credit transfer: Salary February", "Credit")
    ]


def test_only_the_ref_as_metadata(importer, tmp_path):
    path = write(tmp_path, document("04", SINGLE_CREDIT + BATCH_DEBIT))

    metas = [
        {
            key: value
            for key, value in entry.meta.items()
            if key not in ("filename", "lineno")
        }
        for entry in transactions(importer.extract(path, []))
    ]

    assert metas == [{"ref": "REF-100/1"}, {"ref": "REF-200/1"}, {"ref": "REF-200/2"}]


def test_instruction_id_and_creditor_reference_in_narration(importer, tmp_path):
    entry = """
    <Ntry>
      <Amt Ccy="CHF">60.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><Sts>BOOK</Sts>
      <BookgDt><Dt>2024-02-22</Dt></BookgDt>
      <NtryDtls>
        <TxDtls>
          <Refs><InstrId>Garden waste</InstrId></Refs>
          <Amt Ccy="CHF">20.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
          <RmtInf><Strd><CdtrRefInf><Ref>210000000003139471430009019</Ref></CdtrRefInf><AddtlRmtInf>Invoice 7</AddtlRmtInf></Strd></RmtInf>
          <AddtlTxInf>Mobile order 210000000003139471430009019</AddtlTxInf>
        </TxDtls>
        <TxDtls>
          <Refs><InstrId>NOTPROVIDED</InstrId></Refs>
          <Amt Ccy="CHF">40.00</Amt><CdtDbtInd>DBIT</CdtDbtInd>
          <RmtInf><Strd><CdtrRefInf><Ref>210000000003139471430009020</Ref></CdtrRefInf></Strd></RmtInf>
          <AddtlTxInf>Mobile order 210000000003139471430009020</AddtlTxInf>
        </TxDtls>
      </NtryDtls>
    </Ntry>
    """
    path = write(tmp_path, document("04", entry))

    assert [e[2] for e in summary(importer.extract(path, []))] == [
        "Garden waste - Invoice 7",
        "Mobile order",
    ]
