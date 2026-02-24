# IB Flex Query Data Format

This document describes the XML data format used by the IB Flex Query API and how IB Analytics parses it. For troubleshooting data issues, see the [Troubleshooting Guide](./troubleshooting.md). For general usage, see [README.md](../README.md).

> **Note**: Only XML format is supported. CSV support has been removed. The `detect_format()` function in `ib_sec_mcp/core/parsers.py` validates that input data begins with `<` and raises `ValueError` for non-XML data.

---

## Table of Contents

- [API Workflow](#api-workflow)
- [XML Structure Overview](#xml-structure-overview)
- [Sections Reference](#sections-reference)
  - [AccountInformation](#accountinformation)
  - [CashReport / CashReportCurrency](#cashreport-cashreportcurrency)
  - [OpenPositions / OpenPosition](#openpositions-openposition)
  - [Trades / Trade](#trades-trade)
- [Multi-Account Support](#multi-account-support)
- [Currency Handling](#currency-handling)
- [Bond-Specific Fields](#bond-specific-fields)
- [Date and Time Formats](#date-and-time-formats)
- [Parser API Reference](#parser-api-reference)

---

## API Workflow

The IB Flex Query API uses a two-step asynchronous workflow:

```
Step 1: SendRequest
  Client ──> https://ndcdyn.interactivebrokers.com/.../SendRequest
             ?t=TOKEN&q=QUERY_ID&v=3
  Server <── XML response with <ReferenceCode>

Step 2: GetStatement (with retry)
  Client ──> https://gdcdyn.interactivebrokers.com/.../GetStatement
             ?t=TOKEN&q=REFERENCE_CODE&v=3
  Server <── XML data (FlexQueryResponse)
             OR "Statement generation in progress" (retry after delay)
```

**Default Configuration**:

| Parameter     | Default | Description                             |
| ------------- | ------- | --------------------------------------- |
| `timeout`     | 30s     | HTTP request timeout                    |
| `max_retries` | 3       | Maximum retry attempts for GetStatement |
| `retry_delay` | 5s      | Delay between retries                   |
| API Version   | 3       | IB Flex Query API version               |

If `GetStatement` returns "Statement generation in progress", the client waits `retry_delay` seconds and tries again, up to `max_retries` attempts.

---

## XML Structure Overview

The complete XML structure returned by the IB Flex Query API:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="My Query" type="AF">
  <FlexStatements count="2">

    <!-- One FlexStatement per account -->
    <FlexStatement accountId="U1234567" fromDate="20250101" toDate="20251005">

      <AccountInformation
        accountId="U1234567"
        acctAlias="Main Account" />

      <CashReport>
        <CashReportCurrency
          currency="BASE_SUMMARY"
          startingCash="50000.00"
          endingCash="52500.00"
          endingSettledCash="52000.00"
          deposits="5000.00"
          withdrawals="0.00"
          dividends="150.00"
          brokerInterest="25.00"
          commissions="-45.50"
          otherFees="-2.00"
          netTradesSales="10000.00"
          netTradesPurchases="-12500.00" />
        <CashReportCurrency
          currency="USD"
          startingCash="50000.00"
          endingCash="52500.00"
          ... />
      </CashReport>

      <OpenPositions>
        <OpenPosition
          symbol="AAPL"
          description="APPLE INC"
          assetCategory="STK"
          cusip="037833100"
          isin="US0378331005"
          position="100"
          costBasisMoney="15000.00"
          positionValue="17500.00"
          fifoPnlUnrealized="2500.00"
          markPrice="175.00"
          multiplier="1"
          currency="USD"
          fxRateToBase="1"
          reportDate="20251005" />
      </OpenPositions>

      <Trades>
        <Trade
          tradeID="123456789"
          tradeDate="20250915"
          settleDateTarget="20250917"
          symbol="AAPL"
          description="APPLE INC"
          assetCategory="STK"
          buySell="BUY"
          quantity="50"
          tradePrice="172.50"
          tradeMoney="8625.00"
          currency="USD"
          fxRateToBase="1"
          ibCommission="-1.00"
          ibCommissionCurrency="USD"
          fifoPnlRealized="0.00"
          mtmPnl="125.00"
          orderID="987654"
          executionID="0000e123.67890abc.01.01"
          orderTime="20250915;143052"
          notes="" />
      </Trades>

    </FlexStatement>

    <!-- Second account -->
    <FlexStatement accountId="U7654321" fromDate="20250101" toDate="20251005">
      <!-- Same structure as above -->
    </FlexStatement>

  </FlexStatements>
</FlexQueryResponse>
```

---

## Sections Reference

### AccountInformation

Basic account identification data.

| Attribute   | Type   | Description                | Example      |
| ----------- | ------ | -------------------------- | ------------ |
| `accountId` | string | IB account identifier      | `"U1234567"` |
| `acctAlias` | string | User-defined account alias | `"Main"`     |

**Parser**: `XMLParser._parse_account_info()` extracts these values. If `AccountInformation` is missing, the parser falls back to the `accountId` attribute on the `FlexStatement` element. If neither is available, the account ID is set to `"UNKNOWN"` and the account is skipped by `to_accounts()`.

---

### CashReport / CashReportCurrency

Cash flow and balance data. Each `CashReportCurrency` element represents balances in a specific currency.

| Attribute            | Type    | Description                               | Example                   |
| -------------------- | ------- | ----------------------------------------- | ------------------------- |
| `currency`           | string  | Currency code or `"BASE_SUMMARY"`         | `"USD"`, `"BASE_SUMMARY"` |
| `startingCash`       | decimal | Cash balance at period start              | `"50000.00"`              |
| `endingCash`         | decimal | Cash balance at period end                | `"52500.00"`              |
| `endingSettledCash`  | decimal | Settled cash at period end                | `"52000.00"`              |
| `deposits`           | decimal | Total deposits during period              | `"5000.00"`               |
| `withdrawals`        | decimal | Total withdrawals during period           | `"0.00"`                  |
| `dividends`          | decimal | Dividend income received                  | `"150.00"`                |
| `brokerInterest`     | decimal | Broker interest (credit or debit)         | `"25.00"`                 |
| `commissions`        | decimal | Total commissions paid (usually negative) | `"-45.50"`                |
| `otherFees`          | decimal | Other fees (usually negative)             | `"-2.00"`                 |
| `netTradesSales`     | decimal | Net proceeds from sales                   | `"10000.00"`              |
| `netTradesPurchases` | decimal | Net cost of purchases (usually negative)  | `"-12500.00"`             |

**Important**: The parser prioritizes the `BASE_SUMMARY` currency entry, which provides USD-converted totals across all currencies. Individual currency entries (e.g., `USD`, `JPY`) do not include FX rates in the CashReport section, so using them directly would require manual FX conversion and may produce incorrect totals.

**Parser**: `XMLParser._parse_cash_balances()` first looks for `BASE_SUMMARY`, and falls back to individual currency entries only if `BASE_SUMMARY` is absent.

---

### OpenPositions / OpenPosition

Current holdings as of the report date.

| Attribute           | Type    | Description                               | Example                           |
| ------------------- | ------- | ----------------------------------------- | --------------------------------- |
| `symbol`            | string  | Trading symbol                            | `"AAPL"`                          |
| `description`       | string  | Security description                      | `"APPLE INC"`                     |
| `assetCategory`     | string  | Asset class                               | `"STK"`, `"BOND"`, `"OPT"`        |
| `cusip`             | string  | CUSIP identifier                          | `"037833100"`                     |
| `isin`              | string  | ISIN identifier                           | `"US0378331005"`                  |
| `position`          | decimal | Quantity held (mapped to `quantity`)      | `"100"`, `"-50"` (short)          |
| `costBasisMoney`    | decimal | Total cost basis in local currency        | `"15000.00"`                      |
| `positionValue`     | decimal | Market value in local currency            | `"17500.00"`                      |
| `fifoPnlUnrealized` | decimal | Unrealized P&L (FIFO method)              | `"2500.00"`                       |
| `markPrice`         | decimal | Current market price per unit             | `"175.00"`                        |
| `multiplier`        | decimal | Contract multiplier                       | `"1"` (stocks), `"100"` (options) |
| `currency`          | string  | Local currency of the position            | `"USD"`, `"JPY"`                  |
| `fxRateToBase`      | decimal | FX rate to convert to base currency (USD) | `"1"`, `"0.0067"`                 |
| `reportDate`        | string  | Report date (YYYYMMDD)                    | `"20251005"`                      |
| `coupon`            | decimal | Bond coupon rate (bonds only)             | `"4.25"`, `"0"` (STRIPS)          |
| `maturity`          | string  | Bond maturity date (bonds only, YYYYMMDD) | `"20301215"`                      |

**Currency Conversion**: The parser multiplies `positionValue`, `fifoPnlUnrealized`, and `costBasisMoney` by `fxRateToBase` to convert all values to USD. The `average_cost` is calculated as `costBasisMoney * fxRateToBase / quantity`.

**Asset Classes**: The parser maps `assetCategory` to the `AssetClass` enum:

| XML Value | Enum Value         | Description         |
| --------- | ------------------ | ------------------- |
| `STK`     | `AssetClass.STK`   | Stocks              |
| `BOND`    | `AssetClass.BOND`  | Bonds               |
| `OPT`     | `AssetClass.OPT`   | Options             |
| `FUND`    | `AssetClass.FUND`  | Mutual Funds        |
| `CASH`    | `AssetClass.CASH`  | Cash / Forex        |
| (other)   | `AssetClass.OTHER` | Unknown asset class |

**Parser**: `XMLParser._parse_positions_xml()`

---

### Trades / Trade

Individual trade execution records.

| Attribute              | Type    | Description                            | Example                     |
| ---------------------- | ------- | -------------------------------------- | --------------------------- |
| `tradeID`              | string  | Unique trade identifier                | `"123456789"`               |
| `tradeDate`            | string  | Trade execution date (YYYYMMDD)        | `"20250915"`                |
| `settleDateTarget`     | string  | Expected settlement date (YYYYMMDD)    | `"20250917"`                |
| `symbol`               | string  | Trading symbol                         | `"AAPL"`                    |
| `description`          | string  | Security description                   | `"APPLE INC"`               |
| `assetCategory`        | string  | Asset class (same values as positions) | `"STK"`                     |
| `buySell`              | string  | Trade direction                        | `"BUY"`, `"SELL"`           |
| `quantity`             | decimal | Number of units traded                 | `"50"`, `"-50"` (sell)      |
| `tradePrice`           | decimal | Execution price per unit               | `"172.50"`                  |
| `tradeMoney`           | decimal | Total trade value (price x quantity)   | `"8625.00"`                 |
| `currency`             | string  | Trade currency                         | `"USD"`                     |
| `fxRateToBase`         | decimal | FX rate to base currency (USD)         | `"1"`, `"0.0067"`           |
| `ibCommission`         | decimal | IB commission (usually negative)       | `"-1.00"`                   |
| `ibCommissionCurrency` | string  | Commission currency                    | `"USD"`                     |
| `fifoPnlRealized`      | decimal | Realized P&L (FIFO method)             | `"0.00"`, `"500.00"`        |
| `mtmPnl`               | decimal | Mark-to-market P&L                     | `"125.00"`                  |
| `orderID`              | string  | Order identifier                       | `"987654"`                  |
| `executionID`          | string  | Execution identifier                   | `"0000e123.67890abc.01.01"` |
| `orderTime`            | string  | Order timestamp (YYYYMMDD;HHMMSS)      | `"20250915;143052"`         |
| `notes`                | string  | Trade notes/flags                      | `""`, `"P"` (partial fill)  |

**Buy/Sell Mapping**: The parser maps `buySell` to the `BuySell` enum:

| XML Value | Enum Value     |
| --------- | -------------- |
| `BUY`     | `BuySell.BUY`  |
| `SELL`    | `BuySell.SELL` |

**Parser**: `XMLParser._parse_trades_xml()`

---

## Multi-Account Support

A single IB Flex Query can return data for multiple accounts. Each account is represented by a separate `FlexStatement` element within the `FlexStatements` container.

```xml
<FlexQueryResponse>
  <FlexStatements count="2">
    <FlexStatement accountId="U1234567" ...>
      <!-- Account 1 data -->
    </FlexStatement>
    <FlexStatement accountId="U7654321" ...>
      <!-- Account 2 data -->
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
```

### Parser Methods

| Method                    | Returns              | Use Case                                           |
| ------------------------- | -------------------- | -------------------------------------------------- |
| `XMLParser.to_accounts()` | `dict[str, Account]` | Parse all accounts (key = account ID)              |
| `XMLParser.to_account()`  | `Account`            | Parse a specific account (or first if unspecified) |

### How Account Detection Works

1. The parser iterates over all `FlexStatement` elements
2. For each statement, it reads the `accountId` attribute from `AccountInformation`
3. If `AccountInformation` is missing, it falls back to the `accountId` attribute on the `FlexStatement` element
4. Accounts with ID `"UNKNOWN"` are skipped by `to_accounts()`

### CLI Usage

```bash
# Fetch and auto-detect multiple accounts
ib-sec-fetch --start-date 2025-01-01 --end-date 2025-10-05

# Fetch and split into separate files per account
ib-sec-fetch --split-accounts --start-date 2025-01-01 --end-date 2025-10-05

# Analyze a specific account
ib-sec-analyze --account U1234567

# Analyze all accounts
ib-sec-analyze --all-accounts
```

---

## Currency Handling

### Base Currency Conversion

IB provides position and trade values in the local currency of each security. The parser converts all values to USD using the `fxRateToBase` attribute.

**Position Values**:

```
position_value_usd  = positionValue * fxRateToBase
unrealized_pnl_usd  = fifoPnlUnrealized * fxRateToBase
cost_basis_usd       = costBasisMoney * fxRateToBase
average_cost         = cost_basis_usd / quantity
```

**Cash Report**:

The `BASE_SUMMARY` entry in `CashReport` provides pre-converted USD totals. The parser uses this exclusively to avoid manual FX conversion of individual currency entries.

### FX Rate Handling

- The `fxRateToBase` attribute is a multiplier to convert local currency to USD
- For USD-denominated positions, `fxRateToBase = 1`
- For JPY-denominated positions, `fxRateToBase` is approximately `0.0067` (1/149)
- The parser creates `Decimal` values directly from the string attribute to preserve precision
- If `fxRateToBase` is missing or invalid, the parser defaults to `Decimal("1")`

---

## Bond-Specific Fields

Bonds have additional optional fields in the `OpenPosition` element:

| Field           | XML Attribute | Type    | Notes                                                                                        |
| --------------- | ------------- | ------- | -------------------------------------------------------------------------------------------- |
| `coupon_rate`   | `coupon`      | Decimal | Annual coupon rate. `0` for zero-coupon bonds (STRIPS). `None` if attribute is absent.       |
| `maturity_date` | `maturity`    | date    | Maturity date in YYYYMMDD format. May be `None` if not provided by IB.                       |
| `ytm`           | (calculated)  | Decimal | Not provided by IB. Calculated by `BondAnalyzer` when maturity date and price are available. |
| `duration`      | (calculated)  | Decimal | Not provided by IB. Calculated by `BondAnalyzer`.                                            |

**Example Bond Position**:

```xml
<OpenPosition
  symbol="US912828ZT58"
  description="UNITED STATES TREAS BONDS"
  assetCategory="BOND"
  cusip="912828ZT5"
  position="10000"
  costBasisMoney="9500.00"
  positionValue="9750.00"
  markPrice="97.50"
  coupon="0"
  maturity="20301215"
  currency="USD"
  fxRateToBase="1" />
```

See the [Troubleshooting Guide - Bond Data Gaps](./troubleshooting.md#9-bond-data-gaps) for handling missing bond data.

---

## Date and Time Formats

| Field              | Format          | Example             | Notes                             |
| ------------------ | --------------- | ------------------- | --------------------------------- |
| `fromDate`         | YYYYMMDD        | `"20250101"`        | On FlexStatement element          |
| `toDate`           | YYYYMMDD        | `"20251005"`        | On FlexStatement element          |
| `tradeDate`        | YYYYMMDD        | `"20250915"`        |                                   |
| `settleDateTarget` | YYYYMMDD        | `"20250917"`        |                                   |
| `reportDate`       | YYYYMMDD        | `"20251005"`        | On OpenPosition element           |
| `maturity`         | YYYYMMDD        | `"20301215"`        | On OpenPosition (bonds)           |
| `orderTime`        | YYYYMMDD;HHMMSS | `"20250915;143052"` | Semicolon-separated date and time |

The parser uses `datetime.strptime()` with format `"%Y%m%d"` for dates and `"%Y%m%d;%H%M%S"` for order times. Invalid dates fall back to `date.today()`.

---

## Parser API Reference

### `XMLParser` Class

Located in `ib_sec_mcp/core/parsers.py`.

| Method                                                      | Description                                |
| ----------------------------------------------------------- | ------------------------------------------ |
| `parse(xml_data)`                                           | Parse XML into raw element structure       |
| `to_account(xml_data, from_date, to_date, account_id=None)` | Parse single account to `Account` model    |
| `to_accounts(xml_data, from_date, to_date)`                 | Parse all accounts to `dict[str, Account]` |

### `detect_format(data)` Function

Validates that the input data is XML format. Raises `ValueError` if the data does not start with `<`. Always returns `"xml"`.

```python
from ib_sec_mcp.core.parsers import XMLParser, detect_format

# Validate format
detect_format(xml_data)  # Returns "xml" or raises ValueError

# Parse all accounts
accounts = XMLParser.to_accounts(xml_data, from_date, to_date)
# Returns: dict[str, Account]  (e.g., {"U1234567": Account(...), "U7654321": Account(...)})

# Parse specific account
account = XMLParser.to_account(xml_data, from_date, to_date, account_id="U1234567")
# Returns: Account
```

### Security

The parser uses `defusedxml.ElementTree` instead of the standard library `xml.etree.ElementTree` to prevent:

- XML entity expansion attacks (billion laughs)
- External entity injection (XXE)
- DTD retrieval attacks

This is a security best practice for processing untrusted XML input.

---

## Related Documentation

- [README.md](../README.md) - Project overview and usage
- [INSTALL.md](../INSTALL.md) - Installation guide
- [Troubleshooting Guide](./troubleshooting.md) - Error resolution
- [IB Flex Query Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/) - Official IB documentation
